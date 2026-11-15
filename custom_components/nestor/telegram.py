"""Telegram via the central Nestor bot.

Telegram talks to the Nestor cloud; this loop asks the cloud for new messages
(long polling, so no ports are opened on the home network), runs them through
the same agent and sends the reply back. Voice notes are transcribed with the
home's own speech-to-text, and answered with a voice note when they came in as one.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from homeassistant.core import Context

from .cloud import CloudError
from .const import OPT_LANGUAGE, OPT_TTS_ENGINE, OPT_TTS_VOICE
from .i18n import localize, pick_language
from .voice import synthesize, to_ogg_opus, transcribe

if TYPE_CHECKING:
    from . import NestorRuntime

_LOGGER = logging.getLogger(__name__)

NOT_UNDERSTOOD = {
    "en": "Sorry, I couldn't understand that voice message.",
    "es": "Lo siento, no pude entender ese mensaje de voz.",
    "he": "סליחה, לא הצלחתי להבין את ההודעה הקולית.",
    "ru": "Извините, не удалось разобрать голосовое сообщение.",
}


class TelegramRelay:
    def __init__(self, runtime: "NestorRuntime") -> None:
        self.rt = runtime
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None or self._task.done():
            self._task = self.rt.entry.async_create_background_task(
                self.rt.hass, self._loop(), "nestor_telegram")

    def stop(self) -> None:
        if self._task:
            self._task.cancel()
            self._task = None

    async def _loop(self) -> None:
        backoff = 5
        while True:
            try:
                messages = await self.rt.cloud.telegram_poll(wait=25)
                backoff = 5
            except CloudError as err:
                if err.code in ("invalid_key", "subscription_inactive", "telegram_not_linked"):
                    _LOGGER.info("Telegram relay paused: %s", err.code)
                    await asyncio.sleep(300)
                else:
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 120)
                continue
            for msg in messages:
                try:
                    await self.handle(msg)
                except Exception:  # one bad message must not stop the loop
                    _LOGGER.exception("Failed to handle a Telegram message")

    async def handle(self, msg: dict) -> None:
        hass = self.rt.hass
        opts = self.rt.options
        chat_id = msg["chat_id"]
        lang = pick_language(opts.get(OPT_LANGUAGE, "auto"), msg.get("language_code"))
        if msg.get("callback"):
            await self.rt.cloud.telegram_reply(chat_id,
                                               await self.rt.notifier.handle_callback(msg["callback"]))
            return
        text = msg.get("text")
        was_voice = bool(msg.get("voice"))
        if was_voice:
            audio = await self.rt.cloud.telegram_file(chat_id, msg["message_id"])
            try:
                text = await transcribe(hass, audio)
            except Exception as err:
                _LOGGER.warning("Transcribing a Telegram voice note failed: %s", err)
                text = None
            if not text:
                await self.rt.cloud.telegram_reply(
                    chat_id, NOT_UNDERSTOOD.get(lang, NOT_UNDERSTOOD["en"]))
                return
        if not text:
            return
        result = await self.rt.agent.ask(f"telegram-{chat_id}", text, ui_language=lang,
                                         context=Context(),
                                         speaker=msg.get("profile") or msg.get("name"),
                                         guest=msg.get("role") == "guest")
        reply = result["reply"]
        voice = None
        # Voice notes get a spoken answer, unless it's quiet hours.
        if was_voice and self.rt.agent.should_speak_anytime():
            spoken = await synthesize(hass, reply, opts.get(OPT_TTS_ENGINE),
                                      opts.get(OPT_TTS_VOICE))
            if spoken:
                try:
                    voice = await to_ogg_opus(hass, spoken[1])
                except Exception as err:
                    _LOGGER.warning("Converting the spoken reply failed: %s", err)
        if result.get("error"):
            reply = localize(result["error"], lang, None) if not reply else reply
        await self.rt.cloud.telegram_reply(chat_id, reply, voice)
