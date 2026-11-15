"""Setup wizard (config flow) and settings screen (options flow)."""

from __future__ import annotations

import uuid
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (BooleanSelector, SelectOptionDict, SelectSelector,
                                            SelectSelectorConfig, SelectSelectorMode,
                                            TextSelector, TextSelectorConfig, TextSelectorType)

from .cloud import CloudClient, CloudError
from .const import (ALL_PERMISSIONS, CONF_CLOUD_URL, CONF_INSTANCE_ID, CONF_LICENSE_KEY,
                    DEFAULT_CLOUD_URL, DEFAULT_OPTIONS, DOMAIN, HELP_URL, LANGUAGES, OPT_LANGUAGE,
                    OPT_NAME, OPT_PERMISSIONS, OPT_PERSONALITY, OPT_SPEAK, OPT_TTS_ENGINE,
                    OPT_TTS_VOICE, OPT_VOICE_ASSISTANT, PERSONALITIES, TRIAL_URL)
from .voice import list_voices

NAME_SUGGESTIONS = ["Nestor", "Jarvis", "Alfred", "Max", "Ava"]
DEFAULT_VOICE = "__default__"


def _voice_options(hass) -> list[SelectOptionDict]:
    opts = [SelectOptionDict(value=DEFAULT_VOICE, label="Home Assistant's default voice")]
    for engine in list_voices(hass):
        if engine["voices"]:
            for v in engine["voices"]:
                opts.append(SelectOptionDict(value=f"{engine['engine_id']}|{v['voice_id']}",
                                             label=f"{v['name']} ({engine['name']})"))
        else:
            opts.append(SelectOptionDict(value=f"{engine['engine_id']}|",
                                         label=engine["name"]))
    return opts


def _split_voice(value: str) -> tuple[str | None, str | None]:
    if not value or value == DEFAULT_VOICE:
        return None, None
    engine, _, voice = value.partition("|")
    return engine, voice or None


def _join_voice(engine: str | None, voice: str | None) -> str:
    return f"{engine}|{voice or ''}" if engine else DEFAULT_VOICE


def _select(options: list[str], key: str, multiple: bool = False,
            mode: SelectSelectorMode = SelectSelectorMode.LIST) -> SelectSelector:
    return SelectSelector(SelectSelectorConfig(options=options, translation_key=key,
                                               multiple=multiple, mode=mode))


class NestorConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._options: dict[str, Any] = dict(DEFAULT_OPTIONS)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return NestorOptionsFlow()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()
        errors: dict[str, str] = {}
        if user_input is not None:
            key = user_input[CONF_LICENSE_KEY].strip()
            cloud_url = (user_input.get(CONF_CLOUD_URL) or DEFAULT_CLOUD_URL).strip()
            instance_id = uuid.uuid4().hex
            client = CloudClient(async_get_clientsession(self.hass), cloud_url, key, instance_id)
            try:
                await client.verify()
            except CloudError as err:
                errors["base"] = err.code if err.code in (
                    "invalid_key", "subscription_inactive", "too_many_instances",
                    "offline") else "generic"
            else:
                self._data = {CONF_LICENSE_KEY: key, CONF_CLOUD_URL: cloud_url,
                              CONF_INSTANCE_ID: instance_id}
                return await self.async_step_name()
        schema = vol.Schema({
            vol.Required(CONF_LICENSE_KEY): TextSelector(
                TextSelectorConfig(type=TextSelectorType.PASSWORD)),
            vol.Optional(CONF_CLOUD_URL, default=DEFAULT_CLOUD_URL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)),
        })
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors,
                                    description_placeholders={"trial_url": TRIAL_URL,
                                                              "help_url": HELP_URL})

    async def async_step_name(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            name = " ".join(str(user_input[OPT_NAME]).split())[:40] or "Nestor"
            self._options[OPT_NAME] = name
            return await self.async_step_personality()
        schema = vol.Schema({vol.Required(OPT_NAME, default="Nestor"): SelectSelector(
            SelectSelectorConfig(options=NAME_SUGGESTIONS, custom_value=True,
                                 mode=SelectSelectorMode.DROPDOWN))})
        return self.async_show_form(step_id="name", data_schema=schema)

    async def async_step_personality(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            self._options[OPT_PERSONALITY] = user_input[OPT_PERSONALITY]
            return await self.async_step_language()
        schema = vol.Schema({vol.Required(OPT_PERSONALITY, default="butler"):
                             _select(PERSONALITIES, "personality")})
        return self.async_show_form(step_id="personality", data_schema=schema,
                                    description_placeholders={"name": self._options[OPT_NAME]})

    async def async_step_language(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            self._options[OPT_LANGUAGE] = user_input[OPT_LANGUAGE]
            return await self.async_step_permissions()
        schema = vol.Schema({vol.Required(OPT_LANGUAGE, default="auto"):
                             _select(LANGUAGES, "language", mode=SelectSelectorMode.DROPDOWN)})
        return self.async_show_form(step_id="language", data_schema=schema)

    async def async_step_permissions(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            self._options[OPT_PERMISSIONS] = user_input[OPT_PERMISSIONS]
            return await self.async_step_voice()
        schema = vol.Schema({vol.Required(OPT_PERMISSIONS,
                                          default=DEFAULT_OPTIONS[OPT_PERMISSIONS]):
                             _select(ALL_PERMISSIONS, "permissions", multiple=True)})
        return self.async_show_form(step_id="permissions", data_schema=schema,
                                    description_placeholders={"name": self._options[OPT_NAME]})

    async def async_step_voice(self, user_input=None) -> ConfigFlowResult:
        if user_input is not None:
            engine, voice = _split_voice(user_input.get("voice", DEFAULT_VOICE))
            self._options.update({OPT_TTS_ENGINE: engine, OPT_TTS_VOICE: voice,
                                  OPT_VOICE_ASSISTANT: user_input[OPT_VOICE_ASSISTANT],
                                  OPT_SPEAK: user_input[OPT_SPEAK]})
            return self.async_create_entry(title=self._options[OPT_NAME], data=self._data,
                                           options=self._options)
        schema = vol.Schema({
            vol.Required("voice", default=DEFAULT_VOICE): SelectSelector(SelectSelectorConfig(
                options=_voice_options(self.hass), mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(OPT_VOICE_ASSISTANT, default=True): BooleanSelector(),
            vol.Required(OPT_SPEAK, default=False): BooleanSelector(),
        })
        return self.async_show_form(step_id="voice", data_schema=schema,
                                    description_placeholders={"name": self._options[OPT_NAME]})


class NestorOptionsFlow(OptionsFlow):
    """Settings > Devices & services > Nestor > Configure."""

    async def async_step_init(self, user_input=None) -> ConfigFlowResult:
        current = {**DEFAULT_OPTIONS, **self.config_entry.options}
        if user_input is not None:
            engine, voice = _split_voice(user_input.pop("voice", DEFAULT_VOICE))
            name = " ".join(str(user_input[OPT_NAME]).split())[:40] or "Nestor"
            return self.async_create_entry(data={**current, **user_input, OPT_NAME: name,
                                                 OPT_TTS_ENGINE: engine, OPT_TTS_VOICE: voice})
        schema = vol.Schema({
            vol.Required(OPT_NAME, default=current[OPT_NAME]): SelectSelector(
                SelectSelectorConfig(options=NAME_SUGGESTIONS, custom_value=True,
                                     mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(OPT_PERSONALITY, default=current[OPT_PERSONALITY]):
                _select(PERSONALITIES, "personality"),
            vol.Required(OPT_LANGUAGE, default=current[OPT_LANGUAGE]):
                _select(LANGUAGES, "language", mode=SelectSelectorMode.DROPDOWN),
            vol.Required(OPT_PERMISSIONS, default=current[OPT_PERMISSIONS]):
                _select(ALL_PERMISSIONS, "permissions", multiple=True),
            vol.Required("voice", default=_join_voice(current[OPT_TTS_ENGINE],
                                                      current[OPT_TTS_VOICE])):
                SelectSelector(SelectSelectorConfig(options=_voice_options(self.hass),
                                                    mode=SelectSelectorMode.DROPDOWN)),
            vol.Required(OPT_VOICE_ASSISTANT, default=current[OPT_VOICE_ASSISTANT]):
                BooleanSelector(),
            vol.Required(OPT_SPEAK, default=current[OPT_SPEAK]): BooleanSelector(),
        })
        return self.async_show_form(step_id="init", data_schema=schema)
