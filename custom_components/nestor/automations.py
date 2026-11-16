"""Automations in plain language: Nestor writes real Home Assistant automations
(automations.yaml, exactly like the automation editor does) and keeps track of
the ones it made. Every action inside an automation must be one Nestor itself
is allowed to perform, so an automation can't sneak past the permissions."""

from __future__ import annotations

import json
import re
import os
import secrets
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.storage import Store

from .const import FORBIDDEN_DOMAINS, RISKY_COVER_CLASSES, RISKY_SERVICES
from .tools_home import ToolError

AUTOMATION_FILE = "automations.yaml"
SAFE_HELPER_ACTIONS = {"delay", "wait_template", "wait_for_trigger", "choose", "if", "then",
                       "else", "repeat", "sequence", "parallel", "variables", "stop", "event"}
ALWAYS_OK_DOMAINS = {"notify", "persistent_notification", "tts", "input_number",
                     "input_text", "input_select", "input_datetime", "counter", "timer"}


SERVICE_NAME_RE = re.compile(r"[a-z0-9_]+\.[a-z0-9_]+", re.IGNORECASE)
TEMPLATE_KEYS = {"service_template", "action_template"}


def _called_services(node: Any) -> set[str]:
    """Every service an action tree calls (action: light.turn_on / service: ...).

    Raises ToolError for a service name that is computed at run time (a template, a
    variable), since it can't be checked against the permissions in advance.
    """
    found: set[str] = set()
    if isinstance(node, dict):
        if TEMPLATE_KEYS & node.keys():
            raise ToolError("Automations must name each action directly, not with a template.")
        if "device_id" in node and "domain" in node and "type" in node \
                and "condition" not in node and "trigger" not in node:
            # A device action ({device_id, domain: lock, type: unlock}) calls a service too.
            found.add(f"{str(node['domain']).lower()}.{str(node['type']).lower()}")
        if isinstance(node.get("scene"), str):
            found.add("scene.turn_on")
        for key in ("action", "service"):
            value = node.get(key)
            if value is None:
                continue
            if not isinstance(value, str) or not SERVICE_NAME_RE.fullmatch(value.strip()):
                raise ToolError("Automations must name each action directly, like "
                                "light.turn_on, not with a template or variable.")
            found.add(value.strip().lower())
        for value in node.values():
            found |= _called_services(value)
    elif isinstance(node, list):
        for item in node:
            found |= _called_services(item)
    return found


def _called_domains(node: Any) -> set[str]:
    return {svc.split(".", 1)[0] for svc in _called_services(node)}


class Automations:
    def __init__(self, hass: HomeAssistant, entry_id: str, allowed_domains) -> None:
        self.hass = hass
        self._allowed = allowed_domains  # callable -> set[str]
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"nestor.automations.{entry_id}")
        self.created: list[str] = []

    async def async_load(self) -> None:
        self.created = (await self._store.async_load() or {}).get("created", [])

    def _save(self) -> None:
        self._store.async_delay_save(lambda: {"created": self.created}, 1)

    @property
    def path(self) -> str:
        return self.hass.config.path(AUTOMATION_FILE)

    def _read(self) -> list[dict[str, Any]]:
        from homeassistant.util.yaml import load_yaml
        if not os.path.exists(self.path):
            raise ToolError("This Home Assistant doesn't keep automations in automations.yaml, "
                            "so I can't add automations here. They can be created in "
                            "Settings > Automations instead.")
        data = load_yaml(self.path) or []
        if not isinstance(data, list):
            raise ToolError("automations.yaml isn't in the usual format; I won't touch it.")
        return data

    def _write(self, data: list[dict[str, Any]]) -> None:
        from homeassistant.util.file import write_utf8_file_atomic
        from homeassistant.util.yaml import dump
        write_utf8_file_atomic(self.path, dump(data))

    def _check_actions(self, actions: Any) -> None:
        allowed = self._allowed() | ALWAYS_OK_DOMAINS
        services = _called_services(actions)
        for domain in {svc.split(".", 1)[0] for svc in services}:
            if domain in FORBIDDEN_DOMAINS or domain not in allowed:
                raise ToolError(f"This automation would control '{domain}', which I'm not "
                                "allowed to do. The owner can allow it in Nestor's settings.")
        risky = services & (RISKY_SERVICES | {"alarm_control_panel.disarm", "cover.open"})
        if risky or self._opens_risky_cover(actions):
            raise ToolError("For safety I can't create automations that unlock doors, disarm "
                            "the alarm or open the garage/gate. The owner can create one in "
                            "Settings > Automations.")

    def _opens_risky_cover(self, node: Any) -> bool:
        if isinstance(node, list):
            return any(self._opens_risky_cover(n) for n in node)
        if not isinstance(node, dict):
            return False
        svc = str(node.get("action") or node.get("service") or "").lower()
        if svc in ("cover.open_cover", "cover.set_cover_position", "cover.toggle"):
            target = node.get("target") or {}
            ids = target.get("entity_id") or (node.get("data") or {}).get("entity_id") \
                or node.get("entity_id") or []
            ids = [ids] if isinstance(ids, str) else list(ids)
            if not ids or target.get("area_id") or target.get("device_id") or target.get("floor_id"):
                return True  # can't tell which covers: treat as risky
            for eid in ids:
                st = self.hass.states.get(eid)
                if st is None or st.attributes.get("device_class") in RISKY_COVER_CLASSES:
                    return True
        return any(self._opens_risky_cover(v) for v in node.values())

    async def create(self, alias: str, triggers: list, actions: list,
                     description: str = "", conditions: list | None = None,
                     mode: str = "single") -> str:
        from homeassistant.components.automation.config import async_validate_config_item
        self._check_actions(actions)
        auto_id = f"nestor_{secrets.token_hex(5)}"
        config = {"id": auto_id, "alias": alias[:120],
                  "description": (description + " (created by Nestor)").strip(),
                  "triggers": triggers, "conditions": conditions or [], "actions": actions,
                  "mode": mode}
        validated = await async_validate_config_item(self.hass, auto_id, config)
        if validated is not None and getattr(validated, "validation_error", None):
            raise ToolError(f"That automation isn't valid: {validated.validation_error}")
        data = await self.hass.async_add_executor_job(self._read)
        data.append(config)
        await self.hass.async_add_executor_job(self._write, data)
        await self.hass.services.async_call("automation", "reload", {"id": auto_id},
                                            blocking=True)
        self.created.append(auto_id)
        self._save()
        return json.dumps({"ok": True, "id": auto_id, "alias": alias})

    def _entity_id(self, auto_id: str) -> str | None:
        return er.async_get(self.hass).async_get_entity_id("automation", "automation", auto_id)

    async def list_automations(self) -> str:
        data = await self.hass.async_add_executor_job(self._read)
        out = []
        for item in data:
            if item.get("id") in self.created:
                ent = self._entity_id(item["id"])
                st = self.hass.states.get(ent) if ent else None
                out.append({"id": item["id"], "alias": item.get("alias"),
                            "description": item.get("description"),
                            "enabled": st.state == "on" if st else None,
                            "last_triggered": st.attributes.get("last_triggered") if st else None})
        return json.dumps({"automations": out}, ensure_ascii=False, default=str)

    async def set_enabled(self, automation_id: str, enabled: bool) -> str:
        if automation_id not in self.created:
            raise ToolError("I can only switch automations I created.")
        ent = self._entity_id(automation_id)
        if not ent:
            raise ToolError("That automation isn't loaded.")
        await self.hass.services.async_call("automation", "turn_on" if enabled else "turn_off",
                                            {"entity_id": ent}, blocking=True)
        return json.dumps({"ok": True, "enabled": enabled})

    async def delete(self, automation_id: str) -> str:
        if automation_id not in self.created:
            raise ToolError("I can only delete automations I created.")
        data = await self.hass.async_add_executor_job(self._read)
        data = [d for d in data if d.get("id") != automation_id]
        await self.hass.async_add_executor_job(self._write, data)
        if ent := self._entity_id(automation_id):
            er.async_get(self.hass).async_remove(ent)
        await self.hass.services.async_call("automation", "reload", blocking=True)
        self.created.remove(automation_id)
        self._save()
        return json.dumps({"ok": True, "deleted": automation_id})

    def existing_patterns(self) -> list[str]:
        """Entity ids already used by Nestor automations (to avoid duplicate suggestions)."""
        try:
            data = self._read()
        except ToolError:
            return []
        text = json.dumps([d for d in data if d.get("id") in self.created])
        return [e for e in self.hass.states.async_entity_ids() if e in text]
