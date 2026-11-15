"""Nestor talking first: alerts, suggestions and reports, with action buttons.

Channels: Telegram (central bot, inline buttons), phones with the Home Assistant
app (actionable notifications), and Home Assistant's own notification list.
A button press comes back here and runs the action under the home's permissions.
"""

from __future__ import annotations

import logging
import secrets
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.components import persistent_notification
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.util import dt as dt_util

from .agent import in_quiet_hours
from .cloud import CloudError
from .const import OPT_NAME, OPT_NOTIFY_TARGETS, OPT_QUIET
from .tools_home import ToolError

if TYPE_CHECKING:
    from . import NestorRuntime

_LOGGER = logging.getLogger(__name__)
ACTION_TTL = 6 * 3600
MOBILE_EVENT = "mobile_app_notification_action"


@dataclass
class PendingAction:
    action: dict[str, Any]
    label: str
    created: float = field(default_factory=lambda: time.monotonic())


class Notifier:
    def __init__(self, runtime: "NestorRuntime") -> None:
        self.rt = runtime
        self.hass: HomeAssistant = runtime.hass
        self._actions: dict[str, PendingAction] = {}
        self._held: list[tuple[str, list[tuple[str, dict]], str | None]] = []
        self.sent_log: list[dict[str, Any]] = []  # recent notifications, for the panel/tests

    @callback
    def async_start(self) -> None:
        self.rt.entry.async_on_unload(
            self.hass.bus.async_listen(MOBILE_EVENT, self._on_mobile_action))

    # ---- targets --------------------------------------------------------

    def phone_targets(self) -> list[str]:
        configured = self.rt.options.get(OPT_NOTIFY_TARGETS)
        available = [s for s in self.hass.services.async_services_for_domain("notify")
                     if s.startswith("mobile_app_")]
        if configured is None:
            return available
        return [s for s in configured if s in available]

    # ---- sending --------------------------------------------------------

    async def send(self, text: str, *, buttons: list[tuple[str, dict[str, Any]]] | None = None,
                   urgent: bool = False, key: str | None = None) -> None:
        """Send to every channel. `buttons` = [(label, action)], action as in run_action()."""
        buttons = buttons or []
        quiet = in_quiet_hours(self.rt.options.get(OPT_QUIET), dt_util.now().time())
        if quiet and not urgent:
            self._held.append((text, buttons, key))
            return
        await self._deliver(text, buttons, urgent, key)

    async def flush_held(self) -> None:
        held, self._held = self._held, []
        for text, buttons, key in held:
            await self._deliver(text, buttons, False, key)

    async def _deliver(self, text: str, buttons: list[tuple[str, dict]], urgent: bool,
                       key: str | None) -> None:
        name = self.rt.options.get(OPT_NAME, "Nestor")
        ids = []
        for label, action in buttons:
            action_id = secrets.token_hex(4)
            self._actions[action_id] = PendingAction(action, label)
            ids.append((action_id, label))
        self._expire()
        self.sent_log.append({"text": text, "buttons": [l for _, l in ids], "urgent": urgent,
                              "at": time.time()})
        del self.sent_log[:-50]

        delivered = False
        try:
            tg_buttons = [{"text": label, "data": f"a:{aid}"} for aid, label in ids]
            if ids:
                tg_buttons.append({"text": "✖", "data": f"x:{ids[0][0]}"})
            delivered = await self.rt.cloud.telegram_notify(text, tg_buttons) > 0
        except CloudError:
            pass

        for target in self.phone_targets():
            data: dict[str, Any] = {"title": name, "message": text}
            if ids:
                data["data"] = {"actions": [{"action": f"NESTOR_{aid}", "title": label}
                                            for aid, label in ids]}
            if urgent:
                data.setdefault("data", {})["push"] = {"interruption-level": "critical"}
                data["data"]["ttl"] = 0
                data["data"]["priority"] = "high"
            try:
                await self.hass.services.async_call("notify", target, data, blocking=False)
                delivered = True
            except Exception as err:
                _LOGGER.warning("Couldn't notify %s: %s", target, err)

        if urgent or not delivered:
            persistent_notification.async_create(self.hass, text, title=name,
                                                 notification_id=f"nestor_{key or secrets.token_hex(3)}")

    def _expire(self) -> None:
        now = time.monotonic()
        for aid in [a for a, p in self._actions.items() if now - p.created > ACTION_TTL]:
            self._actions.pop(aid)

    # ---- button presses -------------------------------------------------

    @callback
    def _on_mobile_action(self, event: Event) -> None:
        action = str(event.data.get("action", ""))
        if action.startswith("NESTOR_"):
            self.hass.async_create_task(self.run_action(action[7:]))

    async def handle_callback(self, data: str) -> str:
        kind, _, action_id = data.partition(":")
        if kind == "x":
            self._actions.pop(action_id, None)
            return "OK, I'll leave it."
        return await self.run_action(action_id)

    async def run_action(self, action_id: str) -> str:
        pending = self._actions.pop(action_id, None)
        if pending is None:
            return "That button has expired. Just tell me what you'd like."
        action = pending.action
        try:
            kind = action.get("type")
            if kind == "service":
                await self.rt.home.call_service(action["domain"], action["service"],
                                                action["entity_ids"], action.get("data"))
                self.rt.stats.inc("actions")
                if action.get("saving_kwh"):
                    self.rt.stats.add_saving(action["saving_kwh"])
                return f"Done: {pending.label}."
            if kind == "automation":
                await self.rt.automations.create(**action["automation"])
                self.rt.stats.inc("automations")
                self.rt.stats.inc("suggestions_accepted")
                return "Done — it's automatic from now on."
            if kind == "reload_entry":
                await self.hass.config_entries.async_reload(action["entry_id"])
                return "Restarted it. I'll check again later."
            if kind == "snooze":
                self.rt.watchers.snooze(action["rule"], action.get("entity_id"), action["hours"])
                return "OK, I won't mention it for a while."
        except ToolError as err:
            return str(err)
        except Exception as err:  # never let a button crash anything
            _LOGGER.warning("Notification action failed: %s", err)
            return "Sorry, that didn't work."
        return "Done."
