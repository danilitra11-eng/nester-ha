"""The conversation loop: cloud step -> run tools locally -> cloud step ... -> reply.

Tools run here, inside Home Assistant, under the owner's permissions, the plan's
features and the speaker's profile (family members can be restricted; guests only
get the basics). Risky actions need the user's confirmation in a *later* message:
the tool returns a token that only becomes valid after the user speaks again.
"""

from __future__ import annotations

import asyncio
import json
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, time as dtime
from typing import TYPE_CHECKING, Any

from homeassistant.core import Context
from homeassistant.util import dt as dt_util

from .cloud import CloudError
from .const import (CHAT_EDITABLE, LANGUAGES, OPT_LANGUAGE, OPT_NAME, OPT_PERMISSIONS,
                    OPT_PERSONALITY, OPT_PROFILES, OPT_QUIET, OPT_SPEAK, OPT_VACATION,
                    PERMISSION_GROUPS, PERSONALITIES)
from .i18n import localize, pick_language
from .tools_home import ToolError, allowed_domains

if TYPE_CHECKING:
    from . import NestorRuntime

MAX_STEPS = 12
MAX_HISTORY = 40
IDLE_RESET_SECONDS = 600
CONFIRM_TTL = 600
GUEST_DEFAULT_GROUPS = ["lights", "climate", "media", "covers"]

# capability -> (permission needed or None, plan feature needed)
CAPABILITIES = {
    "structure": ("structure", "structure"),
    "design": ("design", "design"),
    "automations": ("automations", "automations"),
    "vision": ("cameras", "vision"),
    "memory": (None, "memory"),
    "vacation": (None, "vacation"),
    "doctor": (None, "doctor"),
}
READ_ONLY_TOOLS = {"find_entities", "get_state", "list_structure", "list_dashboards",
                   "get_dashboard", "list_themes", "list_memories", "list_automations",
                   "list_cameras", "home_health", "activity_summary", "look_at_camera"}


@dataclass
class Conversation:
    messages: list[dict[str, Any]] = field(default_factory=list)
    last_used: float = field(default_factory=lambda: time.monotonic())
    turn: int = 0


@dataclass
class Pending:
    action: str
    args: dict[str, Any]
    summary: str
    conversation_id: str
    issued_turn: int
    issued_at: float = field(default_factory=lambda: time.monotonic())


@dataclass
class Speaker:
    name: str | None = None
    guest: bool = False


def in_quiet_hours(quiet: dict[str, str] | None, now: dtime) -> bool:
    if not quiet:
        return False
    start, end = dtime.fromisoformat(quiet["start"]), dtime.fromisoformat(quiet["end"])
    if start <= end:
        return start <= now < end
    return now >= start or now < end


def validate_setting(key: str, value: Any) -> Any:
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
    def __init__(self, runtime: "NestorRuntime") -> None:
        self.rt = runtime
        self.hass = runtime.hass
        self._convs: dict[str, Conversation] = {}
        self._locks: dict[str, asyncio.Lock] = {}
        self._pending: dict[str, Pending] = {}

    @property
    def options(self) -> dict[str, Any]:
        return self.rt.options

    def reset(self, conversation_id: str) -> None:
        self._convs.pop(conversation_id, None)

    def should_speak(self) -> bool:
        return bool(self.options.get(OPT_SPEAK)) and not in_quiet_hours(
            self.options.get(OPT_QUIET), dt_util.now().time())

    def should_speak_anytime(self) -> bool:
        """For replies to voice messages: speak unless it's quiet hours."""
        return not in_quiet_hours(self.options.get(OPT_QUIET), dt_util.now().time())

    # ---- who may do what -------------------------------------------------

    def capabilities(self, speaker: Speaker | None = None) -> list[str]:
        if speaker and speaker.guest:
            return []
        perms = self.options.get(OPT_PERMISSIONS, [])
        feats = self.rt.features
        return [cap for cap, (perm, feat) in CAPABILITIES.items()
                if feat in feats and (perm is None or perm in perms)]

    def allowed_for(self, speaker: Speaker) -> set[str]:
        base = set(self.rt.home.allowed)
        profiles = self.options.get(OPT_PROFILES) or {}
        profile = profiles.get(speaker.name or "", {}) if speaker.name else {}
        if speaker.guest:
            return base & allowed_domains(profile.get("allowed", GUEST_DEFAULT_GROUPS))
        blocked = profile.get("blocked", [])
        return base - allowed_domains(blocked) if blocked else base

    async def _speaker_from_context(self, context: Context) -> str | None:
        if context.user_id:
            user = await self.hass.auth.async_get_user(context.user_id)
            return user.name if user else None
        return None

    # ---- context --------------------------------------------------------

    def _conversation(self, cid: str) -> Conversation:
        conv = self._convs.get(cid)
        if (conv is None or len(conv.messages) > MAX_HISTORY
                or time.monotonic() - conv.last_used > IDLE_RESET_SECONDS):
            conv = Conversation()
            self._convs[cid] = conv
        conv.last_used = time.monotonic()
        return conv

    def _context_line(self, speaker: Speaker, caps: list[str]) -> str:
        opts = self.options
        now: datetime = dt_util.now()
        unit = self.hass.config.units.temperature_unit
        quiet = opts.get(OPT_QUIET)
        quiet_txt = f"{quiet['start']}-{quiet['end']}" if quiet else "none"
        groups = [g for g in PERMISSION_GROUPS
                  if set(PERMISSION_GROUPS[g]) & self.allowed_for(speaker)]
        lines = [f"[Home local time: {now:%A %Y-%m-%d %H:%M}; temperatures in {unit}]",
                 f"[Your settings: personality {opts.get(OPT_PERSONALITY)}; language "
                 f"{opts.get(OPT_LANGUAGE)}; read replies aloud "
                 f"{'on' if opts.get(OPT_SPEAK) else 'off'}; quiet hours {quiet_txt}; "
                 f"vacation mode {'on' if opts.get(OPT_VACATION) else 'off'}]",
                 f"[Speaking: {speaker.name or 'unknown household member'}"
                 f"{' (GUEST: only basic device control, no settings or changes to the home)' if speaker.guest else ''}; "
                 f"may control: {', '.join(groups) or 'nothing'}; extra abilities: "
                 f"{', '.join(caps) or 'none'}]"]
        if "memory" in caps:
            mem = self.rt.memory.context_text(speaker.name)
            if mem:
                lines.append(mem)
        return "\n".join(lines)

    # ---- confirmations --------------------------------------------------

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
        rt = self.rt
        if action == "delete_structure":
            return await rt.home.delete_structure(**args)
        if action == "delete_dashboard":
            return await rt.design.delete_dashboard(**args)
        if action == "save_dashboard":
            return await rt.design.save_dashboard(**args)
        if action == "delete_automation":
            return await rt.automations.delete(**args)
        raise ToolError(f"Unknown action {action}")

    async def _update_settings(self, changes: dict[str, Any]) -> str:
        cleaned = {}
        for key, value in changes.items():
            if key not in CHAT_EDITABLE:
                raise ToolError(f"'{key}' can only be changed by the owner in Nestor's settings.")
            if value is None and key != OPT_QUIET:
                continue
            cleaned[key] = validate_setting(key, value)
        await self.rt.async_update_options(cleaned)
        return json.dumps({"ok": True, "updated": cleaned}, ensure_ascii=False)

    # ---- tools ----------------------------------------------------------

    async def run_tool(self, name: str, args: dict[str, Any], *, cid: str, turn: int,
                       context: Context, speaker: Speaker) -> tuple[Any, bool]:
        rt = self.rt
        caps = self.capabilities(speaker)

        def need(cap: str, what: str) -> None:
            if cap not in caps:
                raise ToolError(f"{what} isn't available"
                                + (" for guests." if speaker.guest else
                                   ": the owner hasn't allowed it, or the plan doesn't include it."))
        try:
            if name == "find_entities":
                return await rt.home.find_entities(**args), False
            if name == "get_state":
                return await rt.home.get_state(**args), False
            if name == "call_service":
                out = await rt.home.call_service(**args, context=context,
                                                 allowed=self.allowed_for(speaker))
                rt.stats.inc("actions")
                return out, False
            if name == "update_settings":
                if speaker.guest:
                    raise ToolError("Guests can't change settings.")
                return await self._update_settings(args), False
            if name == "confirm_action":
                return await self._confirm(args.get("token", ""), cid, turn), False
            if name == "activity_summary":
                return json.dumps(rt.stats.summary(price=float(self.options.get(
                    "energy_price", 0.17)))), False

            if name in ("remember", "forget", "list_memories"):
                need("memory", "Memory")
                if name == "remember":
                    return await rt.memory.remember(args.get("fact", ""),
                                                    args.get("person") or None), False
                if name == "forget":
                    return await rt.memory.forget(args.get("id", "")), False
                return await rt.memory.list_memories(), False

            if name in STRUCTURE_TOOLS:
                need("structure", "Editing the home's structure")
                if name == "delete_area_or_floor":
                    summary = rt.home.describe_delete(args["kind"], args["name"])
                    return self._need_confirmation("delete_structure", args, summary,
                                                   cid, turn), False
                return await getattr(rt.home, name)(**args), False

            if name in DESIGN_TOOLS:
                need("design", "Editing dashboards and design")
                if name in ("create_dashboard", "save_dashboard"):
                    rt.stats.inc("actions")
                if name == "save_dashboard" and not rt.design.is_nestor_dashboard(
                        args.get("url_path")):
                    return self._need_confirmation(
                        "save_dashboard", args,
                        f"change the existing dashboard '{args.get('url_path')}' (a backup is "
                        "kept and can be restored)", cid, turn), False
                if name == "delete_dashboard":
                    return self._need_confirmation(
                        "delete_dashboard", args,
                        f"delete the dashboard '{args.get('url_path')}'", cid, turn), False
                return await getattr(rt.design, name)(**args), False

            if name in AUTOMATION_TOOLS:
                need("automations", "Creating automations")
                if name == "create_automation":
                    out = await rt.automations.create(**args)
                    rt.stats.inc("automations")
                    return out, False
                if name == "list_automations":
                    return await rt.automations.list_automations(), False
                if name == "set_automation_enabled":
                    return await rt.automations.set_enabled(**args), False
                if name == "delete_automation":
                    return self._need_confirmation(
                        "delete_automation", args,
                        f"delete the automation {args.get('automation_id')}", cid, turn), False

            if name in ("look_at_camera", "list_cameras"):
                need("vision", "Looking through cameras")
                if name == "list_cameras":
                    return await rt.cameras.list_cameras(), False
                return await rt.cameras.look(args["entity_id"], args.get("question")), False

            if name == "set_vacation_mode":
                need("vacation", "Vacation mode")
                await rt.async_update_options({OPT_VACATION: bool(args.get("enabled"))})
                return json.dumps({"ok": True, "vacation_mode": bool(args.get("enabled"))}), False

            if name == "home_health":
                need("doctor", "The home check-up")
                return json.dumps(await rt.watchers.health_check(), default=str), False

            raise ToolError(f"Unknown tool {name}.")
        except ToolError as err:
            return str(err), True
        except (TypeError, KeyError) as err:
            return f"Bad arguments for {name}: {err}", True

    # ---- main loop ---------------------------------------------------

    async def ask(self, conversation_id: str, text: str, *, ui_language: str | None = None,
                  context: Context | None = None, speaker: str | None = None,
                  guest: bool = False) -> dict[str, Any]:
        opts = self.options
        name, language, personality = (opts.get(OPT_NAME, "Nestor"), opts.get(OPT_LANGUAGE, "auto"),
                                       opts.get(OPT_PERSONALITY, "butler"))
        msg_lang = pick_language(language, ui_language)
        context = context or Context()
        who = Speaker(speaker or await self._speaker_from_context(context), guest)
        caps = self.capabilities(who)
        settings_changed = False
        self.rt.stats.inc("commands")
        lock = self._locks.setdefault(conversation_id, asyncio.Lock())
        async with lock:
            conv = self._conversation(conversation_id)
            conv.turn += 1
            turn = conv.turn
            messages = list(conv.messages)
            messages.append({"role": "user", "content": f"{self._context_line(who, caps)}\n{text}"})
            actions: list[dict[str, Any]] = []
            try:
                for _ in range(MAX_STEPS):
                    result = await self.rt.cloud.step(messages, name=name, language=language,
                                                      personality=personality, capabilities=caps)
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
                                          turn=turn, context=context, speaker=who)
                            for b in tool_uses))
                        results = []
                        for block, (out, is_err) in zip(tool_uses, outputs):
                            if block["name"] not in READ_ONLY_TOOLS:
                                actions.append({"tool": block["name"],
                                                "input": block.get("input"), "ok": not is_err})
                            if block["name"] in ("update_settings", "set_vacation_mode") \
                                    and not is_err:
                                settings_changed = True
                            results.append({"type": "tool_result", "tool_use_id": block["id"],
                                            "content": out, "is_error": is_err})
                        messages.append({"role": "user", "content": results})
                        continue

                    reply = " ".join(b.get("text", "") for b in content
                                     if b.get("type") == "text").strip()
                    # drop pictures from the kept history: they're big and already described
                    conv.messages = [] if settings_changed else _without_images(messages)
                    return {"reply": reply or "…", "actions": actions,
                            "quota_remaining": result.get("quota_remaining"),
                            "speak": self.should_speak(), "settings_changed": settings_changed}
                conv.messages = []
                return {"reply": localize("too_many_steps", msg_lang), "actions": actions,
                        "speak": False}
            except CloudError as err:
                if err.code == "plan_feature":
                    self.rt.schedule_feature_refresh()
                return {"reply": localize(err.code, msg_lang, err.detail), "actions": actions,
                        "error": err.code, "speak": False}


def _without_images(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Conversations with a camera picture start fresh next time instead of resending it."""
    for m in messages:
        content = m.get("content")
        if isinstance(content, list):
            for block in content:
                inner = block.get("content") if isinstance(block, dict) else None
                if isinstance(inner, list) and any(i.get("type") == "image" for i in inner):
                    return []
    return messages


STRUCTURE_TOOLS = {"list_structure", "create_floor", "create_area", "update_area", "assign_area",
                   "rename_entity", "delete_area_or_floor"}
DESIGN_TOOLS = {"list_dashboards", "get_dashboard", "create_dashboard", "save_dashboard",
                "undo_dashboard", "delete_dashboard", "list_themes", "set_theme"}
AUTOMATION_TOOLS = {"create_automation", "list_automations", "set_automation_enabled",
                    "delete_automation"}
