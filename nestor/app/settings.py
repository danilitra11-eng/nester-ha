"""User settings: the add-on Configuration tab gives defaults, the in-panel wizard
and chat requests override them. Overrides live in /data/settings.json.

Permissions (allowed_domains, allow_security_devices) can be changed from the
settings screen only, never from chat, so a guest can't talk the assistant
into unlocking the front door.
"""

from __future__ import annotations

import json
import re
from datetime import time as dtime
from pathlib import Path
from typing import Any, Callable

from .i18n import SUPPORTED

PERSONALITIES = ("butler", "friendly", "brief")
LANGUAGES = ("auto",) + SUPPORTED
HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")

DEFAULTS: dict[str, Any] = {
    "license_key": "",
    "assistant_name": "Nestor",
    "language": "auto",
    "personality": "butler",
    "allowed_domains": ["light", "switch", "fan", "climate", "cover", "media_player", "scene",
                        "script", "vacuum", "humidifier", "water_heater", "input_boolean"],
    "allow_security_devices": False,
    "speak_replies": False,
    "quiet_hours": None,          # {"start": "22:00", "end": "07:00"} or None
    "onboarded": False,
}

# What chat may change (via the update_settings tool).
CHAT_EDITABLE = {"assistant_name", "language", "personality", "speak_replies", "quiet_hours"}
# What the settings screen / wizard may change.
PANEL_EDITABLE = CHAT_EDITABLE | {"license_key", "allowed_domains", "allow_security_devices",
                                  "onboarded"}


class SettingsError(ValueError):
    pass


def _validate(key: str, value: Any) -> Any:
    if key == "license_key":
        return str(value).strip()[:200]
    if key == "assistant_name":
        name = " ".join(str(value).split())[:40]
        if not name:
            raise SettingsError("The name can't be empty.")
        return name
    if key == "language":
        if value not in LANGUAGES:
            raise SettingsError(f"Language must be one of: {', '.join(LANGUAGES)}.")
        return value
    if key == "personality":
        if value not in PERSONALITIES:
            raise SettingsError(f"Personality must be one of: {', '.join(PERSONALITIES)}.")
        return value
    if key == "allowed_domains":
        if not isinstance(value, list):
            raise SettingsError("allowed_domains must be a list.")
        return sorted({str(d).strip().lower() for d in value if str(d).strip()})
    if key in ("allow_security_devices", "speak_replies", "onboarded"):
        if not isinstance(value, bool):
            raise SettingsError(f"{key} must be true or false.")
        return value
    if key == "quiet_hours":
        if value is None:
            return None
        if (not isinstance(value, dict) or not HHMM.match(str(value.get("start", "")))
                or not HHMM.match(str(value.get("end", "")))):
            raise SettingsError('quiet_hours must look like {"start": "22:00", "end": "07:00"} or null.')
        return {"start": value["start"], "end": value["end"]}
    raise SettingsError(f"Unknown setting {key}.")


class Settings:
    def __init__(self, options: dict[str, Any], path: Path) -> None:
        self._path = path
        self._base = {**DEFAULTS, **{k: v for k, v in options.items() if k in DEFAULTS}}
        # An existing key from the Configuration tab means setup was done the old way.
        if self._base.get("license_key"):
            self._base["onboarded"] = True
        try:
            self._overrides: dict[str, Any] = json.loads(path.read_text())
        except (OSError, ValueError):
            self._overrides = {}
        self._listeners: list[Callable[["Settings"], None]] = []

    def __getitem__(self, key: str) -> Any:
        return self._overrides.get(key, self._base[key])

    def as_dict(self) -> dict[str, Any]:
        return {k: self[k] for k in DEFAULTS}

    def public(self) -> dict[str, Any]:
        """Everything except the key itself, for the panel."""
        data = self.as_dict()
        data["has_license_key"] = bool(data.pop("license_key"))
        return data

    def on_change(self, fn: Callable[["Settings"], None]) -> None:
        self._listeners.append(fn)

    def update(self, changes: dict[str, Any], *, allowed: set[str]) -> dict[str, Any]:
        cleaned: dict[str, Any] = {}
        for key, value in changes.items():
            if key not in allowed:
                raise SettingsError(f"'{key}' can only be changed from the Nestor settings screen.")
            cleaned[key] = _validate(key, value)
        self._overrides.update(cleaned)
        try:
            self._path.write_text(json.dumps(self._overrides, indent=2))
        except OSError:
            pass
        for fn in self._listeners:
            fn(self)
        return cleaned

    def in_quiet_hours(self, now: dtime) -> bool:
        q = self["quiet_hours"]
        if not q:
            return False
        start = dtime.fromisoformat(q["start"])
        end = dtime.fromisoformat(q["end"])
        if start <= end:
            return start <= now < end
        return now >= start or now < end  # spans midnight
