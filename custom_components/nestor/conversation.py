"""Nestor as a Home Assistant conversation agent, so Assist (phone app, watch,
voice speakers, the Assist dialog) talks to Nestor."""

from __future__ import annotations

from typing import Literal

from homeassistant.components import conversation
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import intent
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import ulid as ulid_util

from .const import DOMAIN, OPT_NAME, OPT_TTS_ENGINE, OPT_TTS_VOICE, OPT_VOICE_ASSISTANT
from .voice import ensure_pipeline


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry,
                            async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([NestorConversationEntity(entry)])


class NestorConversationEntity(conversation.ConversationEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_supported_features = conversation.ConversationEntityFeature.CONTROL

    def __init__(self, entry: ConfigEntry) -> None:
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_conversation"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)}, name=entry.title,
            manufacturer="Nestor", model="AI Butler", entry_type=DeviceEntryType.SERVICE)

    @property
    def supported_languages(self) -> Literal["*"]:
        return "*"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        conversation.async_set_agent(self.hass, self.entry, self)
        opts = self.entry.runtime_data.options
        if opts.get(OPT_VOICE_ASSISTANT, True):
            await ensure_pipeline(self.hass, self.entity_id, opts.get(OPT_NAME, "Nestor"),
                                  opts.get(OPT_TTS_ENGINE), opts.get(OPT_TTS_VOICE))

    async def async_will_remove_from_hass(self) -> None:
        conversation.async_unset_agent(self.hass, self.entry)
        await super().async_will_remove_from_hass()

    async def async_process(
        self, user_input: conversation.ConversationInput
    ) -> conversation.ConversationResult:
        conversation_id = user_input.conversation_id or ulid_util.ulid_now()
        result = await self.entry.runtime_data.agent.ask(
            f"assist-{conversation_id}", user_input.text, ui_language=user_input.language,
            context=user_input.context)
        response = intent.IntentResponse(language=user_input.language)
        if result.get("error"):
            response.async_set_error(intent.IntentResponseErrorCode.UNKNOWN, result["reply"])
        else:
            response.async_set_speech(result["reply"])
        return conversation.ConversationResult(response=response,
                                               conversation_id=conversation_id)
