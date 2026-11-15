"""Device search/control and home-structure tools, executed inside Home Assistant."""

from __future__ import annotations

import json
import re
from typing import Any

from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceNotFound
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr

from .const import FORBIDDEN_DOMAINS, PERMISSION_GROUPS

HIDDEN_DOMAINS = {"update", "persistent_notification", "zone", "conversation", "tts", "stt",
                  "wake_word", "event", "image", "camera", "assist_satellite", "ai_task"}
KEEP_ATTRS = ("unit_of_measurement", "device_class", "brightness", "color_mode", "rgb_color",
              "color_temp_kelvin", "temperature", "current_temperature", "target_temp_high",
              "target_temp_low", "hvac_modes", "hvac_action", "fan_mode", "fan_modes",
              "preset_mode", "preset_modes", "current_position", "volume_level",
              "is_volume_muted", "media_title", "media_artist", "source", "source_list",
              "percentage", "humidity", "battery_level")
SERVICE_RE = re.compile(r"^[a-z0-9_]+$")
MAX_RESULTS = 40


class ToolError(Exception):
    """A tool failed in a way the model should see (returned as is_error)."""


def _norm(text: str) -> str:
    return re.sub(r"[_\.\-]+", " ", (text or "").lower()).strip()


def allowed_domains(permissions: list[str]) -> set[str]:
    domains: set[str] = set()
    for group in permissions:
        domains.update(PERMISSION_GROUPS.get(group, []))
    return domains - FORBIDDEN_DOMAINS


class HomeTools:
    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.allowed: set[str] = set()

    def set_permissions(self, permissions: list[str]) -> None:
        self.allowed = allowed_domains(permissions)

    # ---- lookups -------------------------------------------------------

    def _area_of(self, entity_id: str) -> str | None:
        ent = er.async_get(self.hass).async_get(entity_id)
        area_id = None
        if ent:
            area_id = ent.area_id
            if not area_id and ent.device_id:
                dev = dr.async_get(self.hass).async_get(ent.device_id)
                area_id = dev.area_id if dev else None
        if not area_id:
            return None
        area = ar.async_get(self.hass).async_get_area(area_id)
        return area.name if area else None

    def _find_area(self, name_or_id: str) -> ar.AreaEntry:
        reg = ar.async_get(self.hass)
        area = reg.async_get_area(name_or_id) or reg.async_get_area_by_name(name_or_id)
        if area is None:
            for a in reg.async_list_areas():
                if _norm(a.name) == _norm(name_or_id):
                    return a
            raise ToolError(f"No area called '{name_or_id}'. Use list_structure to see areas.")
        return area

    def _find_floor(self, name_or_id: str) -> fr.FloorEntry:
        reg = fr.async_get(self.hass)
        floor = reg.async_get_floor(name_or_id) or reg.async_get_floor_by_name(name_or_id)
        if floor is None:
            for f in reg.async_list_floors():
                if _norm(f.name) == _norm(name_or_id):
                    return f
            raise ToolError(f"No floor called '{name_or_id}'. Use list_structure to see floors.")
        return floor

    # ---- device tools --------------------------------------------------

    async def find_entities(self, query: str = "", domain: str | None = None,
                            area: str | None = None) -> str:
        words = [w for w in _norm(query).split() if w]
        area_n = _norm(area) if area else None
        scored = []
        for st in self.hass.states.async_all():
            dom = st.domain
            if dom in HIDDEN_DOMAINS or (domain and dom != domain.lower()):
                continue
            ent_area = self._area_of(st.entity_id)
            if area_n and (not ent_area or area_n not in _norm(ent_area)):
                continue
            hay = _norm(f"{st.entity_id} {st.name} {ent_area or ''}")
            score = sum(1 for w in words if w in hay) if words else 1
            if score:
                scored.append((score, st, ent_area))
        scored.sort(key=lambda t: -t[0])
        results = []
        for _, st, ent_area in scored[:MAX_RESULTS]:
            item: dict[str, Any] = {"entity_id": st.entity_id, "name": st.name, "state": st.state,
                                    "controllable": st.domain in self.allowed}
            if ent_area:
                item["area"] = ent_area
            extra = {k: st.attributes[k] for k in KEEP_ATTRS if k in st.attributes}
            if extra:
                item["attributes"] = extra
            results.append(item)
        if not results:
            return json.dumps({"results": [], "note": "No match. Try other words, the English "
                               "name, or search by domain or area only."})
        return json.dumps({"results": results, "truncated": len(scored) > MAX_RESULTS},
                          ensure_ascii=False, default=str)

    async def get_state(self, entity_id: str) -> str:
        st = self.hass.states.get(entity_id)
        if st is None:
            raise ToolError(f"No entity {entity_id}.")
        return json.dumps({"entity_id": st.entity_id, "name": st.name, "state": st.state,
                           "attributes": dict(st.attributes),
                           "last_changed": st.last_changed.isoformat()},
                          ensure_ascii=False, default=str)[:6000]

    async def call_service(self, domain: str, service: str, entity_ids: list[str],
                           data: dict[str, Any] | None = None,
                           context: Context | None = None,
                           allowed: set[str] | None = None) -> str:
        allowed = self.allowed if allowed is None else allowed
        domain, service = domain.lower(), service.lower()
        if not SERVICE_RE.match(domain) or not SERVICE_RE.match(service):
            raise ToolError("Invalid service name.")
        if domain in FORBIDDEN_DOMAINS or domain not in allowed:
            raise ToolError(f"The owner has not allowed controlling '{domain}' devices. They can "
                            "allow it in Nestor's settings (Settings > Devices & services > "
                            "Nestor > Configure).")
        if not entity_ids:
            raise ToolError("entity_ids must not be empty.")
        for eid in entity_ids:
            if eid.split(".", 1)[0] not in allowed:
                raise ToolError(f"The owner has not allowed controlling {eid}.")
            if self.hass.states.get(eid) is None:
                raise ToolError(f"No entity {eid}.")
        payload = dict(data or {})
        payload.pop("entity_id", None)
        payload["entity_id"] = entity_ids
        try:
            await self.hass.services.async_call(domain, service, payload, blocking=True,
                                                context=context)
        except ServiceNotFound as err:
            raise ToolError(f"Service {domain}.{service} does not exist.") from err
        except (HomeAssistantError, ValueError) as err:
            raise ToolError(f"{domain}.{service} failed: {err}") from err
        changed = [{"entity_id": e, "state": s.state}
                   for e in entity_ids if (s := self.hass.states.get(e))]
        return json.dumps({"ok": True, "now": changed}, ensure_ascii=False)

    # ---- structure tools (permission "structure") ---------------------

    async def list_structure(self) -> str:
        floors = [{"floor_id": f.floor_id, "name": f.name, "level": f.level}
                  for f in fr.async_get(self.hass).async_list_floors()]
        ent_reg, dev_reg = er.async_get(self.hass), dr.async_get(self.hass)
        areas = []
        for a in ar.async_get(self.hass).async_list_areas():
            n_ent = len(er.async_entries_for_area(ent_reg, a.id))
            n_dev = len(dr.async_entries_for_area(dev_reg, a.id))
            areas.append({"area_id": a.id, "name": a.name, "floor_id": a.floor_id,
                          "devices": n_dev, "entities": n_ent})
        return json.dumps({"floors": floors, "areas": areas}, ensure_ascii=False)

    async def create_floor(self, name: str, level: int | None = None) -> str:
        try:
            floor = fr.async_get(self.hass).async_create(name, level=level)
        except ValueError as err:
            raise ToolError(str(err)) from err
        return json.dumps({"ok": True, "floor_id": floor.floor_id, "name": floor.name})

    async def create_area(self, name: str, floor: str | None = None) -> str:
        floor_id = self._find_floor(floor).floor_id if floor else None
        try:
            area = ar.async_get(self.hass).async_create(name, floor_id=floor_id)
        except ValueError as err:
            raise ToolError(str(err)) from err
        return json.dumps({"ok": True, "area_id": area.id, "name": area.name})

    async def update_area(self, area: str, new_name: str | None = None,
                          floor: str | None = None) -> str:
        entry = self._find_area(area)
        kwargs: dict[str, Any] = {}
        if new_name:
            kwargs["name"] = new_name
        if floor is not None:
            kwargs["floor_id"] = self._find_floor(floor).floor_id if floor else None
        if not kwargs:
            raise ToolError("Nothing to change.")
        try:
            updated = ar.async_get(self.hass).async_update(entry.id, **kwargs)
        except ValueError as err:
            raise ToolError(str(err)) from err
        return json.dumps({"ok": True, "area_id": updated.id, "name": updated.name,
                           "floor_id": updated.floor_id})

    async def assign_area(self, entity_ids: list[str], area: str) -> str:
        """Move entities (and, when the whole device moves, their device) to an area."""
        area_id = self._find_area(area).id
        ent_reg = er.async_get(self.hass)
        moved = []
        for eid in entity_ids:
            if ent_reg.async_get(eid) is None:
                raise ToolError(f"{eid} can't be assigned to an area (it has no unique ID).")
            ent_reg.async_update_entity(eid, area_id=area_id)
            moved.append(eid)
        return json.dumps({"ok": True, "moved": moved, "area_id": area_id})

    async def rename_entity(self, entity_id: str, new_name: str) -> str:
        ent_reg = er.async_get(self.hass)
        if ent_reg.async_get(entity_id) is None:
            raise ToolError(f"{entity_id} can't be renamed (it has no unique ID).")
        ent_reg.async_update_entity(entity_id, name=new_name)
        return json.dumps({"ok": True, "entity_id": entity_id, "name": new_name},
                          ensure_ascii=False)

    def describe_delete(self, kind: str, name: str) -> str:
        if kind == "area":
            a = self._find_area(name)
            n = len(er.async_entries_for_area(er.async_get(self.hass), a.id))
            return f"delete the area '{a.name}' ({n} entities will be left without an area)"
        f = self._find_floor(name)
        return f"delete the floor '{f.name}' (its areas stay, without a floor)"

    async def delete_structure(self, kind: str, name: str) -> str:
        if kind == "area":
            a = self._find_area(name)
            ar.async_get(self.hass).async_delete(a.id)
            return json.dumps({"ok": True, "deleted_area": a.name}, ensure_ascii=False)
        f = self._find_floor(name)
        fr.async_get(self.hass).async_delete(f.floor_id)
        return json.dumps({"ok": True, "deleted_floor": f.name}, ensure_ascii=False)
