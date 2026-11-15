"""Add-on entry point: aiohttp server behind Home Assistant ingress."""

from __future__ import annotations

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Any

import aiohttp
from aiohttp import web

from .conversation import Butler, CloudClient, CloudError
from .ha import SUPERVISOR_URL, HomeAssistant, HAError, ToolRunner
from .i18n import localize, pick_language
from .settings import PANEL_EDITABLE, Settings, SettingsError

VERSION = "0.1.0"
OPTIONS_PATH = Path("/data/options.json")
INSTANCE_PATH = Path("/data/instance_id")
SETTINGS_PATH = Path("/data/settings.json")
STATIC = Path(__file__).parent / "static"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("nestor")

# HA ingress proxies from this address only; reject anything else.
INGRESS_IPS = {"172.30.32.2", "127.0.0.1"}


def load_options() -> dict[str, Any]:
    try:
        return json.loads(OPTIONS_PATH.read_text())
    except (OSError, ValueError):
        return {}


def instance_id() -> str:
    try:
        return INSTANCE_PATH.read_text().strip()
    except OSError:
        new = uuid.uuid4().hex
        try:
            INSTANCE_PATH.write_text(new)
        except OSError:
            pass
        return new


@web.middleware
async def ingress_only(request: web.Request, handler):
    if request.remote not in INGRESS_IPS:
        raise web.HTTPForbidden()
    return await handler(request)


async def index(request: web.Request) -> web.Response:
    # Everything user-specific is loaded by the page from /api/settings.
    return web.FileResponse(STATIC / "index.html")


def _lang(request: web.Request, ui_lang: str | None = None) -> str:
    return pick_language(request.app["settings"]["language"], ui_lang or request.query.get("lang"))


async def status(request: web.Request) -> web.Response:
    try:
        info = await request.app["cloud"].verify()
        return web.json_response({"ok": True, **info})
    except CloudError as err:
        return web.json_response({"ok": False, "error": err.code,
                                  "message": localize(err.code, _lang(request), err.detail)})


async def get_settings(request: web.Request) -> web.Response:
    return web.json_response(request.app["settings"].public())


async def put_settings(request: web.Request) -> web.Response:
    try:
        changes = await request.json()
        if not isinstance(changes, dict):
            raise ValueError
    except ValueError:
        raise web.HTTPBadRequest()
    changes.pop("license_key", None)  # keys go through /api/setup/license, which checks them
    try:
        request.app["settings"].update(changes, allowed=PANEL_EDITABLE)
    except SettingsError as err:
        return web.json_response({"ok": False, "message": str(err)}, status=400)
    return web.json_response({"ok": True, "settings": request.app["settings"].public()})


async def setup_license(request: web.Request) -> web.Response:
    """Check a key typed into the wizard before saving it."""
    body = await request.json()
    key = str(body.get("license_key", "")).strip()[:200]
    try:
        info = await request.app["cloud"].verify(key)
    except CloudError as err:
        return web.json_response({"ok": False, "error": err.code,
                                  "message": localize(err.code, _lang(request), err.detail)})
    request.app["settings"].update({"license_key": key}, allowed=PANEL_EDITABLE)
    return web.json_response({"ok": True, **info})


async def setup_suggestion(request: web.Request) -> web.Response:
    """A real device from this home for the wizard's 'try it' step."""
    butler: Butler = request.app["butler"]
    try:
        states = await butler.tools.ha.states()
    except HAError:
        return web.json_response({"name": None})
    for domain in ("light", "switch", "fan", "cover", "media_player"):
        if domain not in butler.tools.allowed:
            continue
        for st in states:
            if st["entity_id"].startswith(domain + "."):
                name = st.get("attributes", {}).get("friendly_name") or st["entity_id"]
                return web.json_response({"name": name, "domain": domain,
                                          "state": st.get("state")})
    return web.json_response({"name": None})


async def chat(request: web.Request) -> web.Response:
    try:
        body = await request.json()
    except ValueError:
        raise web.HTTPBadRequest()
    text = str(body.get("text", "")).strip()[:2000]
    cid = str(body.get("conversation_id", "default"))[:64]
    ui_lang = str(body.get("ui_language", ""))[:16]
    if not text:
        raise web.HTTPBadRequest()
    try:
        result = await request.app["butler"].ask(cid, text, ui_lang)
    except HAError as err:
        log.error("HA error: %s", err)
        result = {"reply": localize("generic", _lang(request, ui_lang)),
                  "error": "ha_error"}
    return web.json_response(result)


async def reset(request: web.Request) -> web.Response:
    body = await request.json()
    request.app["butler"].reset(str(body.get("conversation_id", "default"))[:64])
    return web.json_response({"ok": True})


async def on_startup(app: web.Application) -> None:
    opts = app["options"]
    settings: Settings = app["settings"]
    session = aiohttp.ClientSession()
    app["session"] = session
    # NESTOR_HA_URL is for local development only; in HA the Supervisor proxy is used.
    ha = HomeAssistant(session, base_url=os.environ.get("NESTOR_HA_URL", SUPERVISOR_URL))
    tz, temp_unit = "UTC", ""
    try:
        ha_config = await ha.config()
        tz = ha_config.get("time_zone", "UTC")
        temp_unit = (ha_config.get("unit_system") or {}).get("temperature", "")
    except HAError as err:
        log.warning("Could not read HA config: %s", err)
    cloud = CloudClient(session, opts.get("cloud_url", ""), lambda: settings["license_key"],
                        instance_id(), VERSION)
    tools = ToolRunner(ha, settings["allowed_domains"], settings["allow_security_devices"])
    settings.on_change(lambda st: tools.set_permissions(st["allowed_domains"],
                                                        st["allow_security_devices"]))
    app["cloud"] = cloud
    app["butler"] = Butler(cloud, tools, settings, tz, temp_unit)
    if settings["license_key"]:
        try:
            info = await cloud.verify()
            log.info("License OK - plan %s, %s requests left this month",
                     info.get("plan"), info.get("quota_remaining"))
        except CloudError as err:
            log.warning("License check failed: %s", err.code)
    else:
        log.info("No license key yet - open the Nestor panel to finish setup.")
    log.info("Controllable domains: %s", ", ".join(sorted(tools.allowed)))


async def on_cleanup(app: web.Application) -> None:
    await app["session"].close()


def build_app(options: dict[str, Any], settings_path: Path = SETTINGS_PATH) -> web.Application:
    app = web.Application(middlewares=[ingress_only], client_max_size=64 * 1024)
    app["options"] = options
    app["settings"] = Settings(options, settings_path)
    app.router.add_get("/", index)
    app.router.add_get("/api/status", status)
    app.router.add_get("/api/settings", get_settings)
    app.router.add_post("/api/settings", put_settings)
    app.router.add_post("/api/setup/license", setup_license)
    app.router.add_get("/api/setup/suggestion", setup_suggestion)
    app.router.add_post("/api/chat", chat)
    app.router.add_post("/api/reset", reset)
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    return app


if __name__ == "__main__":
    web.run_app(build_app(load_options()), host="0.0.0.0", port=8099, access_log=None)
