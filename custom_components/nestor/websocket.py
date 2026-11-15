"""Websocket commands used by the Nestor sidebar panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import Context, HomeAssistant, callback

from .cloud import CloudError
from .const import (ALL_PERMISSIONS, CHAT_EDITABLE, DOMAIN, LANGUAGES, OPT_LANGUAGE, OPT_NAME,
                    OPT_PERMISSIONS, OPT_PERSONALITY, OPT_QUIET, OPT_SPEAK, OPT_TTS_ENGINE,
                    OPT_TTS_VOICE, OPT_VOICE_ASSISTANT, PERSONALITIES, VERSION)
from .i18n import localize, pick_language
from .voice import list_voices, preview_url

ADMIN_ONLY = {OPT_PERMISSIONS, OPT_TTS_ENGINE, OPT_TTS_VOICE, OPT_VOICE_ASSISTANT}


def _runtime(hass: HomeAssistant):
    entries = hass.config_entries.async_loaded_entries(DOMAIN)
    if not entries:
        raise ValueError("Nestor is not set up")
    return entries[0].runtime_data


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    if hass.data.get(f"{DOMAIN}_ws"):
        return
    for handler in (ws_chat, ws_reset, ws_status, ws_get_settings, ws_update_settings,
                    ws_voices, ws_preview, ws_speak, ws_telegram_pair, ws_telegram_unpair):
        websocket_api.async_register_command(hass, handler)
    hass.data[f"{DOMAIN}_ws"] = True


@websocket_api.websocket_command({vol.Required("type"): "nestor/chat",
                                  vol.Required("text"): vol.All(str, vol.Length(1, 2000)),
                                  vol.Optional("conversation_id", default="panel"): str,
                                  vol.Optional("ui_language"): str})
@websocket_api.async_response
async def ws_chat(hass, connection, msg):
    rt = _runtime(hass)
    cid = f"panel-{connection.user.id}-{msg['conversation_id'][:40]}"
    result = await rt.agent.ask(cid, msg["text"], ui_language=msg.get("ui_language"),
                                context=Context(user_id=connection.user.id))
    if result.get("speak"):
        opts = rt.options
        try:
            result["audio_url"] = await preview_url(hass, result["reply"],
                                                    opts.get(OPT_TTS_ENGINE),
                                                    opts.get(OPT_TTS_VOICE))
        except Exception:
            result["audio_url"] = None
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "nestor/reset",
                                  vol.Optional("conversation_id", default="panel"): str})
@callback
def ws_reset(hass, connection, msg):
    _runtime(hass).agent.reset(f"panel-{connection.user.id}-{msg['conversation_id'][:40]}")
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command({vol.Required("type"): "nestor/status",
                                  vol.Optional("ui_language"): str})
@websocket_api.async_response
async def ws_status(hass, connection, msg):
    rt = _runtime(hass)
    lang = pick_language(rt.options.get(OPT_LANGUAGE, "auto"), msg.get("ui_language"))
    out: dict[str, Any] = {"version": VERSION}
    try:
        out.update({"ok": True, **await rt.cloud.verify()})
    except CloudError as err:
        out.update({"ok": False, "error": err.code,
                    "message": localize(err.code, lang, err.detail)})
    try:
        out["telegram"] = await rt.cloud.telegram_status()
    except CloudError:
        out["telegram"] = {"linked": False}
    connection.send_result(msg["id"], out)


@websocket_api.websocket_command({vol.Required("type"): "nestor/settings"})
@callback
def ws_get_settings(hass, connection, msg):
    rt = _runtime(hass)
    connection.send_result(msg["id"], {"options": rt.options,
                                       "is_admin": connection.user.is_admin,
                                       "personalities": PERSONALITIES, "languages": LANGUAGES,
                                       "permissions": ALL_PERMISSIONS})


@websocket_api.websocket_command({vol.Required("type"): "nestor/settings/update",
                                  vol.Required("changes"): dict})
@websocket_api.async_response
async def ws_update_settings(hass, connection, msg):
    from .agent import validate_setting
    from .tools_home import ToolError

    rt = _runtime(hass)
    cleaned: dict[str, Any] = {}
    for key, value in msg["changes"].items():
        if key in ADMIN_ONLY and not connection.user.is_admin:
            connection.send_error(msg["id"], "unauthorized",
                                  "Only a Home Assistant administrator can change this.")
            return
        try:
            if key in CHAT_EDITABLE:
                cleaned[key] = validate_setting(key, value)
            elif key == OPT_PERMISSIONS:
                cleaned[key] = [p for p in value if p in ALL_PERMISSIONS]
            elif key in (OPT_TTS_ENGINE, OPT_TTS_VOICE):
                cleaned[key] = value or None
            elif key == OPT_VOICE_ASSISTANT:
                cleaned[key] = bool(value)
            else:
                raise ToolError(f"Unknown setting {key}")
        except ToolError as err:
            connection.send_error(msg["id"], "invalid", str(err))
            return
    await rt.async_update_options(cleaned)
    connection.send_result(msg["id"], {"options": rt.options})


@websocket_api.websocket_command({vol.Required("type"): "nestor/voices",
                                  vol.Optional("language"): str})
@callback
def ws_voices(hass, connection, msg):
    connection.send_result(msg["id"], {"engines": list_voices(hass, msg.get("language"))})


@websocket_api.websocket_command({vol.Required("type"): "nestor/voice/preview",
                                  vol.Required("text"): vol.All(str, vol.Length(1, 300)),
                                  vol.Optional("engine"): vol.Any(str, None),
                                  vol.Optional("voice"): vol.Any(str, None)})
@websocket_api.async_response
async def ws_preview(hass, connection, msg):
    url = await preview_url(hass, msg["text"], msg.get("engine"), msg.get("voice"))
    connection.send_result(msg["id"], {"url": url})


@websocket_api.websocket_command({vol.Required("type"): "nestor/speak",
                                  vol.Required("text"): vol.All(str, vol.Length(1, 2000))})
@websocket_api.async_response
async def ws_speak(hass, connection, msg):
    opts = _runtime(hass).options
    url = await preview_url(hass, msg["text"], opts.get(OPT_TTS_ENGINE), opts.get(OPT_TTS_VOICE))
    connection.send_result(msg["id"], {"url": url})


@websocket_api.websocket_command({vol.Required("type"): "nestor/telegram/pair"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_telegram_pair(hass, connection, msg):
    rt = _runtime(hass)
    try:
        data = await rt.cloud.telegram_pair()
    except CloudError as err:
        connection.send_error(msg["id"], err.code, localize(err.code, "en", err.detail))
        return
    rt.telegram.start()
    connection.send_result(msg["id"], data)


@websocket_api.websocket_command({vol.Required("type"): "nestor/telegram/unpair"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_telegram_unpair(hass, connection, msg):
    rt = _runtime(hass)
    try:
        await rt.cloud.telegram_unpair()
    except CloudError as err:
        connection.send_error(msg["id"], err.code, localize(err.code, "en", err.detail))
        return
    connection.send_result(msg["id"], {"ok": True})
