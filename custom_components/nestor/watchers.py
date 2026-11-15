"""The proactive butler. Simple local rules (no AI, no cost) that notice things and
tell the household, with a button to fix them: safety sensors, doors left open,
lights left on, windows open with the AC running, a daily health check-up,
weekly automation suggestions, reports, vacation mode and the doorbell."""

from __future__ import annotations

import logging
import random
import statistics
import time
from collections import defaultdict
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.util import dt as dt_util

from .const import (OPT_ALERTS, OPT_ENERGY_PRICE, OPT_LANGUAGE, OPT_NAME, OPT_VACATION,
                    PERMISSION_GROUPS)
from .notices import notice

if TYPE_CHECKING:
    from . import NestorRuntime

_LOGGER = logging.getLogger(__name__)

SAFETY = {"moisture": "leak", "smoke": "smoke", "gas": "gas", "carbon_monoxide": "co"}
OPEN_COVERS = {"garage", "door", "gate"}
OPEN_MINUTES = 30
WINDOW_MINUTES = 10
COOLDOWN = 3 * 3600
LIGHT_KWH_PER_HOUR = 0.009     # ~9 W LED
CLIMATE_KWH_PER_HOUR = 1.2
NIGHT = (23, 6)


def _is_night(now: datetime) -> bool:
    return now.hour >= NIGHT[0] or now.hour < NIGHT[1]


class Watchers:
    def __init__(self, runtime: "NestorRuntime") -> None:
        self.rt = runtime
        self.hass: HomeAssistant = runtime.hass
        self._last: dict[tuple[str, str], float] = {}
        self._snoozed: dict[tuple[str, str | None], float] = {}
        self._was_home: bool | None = None
        self.health: dict[str, Any] = {}
        self._last_daily = self._last_weekly = self._last_vacation = ""

    @property
    def lang(self) -> str:
        lang = self.rt.options.get(OPT_LANGUAGE, "auto")
        return (lang if lang != "auto" else self.hass.config.language or "en")[:2]

    def enabled(self, rule: str) -> bool:
        feats = self.rt.features
        if rule in ("safety", "lights_left_on", "reports"):
            needed = "alerts_basic"
        elif rule == "doorbell":
            needed = "vision"
        elif rule == "doctor":
            needed = "doctor"
        elif rule == "suggestions":
            needed = "suggestions"
        else:
            needed = "alerts"
        return needed in feats and rule in self.rt.options.get(OPT_ALERTS, [])

    @callback
    def async_start(self) -> None:
        entry = self.rt.entry
        entry.async_on_unload(async_track_time_interval(self.hass, self._tick,
                                                        timedelta(minutes=1)))
        entry.async_on_unload(self.hass.bus.async_listen("state_changed", self._on_state))

    # ---- helpers --------------------------------------------------------

    def snooze(self, rule: str, entity_id: str | None, hours: float) -> None:
        self._snoozed[(rule, entity_id)] = time.time() + hours * 3600

    def _cooldown_ok(self, rule: str, entity_id: str, seconds: float = COOLDOWN) -> bool:
        if self._snoozed.get((rule, entity_id), 0) > time.time() or \
                self._snoozed.get((rule, None), 0) > time.time():
            return False
        last = self._last.get((rule, entity_id), 0)
        if time.time() - last < seconds:
            return False
        self._last[(rule, entity_id)] = time.time()
        return True

    def anyone_home(self) -> bool | None:
        people = self.hass.states.async_all("person")
        if not people:
            return None
        return any(p.state == "home" for p in people)

    def _area_id(self, entity_id: str) -> str | None:
        ent = er.async_get(self.hass).async_get(entity_id)
        if not ent:
            return None
        if ent.area_id:
            return ent.area_id
        dev = dr.async_get(self.hass).async_get(ent.device_id) if ent.device_id else None
        return dev.area_id if dev else None

    def _allowed(self, domain: str) -> bool:
        return domain in self.rt.home.allowed

    async def _alert(self, rule: str, text: str, buttons=None, urgent=False, key=None) -> None:
        self.rt.stats.inc("alerts")
        await self.rt.notifier.send(text, buttons=buttons, urgent=urgent, key=key or rule)

    # ---- instant: safety sensors and doorbell ---------------------------

    @callback
    def _on_state(self, event: Event[EventStateChangedData]) -> None:
        new, old = event.data.get("new_state"), event.data.get("old_state")
        if new is None:
            return
        eid = new.entity_id
        dc = new.attributes.get("device_class")
        if eid.startswith("binary_sensor.") and dc in SAFETY and new.state == "on" \
                and (old is None or old.state != "on") and self.enabled("safety"):
            if self._cooldown_ok("safety", eid, 600):
                self.hass.async_create_task(self._alert(
                    "safety", notice(SAFETY[dc], self.lang, name=new.name), urgent=True,
                    key=f"safety_{eid}"))
        is_doorbell = (eid.startswith("event.") and dc == "doorbell") or \
            (eid.startswith("binary_sensor.") and "doorbell" in eid and new.state == "on")
        if is_doorbell and old is not None and new.state != old.state and self.enabled("doorbell"):
            if self._cooldown_ok("doorbell", eid, 60):
                self.hass.async_create_task(self._doorbell(eid))

    async def _doorbell(self, doorbell_id: str) -> None:
        camera = self._camera_near(doorbell_id)
        description = None
        if camera:
            description = await self.rt.cameras.describe(
                camera, "Someone just rang the doorbell. In one short sentence, who or what is "
                        "at the door? Mention packages or delivery uniforms if visible.")
        text = notice("doorbell", self.lang, description=description) if description \
            else notice("doorbell_plain", self.lang)
        await self._alert("doorbell", text, key="doorbell")

    def _camera_near(self, entity_id: str) -> str | None:
        area = self._area_id(entity_id)
        cams = [s.entity_id for s in self.hass.states.async_all("camera")]
        same = [c for c in cams if area and self._area_id(c) == area]
        named = [c for c in cams if any(w in c for w in ("door", "front", "entry", "porch"))]
        return (same or named or [None])[0]

    # ---- every minute ---------------------------------------------------

    async def _tick(self, _now: datetime | None = None) -> None:
        try:
            now = dt_util.now()
            await self.rt.notifier.flush_held() if not self._quiet(now) else None
            home = self.anyone_home()
            if self.enabled("left_open"):
                await self._check_left_open(now, home)
            if self.enabled("lights_left_on"):
                await self._check_everyone_left(home)
            if self.enabled("window_climate"):
                await self._check_window_climate()
            if self.rt.options.get(OPT_VACATION) and "vacation" in self.rt.features:
                await self._vacation_step(now)
            day = now.strftime("%Y-%m-%d")
            if now.hour >= 9 and self._last_daily != day:
                self._last_daily = day
                if self.enabled("doctor"):
                    await self.health_check(notify=True)
                if self.enabled("reports"):
                    await self._reports(now)
            week = now.strftime("%G-W%V")
            if now.weekday() == 6 and now.hour >= 18 and self._last_weekly != week:
                self._last_weekly = week
                if self.enabled("suggestions"):
                    await self.suggest_automations()
        except Exception:  # a broken rule must never stop the others
            _LOGGER.exception("Nestor watcher tick failed")

    def _quiet(self, now: datetime) -> bool:
        from .agent import in_quiet_hours
        return in_quiet_hours(self.rt.options.get("quiet_hours"), now.time())

    async def _check_left_open(self, now: datetime, home: bool | None) -> None:
        away, night = home is False, _is_night(now)
        if not away and not night:
            return
        for st in self.hass.states.async_all("cover"):
            if st.state != "open" or st.attributes.get("device_class") not in OPEN_COVERS:
                continue
            minutes = int((dt_util.utcnow() - st.last_changed).total_seconds() // 60)
            if minutes < OPEN_MINUTES or not self._cooldown_ok("left_open", st.entity_id):
                continue
            key = "left_open_away" if away else "left_open_night"
            buttons = [(notice("close", self.lang), {"type": "service", "domain": "cover",
                        "service": "close_cover", "entity_ids": [st.entity_id]})] \
                if self._allowed("cover") else []
            buttons.append((notice("snooze", self.lang), {"type": "snooze", "rule": "left_open",
                            "entity_id": st.entity_id, "hours": 8}))
            await self._alert("left_open", notice(key, self.lang, name=st.name, minutes=minutes),
                              buttons, key=f"open_{st.entity_id}")
        if away:
            for st in self.hass.states.async_all("lock"):
                if st.state == "unlocked" and self._cooldown_ok("unlocked", st.entity_id):
                    buttons = [(notice("lock", self.lang), {"type": "service", "domain": "lock",
                                "service": "lock", "entity_ids": [st.entity_id]})] \
                        if self._allowed("lock") else []
                    await self._alert("left_open", notice("unlocked_away", self.lang,
                                                          name=st.name), buttons)

    async def _check_everyone_left(self, home: bool | None) -> None:
        was, self._was_home = self._was_home, home
        if not (was is True and home is False):
            return
        lights = [s for s in self.hass.states.async_all("light") if s.state == "on"]
        if not lights or not self._cooldown_ok("lights_left_on", "all", 1800):
            return
        names = ", ".join(s.name for s in lights[:6]) + ("…" if len(lights) > 6 else "")
        buttons = [(notice("turn_off_all", self.lang), {
            "type": "service", "domain": "light", "service": "turn_off",
            "entity_ids": [s.entity_id for s in lights],
            "saving_kwh": round(len(lights) * LIGHT_KWH_PER_HOUR * 3, 3)})] \
            if self._allowed("light") else []
        await self._alert("lights_left_on", notice("lights_left_on", self.lang,
                                                   count=len(lights), names=names), buttons)

    async def _check_window_climate(self) -> None:
        running = [s for s in self.hass.states.async_all("climate")
                   if s.state not in ("off", "unavailable", "unknown")
                   and s.attributes.get("hvac_action") not in ("off", "idle")]
        if not running:
            return
        openings = [s for s in self.hass.states.async_all("binary_sensor")
                    if s.attributes.get("device_class") in ("window", "door") and s.state == "on"
                    and (dt_util.utcnow() - s.last_changed).total_seconds() > WINDOW_MINUTES * 60]
        for climate in running:
            area = self._area_id(climate.entity_id)
            for window in openings:
                same_area = area and self._area_id(window.entity_id) == area
                if same_area and self._cooldown_ok("window_climate", climate.entity_id):
                    buttons = [(notice("turn_off_climate", self.lang), {
                        "type": "service", "domain": "climate", "service": "turn_off",
                        "entity_ids": [climate.entity_id],
                        "saving_kwh": CLIMATE_KWH_PER_HOUR})] if self._allowed("climate") else []
                    await self._alert("window_climate", notice(
                        "window_climate", self.lang, window=window.name, climate=climate.name),
                        buttons)
                    break

    # ---- home doctor ----------------------------------------------------

    async def health_check(self, notify: bool = False) -> dict[str, Any]:
        cutoff = dt_util.utcnow() - timedelta(hours=1)
        ent_reg = er.async_get(self.hass)
        unavailable = [s for s in self.hass.states.async_all()
                       if s.state == "unavailable" and s.last_changed < cutoff
                       and (e := ent_reg.async_get(s.entity_id)) is not None
                       and not e.disabled_by and not e.hidden_by]
        low = []
        for s in self.hass.states.async_all("sensor"):
            if s.attributes.get("device_class") == "battery":
                try:
                    if float(s.state) < 15:
                        low.append(s)
                except ValueError:
                    pass
        broken = [e for e in self.hass.config_entries.async_entries()
                  if e.state in (ConfigEntryState.SETUP_ERROR, ConfigEntryState.SETUP_RETRY)
                  and e.domain != "nestor"]
        updates = [s for s in self.hass.states.async_all("update") if s.state == "on"]
        self.health = {
            "checked": dt_util.now().isoformat(),
            "unavailable": [{"entity_id": s.entity_id, "name": s.name} for s in unavailable],
            "low_battery": [{"entity_id": s.entity_id, "name": s.name, "level": s.state}
                            for s in low],
            "broken_integrations": [{"entry_id": e.entry_id, "title": e.title,
                                     "domain": e.domain} for e in broken],
            "updates_available": len(updates),
        }
        if notify and (unavailable or low or broken):
            lines = [notice("health_title", self.lang)]
            if unavailable:
                lines.append("• " + notice("health_unavailable", self.lang, count=len(unavailable),
                                           names=", ".join(s.name for s in unavailable[:5])))
            if low:
                lines.append("• " + notice("health_battery", self.lang,
                                           names=", ".join(f"{s.name} ({s.state}%)" for s in low[:5])))
            if broken:
                lines.append("• " + notice("health_broken", self.lang,
                                           names=", ".join(e.title for e in broken)))
            if updates:
                lines.append("• " + notice("health_updates", self.lang, count=len(updates)))
            buttons = [(notice("restart", self.lang, name=e.title[:20]),
                        {"type": "reload_entry", "entry_id": e.entry_id}) for e in broken[:2]]
            fingerprint = str(sorted(s.entity_id for s in unavailable + low) +
                              sorted(e.entry_id for e in broken))
            if self.health.get("_sent") != fingerprint and self._cooldown_ok("doctor", fingerprint,
                                                                             20 * 3600):
                self.rt.stats.inc("fixes", len(broken) + len(low) + min(len(unavailable), 5))
                await self._alert("doctor", "\n".join(lines), buttons, key="doctor")
            self.health["_sent"] = fingerprint
        return self.health

    # ---- reports --------------------------------------------------------

    async def _reports(self, now: datetime) -> None:
        name = self.rt.options.get(OPT_NAME, "Nestor")
        price = float(self.rt.options.get(OPT_ENERGY_PRICE, 0.17))
        currency = {"USD": "$", "EUR": "€", "GBP": "£", "ILS": "₪", "CAD": "$",
                    "AUD": "$"}.get(self.hass.config.currency or "USD", "")
        if self.rt.stats.days_installed() >= 5 and self.rt.stats.mark_sent("trial_day5"):
            s = self.rt.stats.summary(price=price)
            await self.rt.notifier.send(notice("report", self.lang, title=notice(
                "report_trial", self.lang, name=name), commands=s["commands"],
                actions=s["actions"], alerts=s["alerts"], fixes=s["fixes"],
                automations=s["automations"], kwh=s["kwh_saved"], currency=currency,
                money=s["money_saved"]), key="report")
        if now.day == 1:
            last = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")
            if self.rt.stats.mark_sent(f"month_{last}"):
                s = self.rt.stats.summary(last, price)
                await self.rt.notifier.send(notice("report", self.lang, title=notice(
                    "report_month", self.lang, name=name), commands=s["commands"],
                    actions=s["actions"], alerts=s["alerts"], fixes=s["fixes"],
                    automations=s["automations"], kwh=s["kwh_saved"], currency=currency,
                    money=s["money_saved"]), key="report")

    # ---- automation suggestions -----------------------------------------

    async def suggest_automations(self, days: int = 14, min_days: int = 5) -> list[dict[str, Any]]:
        """Find things people do by hand at about the same time on most days."""
        from homeassistant.components.recorder import get_instance, history

        domains = [d for d in ("light", "switch", "cover") if self._allowed(d)]
        entity_ids = [s.entity_id for d in domains for s in self.hass.states.async_all(d)]
        if not entity_ids:
            return []
        start = dt_util.utcnow() - timedelta(days=days)
        try:
            states = await get_instance(self.hass).async_add_executor_job(
                lambda: history.get_significant_states(self.hass, start, None, entity_ids,
                                                       include_start_time_state=False,
                                                       no_attributes=True))
        except Exception as err:
            _LOGGER.debug("No history for suggestions: %s", err)
            return []
        taken = set(self.rt.automations.existing_patterns())
        suggestions = []
        for eid, history_states in states.items():
            if eid in taken:
                continue
            by_target: dict[str, dict[str, list[int]]] = defaultdict(lambda: defaultdict(list))
            for st in history_states:
                if not hasattr(st, "state") or st.state not in ("on", "off", "open", "closed"):
                    continue
                local = dt_util.as_local(st.last_changed)
                by_target[st.state][local.strftime("%Y-%m-%d")].append(local.hour * 60 +
                                                                       local.minute)
            for target, per_day in by_target.items():
                firsts = sorted(min(v) for v in per_day.values())
                if len(firsts) < min_days:
                    continue
                center = int(statistics.median(firsts))
                close = [m for m in firsts if abs(m - center) <= 20]
                if len(close) >= min_days:
                    suggestions.append({"entity_id": eid, "state": target,
                                        "time": f"{center // 60:02d}:{center % 60:02d}",
                                        "days": len(close)})
        suggestions.sort(key=lambda s: -s["days"])
        for sug in suggestions[:2]:
            await self._send_suggestion(sug)
        return suggestions

    async def _send_suggestion(self, sug: dict[str, Any]) -> None:
        st = self.hass.states.get(sug["entity_id"])
        name = st.name if st else sug["entity_id"]
        domain = sug["entity_id"].split(".")[0]
        service = {"on": "turn_on", "off": "turn_off", "open": "open_cover",
                   "closed": "close_cover"}[sug["state"]]
        automation = {
            "alias": f"{name} {sug['state']} at {sug['time']}",
            "description": f"Suggested by Nestor: {name} was {sug['state']} around {sug['time']} "
                           f"on {sug['days']} of the last 14 days.",
            "triggers": [{"trigger": "time", "at": f"{sug['time']}:00"}],
            "actions": [{"action": f"{domain}.{service}", "target": {"entity_id": sug["entity_id"]}}],
        }
        buttons = [(notice("yes_automate", self.lang), {"type": "automation",
                                                        "automation": automation}),
                   (notice("snooze", self.lang), {"type": "snooze", "rule": "suggestions",
                                                  "entity_id": sug["entity_id"], "hours": 24 * 30})]
        if self._cooldown_ok("suggestion", sug["entity_id"], 7 * 86400):
            await self.rt.notifier.send(notice("suggest", self.lang, name=name,
                                               verb=notice(f"verb_{sug['state']}", self.lang),
                                               time=sug["time"]), buttons=buttons,
                                        key=f"suggest_{sug['entity_id']}")

    # ---- vacation mode ----------------------------------------------------

    async def _vacation_step(self, now: datetime) -> None:
        """Lights that come and go in the evening, so the house looks lived-in."""
        if not self._allowed("light"):
            return
        sun = self.hass.states.get("sun.sun")
        dark = (sun.state == "below_horizon") if sun else now.hour >= 18
        lights = [s for s in self.hass.states.async_all("light")
                  if not any(w in s.entity_id for w in ("bed", "kids", "nursery"))]
        if not lights:
            return
        if now.hour >= 23 or now.hour < 6 or not dark:
            on = [s.entity_id for s in lights if s.state == "on"]
            if on and self._last_vacation != "off":
                self._last_vacation = "off"
                await self.hass.services.async_call("light", "turn_off", {"entity_id": on})
            return
        if random.random() < 1 / 20:  # about every 20 minutes
            pick = random.choice(lights)
            service = "turn_off" if pick.state == "on" else "turn_on"
            self._last_vacation = "on"
            await self.hass.services.async_call("light", service, {"entity_id": pick.entity_id})
