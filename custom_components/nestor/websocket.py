"""Websocket commands used by the Nestor sidebar panel."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components import websocket_api
from homeassistant.core import Context, HomeAssistant, callback

from .cloud import CloudError
from .const import (ALERT_RULES, ALL_PERMISSIONS, CHAT_EDITABLE, DOMAIN, LANGUAGES, OPT_ALERTS,
                    OPT_ENERGY_PRICE, OPT_LANGUAGE, OPT_NAME, OPT_NOTIFY_TARGETS, OPT_PERMISSIONS,
                    OPT_PERSONALITY, OPT_PROFILES, OPT_QUIET, OPT_SPEAK, OPT_TTS_ENGINE,
                    OPT_TTS_VOICE, OPT_VACATION, OPT_VOICE_ASSISTANT, PERMISSION_GROUPS,
                    PERSONALITIES, VERSION)
from .i18n import localize, pick_language
from .voice import list_voices, preview_url

ADMIN_ONLY = {OPT_PERMISSIONS, OPT_TTS_ENGINE, OPT_TTS_VOICE, OPT_VOICE_ASSISTANT, OPT_ALERTS,
              OPT_NOTIFY_TARGETS, OPT_PROFILES, OPT_ENERGY_PRICE}


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
                    ws_voices, ws_preview, ws_speak, ws_telegram_pair, ws_telegram_unpair,
                    ws_telegram_unlink_chat, ws_memory, ws_memory_forget, ws_health, ws_report,
                    ws_notify_targets, ws_test_notification):
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
        info = await rt.cloud.verify()
        if info.get("features"):
            rt.features = set(info["features"])
            rt.plan = info.get("plan")
        out.update({"ok": True, **info})
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
                                       "permissions": ALL_PERMISSIONS,
                                       "device_groups": list(PERMISSION_GROUPS),
                                       "alert_rules": ALERT_RULES,
                                       "features": sorted(rt.features), "plan": rt.plan})


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
            elif key in (OPT_VOICE_ASSISTANT, OPT_VACATION):
                cleaned[key] = bool(value)
            elif key == OPT_ALERTS:
                cleaned[key] = [r for r in value if r in ALERT_RULES]
            elif key == OPT_NOTIFY_TARGETS:
                cleaned[key] = None if value is None else [str(v) for v in value]
            elif key == OPT_PROFILES:
                cleaned[key] = {str(name)[:40]: {
                    "blocked": [g for g in p.get("blocked", []) if g in PERMISSION_GROUPS],
                    "allowed": [g for g in p.get("allowed", []) if g in PERMISSION_GROUPS]}
                    for name, p in (value or {}).items() if str(name).strip()}
            elif key == OPT_ENERGY_PRICE:
                cleaned[key] = max(0.0, min(float(value), 5.0))
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


@websocket_api.websocket_command({vol.Required("type"): "nestor/telegram/pair",
                                  vol.Optional("role", default="member"): vol.In(["member", "guest"]),
                                  vol.Optional("profile"): vol.Any(str, None),
                                  vol.Optional("guest_hours"): vol.Any(vol.All(int, vol.Range(1, 720)), None)})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_telegram_pair(hass, connection, msg):
    rt = _runtime(hass)
    try:
        data = await rt.cloud.telegram_pair(msg["role"], msg.get("profile"), msg.get("guest_hours"))
    except CloudError as err:
        connection.send_error(msg["id"], err.code, localize(err.code, pick_language(rt.options.get(OPT_LANGUAGE, "auto"), None), err.detail))
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
        connection.send_error(msg["id"], err.code, localize(err.code, pick_language(rt.options.get(OPT_LANGUAGE, "auto"), None), err.detail))
        return
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command({vol.Required("type"): "nestor/telegram/unlink_chat",
                                  vol.Required("chat_id"): int})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_telegram_unlink_chat(hass, connection, msg):
    try:
        await _runtime(hass).cloud.telegram_unlink_chat(msg["chat_id"])
    except CloudError as err:
        connection.send_error(msg["id"], err.code, err.code)
        return
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command({vol.Required("type"): "nestor/memory"})
@callback
def ws_memory(hass, connection, msg):
    connection.send_result(msg["id"], {"facts": _runtime(hass).memory.facts})


@websocket_api.websocket_command({vol.Required("type"): "nestor/memory/forget",
                                  vol.Required("id"): str})
@websocket_api.async_response
async def ws_memory_forget(hass, connection, msg):
    from .tools_home import ToolError
    try:
        await _runtime(hass).memory.forget(msg["id"])
    except ToolError as err:
        connection.send_error(msg["id"], "not_found", str(err))
        return
    connection.send_result(msg["id"], {"ok": True})


@websocket_api.websocket_command({vol.Required("type"): "nestor/health"})
@websocket_api.async_response
async def ws_health(hass, connection, msg):
    health = await _runtime(hass).watchers.health_check(notify=False)
    connection.send_result(msg["id"], {k: v for k, v in health.items() if not k.startswith("_")})


@websocket_api.websocket_command({vol.Required("type"): "nestor/report"})
@callback
def ws_report(hass, connection, msg):
    rt = _runtime(hass)
    connection.send_result(msg["id"], {
        "month": rt.stats.summary(price=float(rt.options.get(OPT_ENERGY_PRICE, 0.17))),
        "recent_notifications": rt.notifier.sent_log[-10:],
        "currency": hass.config.currency})


@websocket_api.websocket_command({vol.Required("type"): "nestor/notify_targets"})
@callback
def ws_notify_targets(hass, connection, msg):
    rt = _runtime(hass)
    phones = [s for s in hass.services.async_services_for_domain("notify")
              if s.startswith("mobile_app_")]
    connection.send_result(msg["id"], {"available": phones,
                                       "selected": rt.notifier.phone_targets()})


@websocket_api.websocket_command({vol.Required("type"): "nestor/notify/test"})
@websocket_api.require_admin
@websocket_api.async_response
async def ws_test_notification(hass, connection, msg):
    rt = _runtime(hass)
    await rt.notifier.send(f"👋 Test from {rt.options.get(OPT_NAME, 'Nestor')}. "
                           "If you see this, notifications work.", urgent=False, key="test")
    connection.send_result(msg["id"], {"ok": True})
