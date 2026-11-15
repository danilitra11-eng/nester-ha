"""Voices: list/preview TTS voices, speak, transcribe, and the Nestor Assist pipeline."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


def list_voices(hass: HomeAssistant, language: str | None = None) -> list[dict[str, Any]]:
    """All TTS engines with their voices for the language (HA's own voices: Piper, Cloud...)."""
    from homeassistant.components.tts.const import DATA_COMPONENT

    lang = language or hass.config.language
    component = hass.data.get(DATA_COMPONENT)
    engines = []
    for entity in (component.entities if component else []):
        langs = entity.supported_languages or []
        match = next((l for l in langs if l == lang), None) or next(
            (l for l in langs if l.split("-")[0] == lang.split("-")[0]), None)
        voices = []
        if match:
            try:
                voices = [{"voice_id": v.voice_id, "name": v.name}
                          for v in (entity.async_get_supported_voices(match) or [])]
            except Exception:  # some engines don't implement voices
                voices = []
        engines.append({"engine_id": entity.entity_id, "name": entity.name or entity.entity_id,
                        "language": match, "voices": voices})
    return engines


async def synthesize(hass: HomeAssistant, text: str, engine: str | None, voice: str | None,
                     language: str | None = None) -> tuple[str, bytes] | None:
    """Speak text with the chosen voice. Returns (extension, audio) or None."""
    from homeassistant.components import tts

    engine = tts.async_resolve_engine(hass, engine)
    if engine is None:
        return None
    options = {"voice": voice} if voice else None
    try:
        stream = tts.async_create_stream(hass, engine, language=language, options=options)
        stream.async_set_message(text)
        data = b"".join([chunk async for chunk in stream.async_stream_result()])
        return stream.extension, data
    except Exception as err:  # engine errors shouldn't break the chat
        _LOGGER.warning("Text-to-speech failed: %s", err)
        return None


async def preview_url(hass: HomeAssistant, text: str, engine: str | None, voice: str | None,
                      language: str | None = None) -> str | None:
    """A URL the browser can play, for the voice picker's ▶ button and read-aloud."""
    from homeassistant.components import tts

    engine = tts.async_resolve_engine(hass, engine)
    if engine is None:
        return None
    options = {"voice": voice} if voice else None
    stream = tts.async_create_stream(hass, engine, language=language, options=options)
    stream.async_set_message(text)
    return stream.url


def _ffmpeg(hass: HomeAssistant) -> str:
    try:
        from homeassistant.components.ffmpeg import get_ffmpeg_manager
        return get_ffmpeg_manager(hass).binary
    except Exception:
        return "ffmpeg"


async def _run_ffmpeg(hass: HomeAssistant, args: list[str], data: bytes) -> bytes:
    proc = await asyncio.create_subprocess_exec(
        _ffmpeg(hass), "-hide_banner", "-loglevel", "error", *args,
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE)
    out, err = await asyncio.wait_for(proc.communicate(data), 60)
    if proc.returncode != 0:
        raise RuntimeError(err.decode(errors="ignore")[:300])
    return out


async def to_ogg_opus(hass: HomeAssistant, audio: bytes) -> bytes:
    """Telegram voice messages must be OGG/Opus."""
    return await _run_ffmpeg(hass, ["-i", "pipe:0", "-c:a", "libopus", "-b:a", "32k",
                                    "-f", "ogg", "pipe:1"], audio)


async def transcribe(hass: HomeAssistant, audio: bytes, language: str | None = None) -> str | None:
    """Speech to text with the home's own STT engine (Whisper, Cloud...)."""
    from homeassistant.components import stt

    engine_id = stt.async_default_engine(hass)
    engine = stt.async_get_speech_to_text_engine(hass, engine_id) if engine_id else None
    if engine is None:
        return None
    lang = language or hass.config.language
    supported = engine.supported_languages
    if lang not in supported:
        lang = next((l for l in supported if l.split("-")[0] == lang.split("-")[0]),
                    supported[0] if supported else lang)
    pcm = await _run_ffmpeg(hass, ["-i", "pipe:0", "-f", "s16le", "-ac", "1", "-ar", "16000",
                                   "pipe:1"], audio)
    metadata = stt.SpeechMetadata(language=lang, format=stt.AudioFormats.WAV,
                                  codec=stt.AudioCodecs.PCM, bit_rate=stt.AudioBitRates.BITRATE_16,
                                  sample_rate=stt.AudioSampleRates.SAMPLERATE_16000,
                                  channel=stt.AudioChannels.CHANNEL_MONO)

    async def chunks():
        for i in range(0, len(pcm), 4096):
            yield pcm[i:i + 4096]

    result = await engine.async_process_audio_stream(metadata, chunks())
    if result.result == stt.SpeechResultState.SUCCESS and result.text:
        return result.text
    return None


async def ensure_pipeline(hass: HomeAssistant, entity_id: str, name: str,
                          tts_engine: str | None, tts_voice: str | None) -> str | None:
    """Create (or update) a "Nestor" voice assistant and make it the preferred one.

    It copies speech-to-text and wake word from the current preferred assistant,
    so phones, watches and voice speakers start talking to Nestor right away.
    """
    try:
        from homeassistant.components.assist_pipeline.pipeline import (
            KEY_ASSIST_PIPELINE, async_get_pipeline, async_get_pipelines)
    except ImportError:
        return None
    if KEY_ASSIST_PIPELINE not in hass.data:
        return None
    store = hass.data[KEY_ASSIST_PIPELINE].pipeline_store
    preferred = async_get_pipeline(hass)
    lang = hass.config.language
    tts_lang = preferred.tts_language
    if tts_engine and tts_engine != preferred.tts_engine:
        tts_lang = next((e["language"] for e in list_voices(hass, lang)
                         if e["engine_id"] == tts_engine), None) or lang
    settings = {
        "conversation_engine": entity_id,
        "conversation_language": lang,
        "language": preferred.language or lang,
        "name": name,
        "stt_engine": preferred.stt_engine,
        "stt_language": preferred.stt_language,
        "tts_engine": tts_engine or preferred.tts_engine,
        "tts_language": tts_lang if (tts_engine or preferred.tts_engine) else None,
        "tts_voice": tts_voice if tts_engine else preferred.tts_voice,
        "wake_word_entity": preferred.wake_word_entity,
        "wake_word_id": preferred.wake_word_id,
    }
    existing = next((p for p in async_get_pipelines(hass)
                     if p.conversation_engine == entity_id), None)
    try:
        if existing:
            item = await store.async_update_item(existing.id, settings)
        else:
            item = await store.async_create_item(settings)
        store.async_set_preferred_item(item.id)
        return item.id
    except Exception as err:
        _LOGGER.warning("Couldn't set up the Nestor voice assistant: %s", err)
        return None
