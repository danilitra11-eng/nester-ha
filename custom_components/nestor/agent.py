"""The conversation loop: cloud step -> run tools locally -> cloud step ... -> reply.

Tools run here, inside Home Assistant, under the owner's permissions. The cloud
only decides what to do. Risky actions (deleting rooms, overwriting a dashboard
Nestor didn't create) need the user's confirmation in a *later* message: the
tool returns a token that only becomes valid after the user speaks again.
"""

from __future__ import annotations

import asyncio
import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, time as dtime
from typing import Any, Awaitable, Callable

from homeassistant.core import Context, HomeAssistant
from homeassistant.util import dt as dt_util

from .cloud import CloudClient, CloudError
from .const import (CHAT_EDITABLE, LANGUAGES, OPT_LANGUAGE, OPT_NAME, OPT_PERMISSIONS,
                    OPT_PERSONALITY, OPT_QUIET, OPT_SPEAK, PERMISSION_DESIGN,
                    PERMISSION_STRUCTURE, PERSONALITIES)
from .i18n import localize, pick_language
from .tools_design import DesignTools
from .tools_home import HomeTools, ToolError

MAX_STEPS = 10
MAX_HISTORY = 40
IDLE_RESET_SECONDS = 600
CONFIRM_TTL = 600


@dataclass
class Conversation:
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_used: float = field(default_factory=time.monotonic)
    turn: int = 0


@dataclass
class Pending:
    action: str
    args: dict[str, Any]
    summary: str
    conversation_id: str
    issued_turn: int
    issued_at: float = field(default_factory=time.monotonic)


def in_quiet_hours(quiet: dict[str, str] | None, now: dtime) -> bool:
    if not quiet:
        return False
    start, end = dtime.fromisoformat(quiet["start"]), dtime.fromisoformat(quiet["end"])
    if start <= end:
        return start <= now < end
    return now >= start or now < end


def validate_setting(key: str, value: Any) -> Any:
    import re
    if key == OPT_NAME:
        name = " ".join(str(value).split())[:40]
        if not name:
            raise ToolError("The name can't be empty.")
        return name
    if key == OPT_LANGUAGE and value in LANGUAGES:
        return value
    if key == OPT_PERSONALITY and value in PERSONALITIES:
        return value
    if key == OPT_SPEAK and isinstance(value, bool):
        return value
    if key == OPT_QUIET:
        if value is None:
            return None
        hhmm = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
        if isinstance(value, dict) and hhmm.match(str(value.get("start", ""))) \
                and hhmm.match(str(value.get("end", ""))):
            return {"start": value["start"], "end": value["end"]}
    raise ToolError(f"Invalid value for {key}: {value!r}")


class Agent:
    def __init__(self, hass: HomeAssistant, cloud: CloudClient,
                 get_options: Callable[[], dict[str, Any]],
                 update_options: Callable[[dict[str, Any]], Awaitable[None]],
                 home: HomeTools, design: DesignTools) -> None:
        self.hass = hass
        self.cloud = cloud
        self._get_options = get_options
        self._update_options = update_options
        self.home = home
        self.design = design
        self._convs: dict[str, Conversation] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pending: dict[str, Pending] = {}

    @property
    def options(self) -> dict[str, Any]:
        return self._get_options()

    def reset(self, conversation_id: str) -> None:
        self._convs.pop(conversation_id, None)

    def should_speak(self) -> bool:
        return bool(self.options.get(OPT_SPEAK)) and not in_quiet_hours(
            self.options.get(OPT_QUIET), dt_util.now().time())

    def should_speak_anytime(self) -> bool:
        """For replies to voice messages: speak unless it's quiet hours."""
        return not in_quiet_hours(self.options.get(OPT_QUIET), dt_util.now().time())

    def capabilities(self) -> list[str]:
        perms = self.options.get(OPT_PERMISSIONS, [])
        return [p for p in (PERMISSION_STRUCTURE, PERMISSION_DESIGN) if p in perms]

    def _conversation(self, cid: str) -> Conversation:
        conv = self._convs.get(cid)
        if (conv is None or len(conv.messages) > MAX_HISTORY
                or time.monotonic() - conv.last_used > IDLE_RESET_SECONDS):
            conv = Conversation()
            self._convs[cid] = conv
        conv.last_used = time.monotonic()
        return conv

    def _context_line(self) -> str:
        opts = self.options
        now: datetime = dt_util.now()
        unit = self.hass.config.units.temperature_unit
        quiet = opts.get(OPT_QUIET)
        quiet_txt = f"{quiet['start']}-{quiet['end']}" if quiet else "none"
        caps = ", ".join(self.capabilities()) or "device control only"
        return (f"[Home local time: {now:%A %Y-%m-%d %H:%M}; temperatures in {unit}]\n"
                f"[Your settings: personality {opts.get(OPT_PERSONALITY)}; language "
                f"{opts.get(OPT_LANGUAGE)}; read replies aloud "
                f"{'on' if opts.get(OPT_SPEAK) else 'off'}; quiet hours {quiet_txt}; "
                f"permissions: {caps}]")

    # ---- tools ----------------------------------------------------------

    def _need_confirmation(self, action: str, args: dict[str, Any], summary: str,
                           cid: str, turn: int) -> str:
        token = secrets.token_hex(4)
        self._pending[token] = Pending(action, args, summary, cid, turn)
        return json.dumps({
            "needs_confirmation": True, "token": token, "action": summary,
            "instruction": "Do not do it yet. Ask the user to confirm this exact action in plain "
                           "words. Only if their NEXT message agrees, call confirm_action with "
                           "this token.",
        })

    async def _confirm(self, token: str, cid: str, turn: int) -> str:
        pending = self._pending.get(token)
        if pending is None or pending.conversation_id != cid:
            raise ToolError("Unknown or expired confirmation. Ask again from the start.")
        if time.monotonic() - pending.issued_at > CONFIRM_TTL:
            self._pending.pop(token, None)
            raise ToolError("The confirmation expired. Ask the user again.")
        if turn <= pending.issued_turn:
            raise ToolError("The user hasn't confirmed yet. Ask them and wait for their reply.")
        self._pending.pop(token)
        return await self._execute(pending.action, pending.args)

    async def _execute(self, action: str, args: dict[str, Any]) -> str:
        if action == "delete_structure":
            return await self.home.delete_structure(**args)
        if action == "delete_dashboard":
            return await self.design.delete_dashboard(**args)
        if action == "save_dashboard":
            return await self.design.save_dashboard(**args)
        raise ToolError(f"Unknown action {action}")

    async def _update_settings(self, changes: dict[str, Any]) -> str:
        cleaned = {}
        for key, value in changes.items():
            if key not in CHAT_EDITABLE:
                raise ToolError(f"'{key}' can only be changed by the owner in Nestor's settings.")
            if value is None and key != OPT_QUIET:
                continue
            cleaned[key] = validate_setting(key, value)
        await self._update_options(cleaned)
        return json.dumps({"ok": True, "updated": cleaned}, ensure_ascii=False)

    async def run_tool(self, name: str, args: dict[str, Any], *, cid: str, turn: int,
                       context: Context) -> tuple[str, bool]:
        caps = self.capabilities()
        try:
            if name == "find_entities":
                return await self.home.find_entities(**args), False
            if name == "get_state":
                return await self.home.get_state(**args), False
            if name == "call_service":
                return await self.home.call_service(**args, context=context), False
            if name == "update_settings":
                return await self._update_settings(args), False
            if name == "confirm_action":
                return await self._confirm(args.get("token", ""), cid, turn), False

            if name in STRUCTURE_TOOLS:
                if PERMISSION_STRUCTURE not in caps:
                    raise ToolError("The owner hasn't allowed editing the home's structure.")
                if name == "delete_area_or_floor":
                    summary = self.home.describe_delete(args["kind"], args["name"])
                    return self._need_confirmation("delete_structure", args, summary,
                                                   cid, turn), False
                return await getattr(self.home, name)(**args), False

            if name in DESIGN_TOOLS:
                if PERMISSION_DESIGN not in caps:
                    raise ToolError("The owner hasn't allowed editing dashboards and design.")
                if name == "save_dashboard" and not self.design.is_nestor_dashboard(
                        args.get("url_path")):
                    return self._need_confirmation(
                        "save_dashboard", args,
                        f"change the existing dashboard '{args.get('url_path')}' (a backup is "
                        "kept and can be restored)", cid, turn), False
                if name == "delete_dashboard":
                    return self._need_confirmation(
                        "delete_dashboard", args,
                        f"delete the dashboard '{args.get('url_path')}'", cid, turn), False
                return await getattr(self.design, name)(**args), False

            raise ToolError(f"Unknown tool {name}.")
        except ToolError as err:
            return str(err), True
        except TypeError as err:
            return f"Bad arguments for {name}: {err}", True

    # ---- main loop ---------------------------------------------------

    async def ask(self, conversation_id: str, text: str, *, ui_language: str | None = None,
                  context: Context | None = None) -> dict[str, Any]:
        opts = self.options
        name, language, personality = (opts.get(OPT_NAME, "Nestor"), opts.get(OPT_LANGUAGE, "auto"),
                                       opts.get(OPT_PERSONALITY, "butler"))
        msg_lang = pick_language(language, ui_language)
        context = context or Context()
        settings_changed = False
        lock = self._locks.setdefault(conversation_id, asyncio.Lock())
        async with lock:
            conv = self._conversation(conversation_id)
            conv.turn += 1
            turn = conv.turn
            messages = list(conv.messages)
            messages.append({"role": "user", "content": f"{self._context_line()}\n{text}"})
            actions: list[dict[str, Any]] = []
            try:
                for _ in range(MAX_STEPS):
                    result = await self.cloud.step(messages, name=name, language=language,
                                                   personality=personality,
                                                   capabilities=self.capabilities())
                    content = result.get("content", [])
                    messages.append({"role": "assistant", "content": content})
                    stop = result.get("stop_reason")
                    if stop == "refusal":
                        conv.messages = []
                        return {"reply": localize("refusal", msg_lang), "actions": actions,
                                "speak": self.should_speak()}

                    tool_uses = [b for b in content if b.get("type") == "tool_use"]
                    if stop == "tool_use" and tool_uses:
                        outputs = await asyncio.gather(*(
                            self.run_tool(b["name"], b.get("input") or {}, cid=conversation_id,
                                          turn=turn, context=context) for b in tool_uses))
                        results = []
                        for block, (out, is_err) in zip(tool_uses, outputs):
                            if block["name"] not in ("find_entities", "get_state",
                                                     "list_structure", "list_dashboards",
                                                     "get_dashboard", "list_themes"):
                                actions.append({"tool": block["name"],
                                                "input": block.get("input"), "ok": not is_err})
                            if block["name"] == "update_settings" and not is_err:
                                settings_changed = True
                            results.append({"type": "tool_result", "tool_use_id": block["id"],
                                            "content": out, "is_error": is_err})
                        messages.append({"role": "user", "content": results})
                        continue

                    reply = " ".join(b.get("text", "") for b in content
                                     if b.get("type") == "text").strip()
                    conv.messages = [] if settings_changed else messages
                    return {"reply": reply or "…", "actions": actions,
                            "quota_remaining": result.get("quota_remaining"),
                            "speak": self.should_speak(), "settings_changed": settings_changed}
                conv.messages = []
                return {"reply": localize("too_many_steps", msg_lang), "actions": actions,
                        "speak": False}
            except CloudError as err:
                return {"reply": localize(err.code, msg_lang, err.detail), "actions": actions,
                        "error": err.code, "speak": False}


STRUCTURE_TOOLS = {"list_structure", "create_floor", "create_area", "update_area", "assign_area",
                   "rename_entity", "delete_area_or_floor"}
DESIGN_TOOLS = {"list_dashboards", "get_dashboard", "create_dashboard", "save_dashboard",
                "undo_dashboard", "delete_dashboard", "list_themes", "set_theme"}
