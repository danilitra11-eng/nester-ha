"""Nestor AI Butler: a paid AI assistant for Home Assistant."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .agent import Agent
from .cloud import CloudClient
from .const import (CONF_CLOUD_URL, CONF_INSTANCE_ID, CONF_LICENSE_KEY, DEFAULT_CLOUD_URL,
                    DEFAULT_OPTIONS, DOMAIN, OPT_NAME, OPT_PERMISSIONS, OPT_TTS_ENGINE,
                    OPT_TTS_VOICE, OPT_VOICE_ASSISTANT, PANEL_URL, STATIC_URL, VERSION)
from .telegram import TelegramRelay
from .tools_design import DesignTools
from .tools_home import HomeTools

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.CONVERSATION]

type NestorConfigEntry = ConfigEntry[NestorRuntime]


class NestorRuntime:
    """Everything Nestor needs while running, stored on entry.runtime_data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self.entry = entry
        self.cloud = CloudClient(async_get_clientsession(hass),
                                 entry.data.get(CONF_CLOUD_URL, DEFAULT_CLOUD_URL),
                                 entry.data[CONF_LICENSE_KEY], entry.data[CONF_INSTANCE_ID])
        self.home = HomeTools(hass)
        self.design = DesignTools(hass, entry.entry_id)
        self.agent = Agent(hass, self.cloud, lambda: self.options, self.async_update_options,
                           self.home, self.design)
        self.telegram = TelegramRelay(self)
        self.apply_options()

    @property
    def options(self) -> dict[str, Any]:
        return {**DEFAULT_OPTIONS, **self.entry.options}

    def apply_options(self) -> None:
        self.home.set_permissions(self.options[OPT_PERMISSIONS])

    async def async_update_options(self, changes: dict[str, Any]) -> None:
        self.hass.config_entries.async_update_entry(
            self.entry, options={**self.entry.options, **changes})


async def async_setup_entry(hass: HomeAssistant, entry: NestorConfigEntry) -> bool:
    runtime = NestorRuntime(hass, entry)
    await runtime.design.async_load()
    entry.runtime_data = runtime

    await _async_register_panel(hass)
    from .websocket import async_register_commands
    async_register_commands(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    runtime.telegram.start()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: NestorConfigEntry) -> bool:
    entry.runtime_data.telegram.stop()
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_options_updated(hass: HomeAssistant, entry: NestorConfigEntry) -> None:
    """Apply changes without a reload, so conversations and Telegram keep running."""
    runtime = entry.runtime_data
    runtime.apply_options()
    opts = runtime.options
    if opts.get(OPT_VOICE_ASSISTANT):
        from homeassistant.helpers import entity_registry as er
        from .voice import ensure_pipeline
        ent_id = er.async_get(hass).async_get_entity_id("conversation", DOMAIN,
                                                        f"{entry.entry_id}_conversation")
        if ent_id:
            await ensure_pipeline(hass, ent_id, opts.get(OPT_NAME, "Nestor"),
                                  opts.get(OPT_TTS_ENGINE), opts.get(OPT_TTS_VOICE))


async def _async_register_panel(hass: HomeAssistant) -> None:
    if hass.data.get(f"{DOMAIN}_panel"):
        return
    from homeassistant.components import panel_custom

    frontend_dir = Path(__file__).parent / "frontend"
    await hass.http.async_register_static_paths(
        [StaticPathConfig(STATIC_URL, str(frontend_dir), cache_headers=False)])
    await panel_custom.async_register_panel(
        hass, frontend_url_path=PANEL_URL, webcomponent_name="nestor-panel",
        sidebar_title="Nestor", sidebar_icon="mdi:account-tie",
        module_url=f"{STATIC_URL}/nestor-panel.js?v={VERSION}", require_admin=False)
    hass.data[f"{DOMAIN}_panel"] = True
