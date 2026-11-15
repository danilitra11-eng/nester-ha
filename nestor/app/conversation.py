"""Conversation loop: cloud step -> run tools locally -> cloud step ... -> reply."""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable
from zoneinfo import ZoneInfo

import aiohttp

from .ha import ToolRunner
from .i18n import localize, pick_language
from .settings import CHAT_EDITABLE, Settings, SettingsError

MAX_STEPS = 8
MAX_HISTORY = 40          # messages; beyond this a new conversation starts
IDLE_RESET_SECONDS = 600  # a pause of 10 minutes starts a new conversation

class CloudError(Exception):
    def __init__(self, code: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail or {}


class CloudClient:
    def __init__(self, session: aiohttp.ClientSession, base_url: str,
                 license_key: str | Callable[[], str], instance_id: str, version: str) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        # A callable so a key entered in the setup wizard takes effect immediately.
        self._key = license_key if callable(license_key) else (lambda: license_key)
        self._instance = instance_id
        self._version = version

    async def _post(self, path: str, body: dict[str, Any], key: str | None = None) -> dict[str, Any]:
        key = (key if key is not None else self._key()).strip()
        if not key:
            raise CloudError("missing_key")
        payload = {"license_key": key, "instance_id": self._instance, **body}
        try:
            async with self._session.post(f"{self._base}{path}", json=payload,
                                          timeout=aiohttp.ClientTimeout(total=120)) as resp:
                data = await resp.json(content_type=None)
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise CloudError("offline") from exc
        if resp.status >= 400:
            detail = data.get("detail") if isinstance(data, dict) else None
            code = detail.get("code", "generic") if isinstance(detail, dict) else "generic"
            raise CloudError(code, detail if isinstance(detail, dict) else None)
        return data

    async def verify(self, key: str | None = None) -> dict[str, Any]:
        """Check the saved key, or a candidate key typed into the setup wizard."""
        return await self._post("/v1/license/verify", {}, key)

    async def step(self, messages: list[dict[str, Any]], name: str, language: str,
                   personality: str) -> dict[str, Any]:
        return await self._post("/v1/chat", {"messages": messages, "assistant_name": name,
                                             "language": language, "personality": personality,
                                             "addon_version": self._version})


@dataclass
class Conversation:
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_used: float = field(default_factory=time.monotonic)


class Butler:
    def __init__(self, cloud: CloudClient, tools: ToolRunner, settings: Settings,
                 timezone: str = "UTC", temperature_unit: str = "") -> None:
        self.cloud = cloud
        self.tools = tools
        self.settings = settings
        self.timezone = timezone
        self.temperature_unit = temperature_unit
        self._convs: dict[str, Conversation] = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def now(self) -> datetime:
        try:
            return datetime.now(ZoneInfo(self.timezone))
        except Exception:
            return datetime.now()

    def should_speak(self) -> bool:
        return bool(self.settings["speak_replies"]) and not self.settings.in_quiet_hours(
            self.now().time())

    def reset(self, conversation_id: str) -> None:
        self._convs.pop(conversation_id, None)

    def _conversation(self, cid: str) -> Conversation:
        conv = self._convs.get(cid)
        if (conv is None or len(conv.messages) > MAX_HISTORY
                or time.monotonic() - conv.last_used > IDLE_RESET_SECONDS):
            conv = Conversation()
            self._convs[cid] = conv
        conv.last_used = time.monotonic()
        return conv

    def _context_line(self) -> str:
        st = self.settings
        units = f"; temperatures in {self.temperature_unit}" if self.temperature_unit else ""
        quiet = st["quiet_hours"]
        quiet_txt = f"{quiet['start']}-{quiet['end']}" if quiet else "none"
        return (f"[Home local time: {self.now():%A %Y-%m-%d %H:%M}{units}]\n"
                f"[Your settings: personality {st['personality']}; language {st['language']}; "
                f"read replies aloud {'on' if st['speak_replies'] else 'off'}; "
                f"quiet hours {quiet_txt}]")

    def _update_settings(self, changes: dict[str, Any]) -> tuple[str, bool]:
        changes = {k: v for k, v in changes.items() if v is not None or k == "quiet_hours"}
        try:
            applied = self.settings.update(changes, allowed=CHAT_EDITABLE)
        except SettingsError as err:
            return str(err), True
        return json.dumps({"ok": True, "updated": applied}, ensure_ascii=False), False

    async def ask(self, conversation_id: str, text: str,
                  ui_language: str | None = None) -> dict[str, Any]:
        # Snapshot for the whole turn: a settings change mid-turn applies from the next message.
        name, language, personality = (self.settings["assistant_name"], self.settings["language"],
                                       self.settings["personality"])
        msg_lang = pick_language(language, ui_language)
        settings_changed = False
        lock = self._locks.setdefault(conversation_id, asyncio.Lock())
        async with lock:
            conv = self._conversation(conversation_id)
            # Work on a copy so a failed turn leaves the stored history valid.
            messages = list(conv.messages)
            messages.append({"role": "user", "content": f"{self._context_line()}\n{text}"})
            actions: list[dict[str, Any]] = []
            try:
                for _ in range(MAX_STEPS):
                    result = await self.cloud.step(messages, name, language, personality)
                    content = result.get("content", [])
                    messages.append({"role": "assistant", "content": content})
                    stop = result.get("stop_reason")

                    if stop == "refusal":
                        conv.messages = []  # a refused turn can't be continued cleanly
                        return {"reply": localize("refusal", msg_lang), "actions": actions}

                    tool_uses = [b for b in content if b.get("type") == "tool_use"]
                    if stop == "tool_use" and tool_uses:
                        outputs = await asyncio.gather(*(self._run_tool(b) for b in tool_uses))
                        results = []
                        for block, (out, is_err) in zip(tool_uses, outputs):
                            if block["name"] == "call_service":
                                actions.append({"call": block.get("input"), "ok": not is_err})
                            if block["name"] == "update_settings" and not is_err:
                                settings_changed = True
                            results.append({"type": "tool_result", "tool_use_id": block["id"],
                                            "content": out, "is_error": is_err})
                        messages.append({"role": "user", "content": results})
                        continue

                    reply = " ".join(b.get("text", "") for b in content
                                     if b.get("type") == "text").strip()
                    # The system prompt depends on name/language/personality, so a change
                    # starts a fresh conversation rather than editing the cached one.
                    conv.messages = [] if settings_changed else messages
                    return {"reply": reply or "…", "actions": actions,
                            "quota_remaining": result.get("quota_remaining"),
                            "speak": self.should_speak(), "settings_changed": settings_changed}
                conv.messages = []
                return {"reply": localize("too_many_steps", msg_lang), "actions": actions}
            except CloudError as err:
                return {"reply": localize(err.code, msg_lang, err.detail),
                        "actions": actions, "error": err.code}

    async def _run_tool(self, block: dict[str, Any]) -> tuple[str, bool]:
        if block["name"] == "update_settings":
            return self._update_settings(block.get("input") or {})
        return await self.tools.run(block["name"], block.get("input") or {})
