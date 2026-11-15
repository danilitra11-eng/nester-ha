"""Talks to Home Assistant Core through the Supervisor proxy, and runs the tools.

Every device action passes through ToolRunner, which enforces the owner's
allowed_domains setting. The cloud only ever sees what these tools return.
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

import aiohttp

SUPERVISOR_URL = "http://supervisor/core/api"

SECURITY_DOMAINS = {"lock", "alarm_control_panel"}
# Never callable from chat, whatever the settings say.
FORBIDDEN_DOMAINS = {"homeassistant", "hassio", "shell_command", "python_script", "rest_command",
                     "recorder", "system_log", "logger", "backup", "pyscript"}
# Read-only noise we don't show to the model.
HIDDEN_DOMAINS = {"update", "persistent_notification", "zone", "conversation", "tts", "stt",
                  "wake_word", "event", "image", "camera", "assist_satellite"}
KEEP_ATTRS = ("friendly_name", "unit_of_measurement", "device_class", "brightness",
              "color_mode", "rgb_color", "color_temp_kelvin", "temperature",
              "current_temperature", "target_temp_high", "target_temp_low", "hvac_modes",
              "hvac_action", "fan_mode", "fan_modes", "preset_mode", "preset_modes",
              "current_position", "volume_level", "is_volume_muted", "media_title",
              "media_artist", "source", "source_list", "percentage", "humidity",
              "battery_level")
SERVICE_RE = re.compile(r"^[a-z0-9_]+$")
MAX_RESULTS = 40

AREA_TEMPLATE = (
    "{% set ns = namespace(o=[]) %}"
    "{% for s in states %}{% set a = area_name(s.entity_id) %}"
    "{% if a %}{% set ns.o = ns.o + [[s.entity_id, a]] %}{% endif %}"
    "{% endfor %}{{ ns.o | tojson }}"
)


class HAError(Exception):
    pass


class HomeAssistant:
    def __init__(self, session: aiohttp.ClientSession, token: str | None = None,
                 base_url: str = SUPERVISOR_URL) -> None:
        self._session = session
        self._base = base_url
        self._headers = {"Authorization": f"Bearer {token or os.environ.get('SUPERVISOR_TOKEN', '')}"}
        self._areas: dict[str, str] = {}
        self._areas_at = 0.0

    async def _request(self, method: str, path: str, payload: Any = None) -> Any:
        async with self._session.request(
            method, f"{self._base}{path}", headers=self._headers, json=payload,
            timeout=aiohttp.ClientTimeout(total=20),
        ) as resp:
            text = await resp.text()
            if resp.status >= 400:
                raise HAError(f"Home Assistant returned {resp.status}: {text[:300]}")
            if "json" in resp.headers.get("Content-Type", ""):
                return json.loads(text)
            return text

    async def states(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/states")

    async def state(self, entity_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/states/{entity_id}")

    async def areas(self) -> dict[str, str]:
        """entity_id -> area name, cached for 5 minutes."""
        if time.monotonic() - self._areas_at > 300:
            try:
                raw = await self._request("POST", "/template", {"template": AREA_TEMPLATE})
                pairs = json.loads(raw) if isinstance(raw, str) else raw
                self._areas = {eid: area for eid, area in pairs}
            except (HAError, ValueError):
                self._areas = {}
            self._areas_at = time.monotonic()
        return self._areas

    async def call_service(self, domain: str, service: str, data: dict[str, Any]) -> list[dict]:
        return await self._request("POST", f"/services/{domain}/{service}", data)

    async def config(self) -> dict[str, Any]:
        return await self._request("GET", "/config")


def _compact(state: dict[str, Any], area: str | None) -> dict[str, Any]:
    attrs = state.get("attributes", {})
    out: dict[str, Any] = {
        "entity_id": state["entity_id"],
        "name": attrs.get("friendly_name", state["entity_id"]),
        "state": state.get("state"),
    }
    if area:
        out["area"] = area
    extra = {k: attrs[k] for k in KEEP_ATTRS if k in attrs and k != "friendly_name"}
    if extra:
        out["attributes"] = extra
    return out


def _norm(text: str) -> str:
    return re.sub(r"[_\.\-]+", " ", text.lower()).strip()


class ToolRunner:
    def __init__(self, ha: HomeAssistant, allowed_domains: list[str], allow_security: bool) -> None:
        self.ha = ha
        self.set_permissions(allowed_domains, allow_security)

    def set_permissions(self, allowed_domains: list[str], allow_security: bool) -> None:
        allowed = {d.strip().lower() for d in allowed_domains if d.strip()}
        allowed -= FORBIDDEN_DOMAINS
        if allow_security:
            allowed |= SECURITY_DOMAINS
        else:
            allowed -= SECURITY_DOMAINS
        self.allowed = allowed

    async def run(self, name: str, args: dict[str, Any]) -> tuple[str, bool]:
        """Execute one tool. Returns (result_text, is_error)."""
        try:
            if name == "find_entities":
                return await self.find_entities(**args), False
            if name == "get_state":
                return await self.get_state(**args), False
            if name == "call_service":
                return await self.call_service(**args), False
            return f"Unknown tool {name}", True
        except TypeError as exc:
            return f"Bad arguments for {name}: {exc}", True
        except PermissionError as exc:
            return str(exc), True
        except HAError as exc:
            return str(exc), True

    async def find_entities(self, query: str = "", domain: str | None = None,
                            area: str | None = None) -> str:
        states, areas = await self.ha.states(), await self.ha.areas()
        words = [w for w in _norm(query).split() if w]
        area_n = _norm(area) if area else None
        scored = []
        for st in states:
            eid = st["entity_id"]
            dom = eid.split(".", 1)[0]
            if dom in HIDDEN_DOMAINS or (domain and dom != domain.lower()):
                continue
            ent_area = areas.get(eid)
            if area_n and (not ent_area or area_n not in _norm(ent_area)):
                continue
            hay = _norm(f"{eid} {st.get('attributes', {}).get('friendly_name', '')} {ent_area or ''}")
            score = sum(1 for w in words if w in hay) if words else 1
            if score:
                scored.append((score, st, ent_area))
        scored.sort(key=lambda t: -t[0])
        results = [_compact(st, a) for _, st, a in scored[:MAX_RESULTS]]
        for r in results:
            r["controllable"] = r["entity_id"].split(".", 1)[0] in self.allowed
        if not results:
            return json.dumps({"results": [], "note": "No match. Try other words, "
                               "the English name, or search by domain only."})
        return json.dumps({"results": results, "truncated": len(scored) > MAX_RESULTS},
                          ensure_ascii=False)

    async def get_state(self, entity_id: str) -> str:
        st = await self.ha.state(entity_id)
        return json.dumps(st, ensure_ascii=False, default=str)[:6000]

    async def call_service(self, domain: str, service: str, entity_ids: list[str],
                           data: dict[str, Any] | None = None) -> str:
        domain, service = domain.lower(), service.lower()
        if not SERVICE_RE.match(domain) or not SERVICE_RE.match(service):
            raise PermissionError("Invalid service name.")
        if domain not in self.allowed:
            raise PermissionError(f"The owner has not allowed controlling '{domain}' devices. "
                                  "They can allow it in the Nestor settings screen.")
        if not entity_ids:
            raise PermissionError("entity_ids must not be empty.")
        for eid in entity_ids:
            if eid.split(".", 1)[0] not in self.allowed:
                raise PermissionError(f"The owner has not allowed controlling {eid}.")
        payload = dict(data or {})
        payload.pop("entity_id", None)
        payload["entity_id"] = entity_ids
        changed = await self.ha.call_service(domain, service, payload)
        summary = [{"entity_id": s.get("entity_id"), "state": s.get("state")}
                   for s in (changed or []) if isinstance(s, dict)]
        return json.dumps({"ok": True, "changed": summary}, ensure_ascii=False)
