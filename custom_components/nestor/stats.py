"""Counters for the monthly report ("this month Nestor did X, saved about $Y")."""

from __future__ import annotations

import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

KEYS = ("commands", "actions", "alerts", "fixes", "automations", "suggestions_accepted")


def _month() -> str:
    return dt_util.now().strftime("%Y-%m")


class Stats:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"nestor.stats.{entry_id}")
        self.data: dict[str, Any] = {}

    async def async_load(self) -> None:
        self.data = await self._store.async_load() or {}
        self.data.setdefault("installed", time.time())
        self.data.setdefault("months", {})
        self.data.setdefault("sent", {})  # which one-off reports went out
        self._save()

    def _save(self) -> None:
        self._store.async_delay_save(lambda: self.data, 2)

    def _cur(self, month: str | None = None) -> dict[str, float]:
        m = self.data["months"].setdefault(month or _month(), {})
        for k in (*KEYS, "kwh_saved"):
            m.setdefault(k, 0)
        return m

    def inc(self, key: str, n: int = 1) -> None:
        self._cur()[key] += n
        self._save()

    def add_saving(self, kwh: float) -> None:
        self._cur()["kwh_saved"] += max(kwh, 0)
        self._save()

    def summary(self, month: str | None = None, price: float = 0.17) -> dict[str, Any]:
        m = dict(self._cur(month))
        m["money_saved"] = f"{m['kwh_saved'] * price:.2f}"
        m["kwh_saved"] = f"{m['kwh_saved']:.1f}"
        m["month"] = month or _month()
        return m

    def days_installed(self) -> float:
        return (time.time() - self.data["installed"]) / 86400

    def mark_sent(self, key: str) -> bool:
        """True the first time a one-off report key is used."""
        if key in self.data["sent"]:
            return False
        self.data["sent"][key] = time.time()
        self._save()
        return True
