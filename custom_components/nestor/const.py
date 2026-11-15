"""Constants for the Nestor integration."""

from __future__ import annotations

DOMAIN = "nestor"
VERSION = "0.3.0"

DEFAULT_CLOUD_URL = "https://api.your-domain.com"
HELP_URL = "https://github.com/danilitra11-eng/nester-ha/tree/main/docs/guides"
TRIAL_URL = "https://your-domain.com/#pricing"

# config entry data (fixed after setup)
CONF_LICENSE_KEY = "license_key"
CONF_CLOUD_URL = "cloud_url"
CONF_INSTANCE_ID = "instance_id"

# options (changeable)
OPT_NAME = "assistant_name"
OPT_LANGUAGE = "language"
OPT_PERSONALITY = "personality"
OPT_PERMISSIONS = "permissions"
OPT_TTS_ENGINE = "tts_engine"
OPT_TTS_VOICE = "tts_voice"
OPT_SPEAK = "speak_replies"
OPT_QUIET = "quiet_hours"
OPT_VOICE_ASSISTANT = "make_voice_assistant"
OPT_NOTIFY_TARGETS = "notify_targets"   # None = every phone with the HA app
OPT_ALERTS = "alerts"                   # enabled proactive rules
OPT_PROFILES = "profiles"               # {name: {"blocked": [permission groups]}}
OPT_VACATION = "vacation_mode"
OPT_ENERGY_PRICE = "energy_price"       # per kWh, for the savings estimate

PERSONALITIES = ["butler", "friendly", "brief"]
LANGUAGES = ["auto", "en", "es", "fr", "de", "it", "pt", "ru", "he", "zh", "ja"]

# Permission groups shown in the setup wizard -> the HA domains they unlock.
PERMISSION_GROUPS: dict[str, list[str]] = {
    "lights": ["light"],
    "switches": ["switch", "input_boolean"],
    "climate": ["climate", "fan", "humidifier", "water_heater"],
    "covers": ["cover"],
    "media": ["media_player"],
    "vacuum": ["vacuum", "lawn_mower"],
    "scenes": ["scene", "script"],
    "security": ["lock", "alarm_control_panel"],
}
# Special permissions that unlock tool families rather than device domains.
PERMISSION_STRUCTURE = "structure"
PERMISSION_DESIGN = "design"
PERMISSION_AUTOMATIONS = "automations"
PERMISSION_CAMERAS = "cameras"
ALL_PERMISSIONS = [*PERMISSION_GROUPS, PERMISSION_STRUCTURE, PERMISSION_DESIGN,
                   PERMISSION_AUTOMATIONS, PERMISSION_CAMERAS]
DEFAULT_PERMISSIONS = ["lights", "switches", "climate", "covers", "media", "vacuum", "scenes"]

# Domains that can never be called from chat, whatever the permissions.
FORBIDDEN_DOMAINS = {"homeassistant", "hassio", "shell_command", "python_script", "rest_command",
                     "recorder", "system_log", "logger", "backup", "pyscript", "update"}

# What the assistant itself may change through chat.
CHAT_EDITABLE = {OPT_NAME, OPT_LANGUAGE, OPT_PERSONALITY, OPT_SPEAK, OPT_QUIET}

DEFAULT_OPTIONS = {
    OPT_NAME: "Nestor",
    OPT_LANGUAGE: "auto",
    OPT_PERSONALITY: "butler",
    OPT_PERMISSIONS: DEFAULT_PERMISSIONS,
    OPT_TTS_ENGINE: None,
    OPT_TTS_VOICE: None,
    OPT_SPEAK: False,
    OPT_QUIET: None,
    OPT_VOICE_ASSISTANT: True,
    OPT_NOTIFY_TARGETS: None,
    OPT_ALERTS: ["safety", "left_open", "lights_left_on", "window_climate", "doctor",
                 "suggestions", "reports", "doorbell"],
    OPT_PROFILES: {},
    OPT_VACATION: False,
    OPT_ENERGY_PRICE: 0.17,
}

ALERT_RULES = ["safety", "left_open", "lights_left_on", "window_climate", "doctor",
               "suggestions", "reports", "doorbell"]

PANEL_URL = "nestor"
STATIC_URL = "/nestor_static"
