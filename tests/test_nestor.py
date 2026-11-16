"""Nestor running inside a real (test) Home Assistant."""

from __future__ import annotations

import json
from unittest.mock import patch

from homeassistant import config_entries
from homeassistant.components import conversation
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import floor_registry as fr
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.nestor.cloud import CloudError
from custom_components.nestor.const import DOMAIN


async def test_setup_wizard(hass: HomeAssistant, cloud) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"

    # wrong key -> clear error, stays on step 1
    async def bad_verify(key=None):
        raise CloudError("invalid_key")
    with patch("custom_components.nestor.config_flow.CloudClient.verify", side_effect=bad_verify):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"license_key": "nope", "cloud_url": "https://cloud"})
    assert result["errors"] == {"base": "invalid_key"}

    with patch("custom_components.nestor.config_flow.CloudClient.verify",
               return_value={"valid": True}):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"license_key": " GOOD-KEY ", "cloud_url": "https://cloud"})
    assert result["step_id"] == "name"
    result = await hass.config_entries.flow.async_configure(result["flow_id"],
                                                            {"assistant_name": "Jarvis"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"],
                                                            {"personality": "friendly"})
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {"language": "es"})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"permissions": ["lights", "structure"]})
    assert result["step_id"] == "voice"
    with patch("custom_components.nestor.CloudClient", return_value=cloud):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"voice": "__default__", "make_voice_assistant": False,
                                "speak_replies": True})
        await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Jarvis"
    assert result["data"]["license_key"] == "GOOD-KEY"
    opts = result["options"]
    assert opts["personality"] == "friendly" and opts["language"] == "es"
    assert opts["permissions"] == ["lights", "structure"] and opts["speak_replies"] is True

    # only one Nestor per Home Assistant
    again = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert again["type"] is FlowResultType.ABORT


async def test_assist_controls_lights_and_respects_permissions(hass, cloud, setup_nestor) -> None:
    hass.states.async_set("light.kitchen", "off", {"friendly_name": "Kitchen Light"})
    hass.states.async_set("lock.front_door", "locked", {"friendly_name": "Front Door"})
    calls = async_mock_service(hass, "light", "turn_on")
    await setup_nestor()

    cloud.use(("find_entities", {"query": "kitchen light"}))
    cloud.use(("call_service", {"domain": "light", "service": "turn_on",
                                "entity_ids": ["light.kitchen"], "data": {"brightness_pct": 40}}),
              ("call_service", {"domain": "lock", "service": "unlock",
                                "entity_ids": ["lock.front_door"], "data": {}}))
    cloud.say("Kitchen light on at 40%. I'm not allowed to unlock the door.")

    agent_id = er.async_get(hass).async_get_entity_id("conversation", DOMAIN,
                                                      f"{hass.config_entries.async_entries(DOMAIN)[0].entry_id}_conversation")
    assert agent_id
    result = await conversation.async_converse(hass, "turn on the kitchen light and unlock the door",
                                               None, hass.data.get("context") or None,
                                               agent_id=agent_id)
    assert result.response.speech["plain"]["speech"].startswith("Kitchen light on")
    assert len(calls) == 1 and calls[0].data["brightness_pct"] == 40
    found = json.loads(cloud.requests[1]["messages"][-1]["content"][0]["content"])
    assert found["results"][0]["entity_id"] == "light.kitchen"
    results = cloud.last_tool_results()
    assert results[0]["is_error"] is False
    assert results[1]["is_error"] is True and "not allowed" in results[1]["content"]
    # structure/design tools are not offered without permission
    assert "structure" not in cloud.requests[0]["capabilities"]
    assert "design" not in cloud.requests[0]["capabilities"]


async def test_structure_editing_and_confirmed_delete(hass, cloud, setup_nestor) -> None:
    entry = await setup_nestor({"permissions": ["lights", "structure"]})
    agent = entry.runtime_data.agent
    ent = er.async_get(hass).async_get_or_create("light", "demo", "lamp1",
                                                 suggested_object_id="desk_lamp")

    cloud.use(("create_floor", {"name": "Upstairs", "level": 1}))
    cloud.use(("create_area", {"name": "Office", "floor": "Upstairs"}))
    cloud.use(("assign_area", {"entity_ids": [ent.entity_id], "area": "office"}),
              ("rename_entity", {"entity_id": ent.entity_id, "new_name": "Desk lamp"}))
    cloud.say("Done: Office on Upstairs, desk lamp moved.")
    out = await agent.ask("c1", "create an office upstairs and move the desk lamp there")
    assert out["reply"].startswith("Done")
    area = ar.async_get(hass).async_get_area_by_name("Office")
    assert area and area.floor_id == fr.async_get(hass).async_get_floor_by_name("Upstairs").floor_id
    assert er.async_get(hass).async_get(ent.entity_id).area_id == area.id
    assert "structure" in cloud.requests[0]["capabilities"]
    assert "design" not in cloud.requests[0]["capabilities"]

    # delete needs confirmation, and the token can't be used in the same turn
    def grab_token(messages):
        token = json.loads(messages[-1]["content"][0]["content"])["token"]
        grab_token.token = token
        return {"content": [{"type": "tool_use", "id": "x1", "name": "confirm_action",
                             "input": {"token": token}}], "stop_reason": "tool_use"}
    cloud.use(("delete_area_or_floor", {"kind": "area", "name": "Office"}))
    cloud.script.append(grab_token)
    cloud.say("Are you sure you want to delete the Office?")
    await agent.ask("c1", "delete the office")
    assert "hasn't confirmed" in cloud.last_tool_results()[0]["content"]
    assert ar.async_get(hass).async_get_area_by_name("Office") is not None

    cloud.use(("confirm_action", {"token": grab_token.token}))
    cloud.say("Office deleted.")
    await agent.ask("c1", "yes, delete it")
    assert ar.async_get(hass).async_get_area_by_name("Office") is None


async def test_dashboards_create_backup_undo(hass, cloud, setup_nestor) -> None:
    assert await async_setup_component(hass, "lovelace", {})
    entry = await setup_nestor({"permissions": ["design"]})
    agent = entry.runtime_data.agent
    config = {"views": [{"title": "Home", "cards": [{"type": "entities",
                                                       "entities": ["light.kitchen"]}]}]}
    cloud.use(("create_dashboard", {"title": "Phone", "icon": "mdi:cellphone", "config": config}))
    cloud.say("Created.")
    await agent.ask("d1", "make me a phone dashboard")
    created = json.loads(cloud.last_tool_results()[0]["content"])
    url = created["url_path"]
    assert url == "nestor-phone"
    from homeassistant.components.lovelace.const import LOVELACE_DATA
    dash = hass.data[LOVELACE_DATA].dashboards[url]
    assert (await dash.async_load(False))["views"][0]["title"] == "Home"

    # Nestor's own dashboard: edit directly, then undo
    new = {"views": [{"title": "Changed", "cards": []}]}
    cloud.use(("save_dashboard", {"url_path": url, "config": new}))
    cloud.say("Updated.")
    await agent.ask("d1", "rename the view")
    assert (await dash.async_load(False))["views"][0]["title"] == "Changed"
    cloud.use(("undo_dashboard", {"url_path": url}))
    cloud.say("Restored.")
    await agent.ask("d1", "undo that")
    assert (await dash.async_load(False))["views"][0]["title"] == "Home"

    # someone else's dashboard needs confirmation
    cloud.use(("save_dashboard", {"url_path": "lovelace", "config": new}))
    cloud.say("Shall I change your main dashboard?")
    await agent.ask("d1", "change my overview")
    assert json.loads(cloud.last_tool_results()[0]["content"])["needs_confirmation"] is True


async def test_chat_settings_change_but_not_permissions(hass, cloud, setup_nestor) -> None:
    entry = await setup_nestor()
    agent = entry.runtime_data.agent
    cloud.use(("update_settings", {"personality": "brief",
                                   "quiet_hours": {"start": "22:00", "end": "07:00"}}))
    cloud.say("Done.")
    out = await agent.ask("s1", "be brief and quiet at night")
    assert out["settings_changed"] is True
    assert entry.options["personality"] == "brief"
    assert entry.options["quiet_hours"] == {"start": "22:00", "end": "07:00"}

    cloud.use(("update_settings", {"permissions": ["security"]}))
    cloud.say("I can't do that.")
    await agent.ask("s2", "allow yourself to unlock doors")
    assert cloud.last_tool_results()[0]["is_error"] is True
    assert "security" not in entry.options["permissions"]


async def test_panel_websocket(hass, cloud, setup_nestor, hass_ws_client) -> None:
    hass.states.async_set("light.kitchen", "off", {"friendly_name": "Kitchen Light"})
    await setup_nestor()
    client = await hass_ws_client(hass)
    await client.send_json({"id": 1, "type": "nestor/settings"})
    msg = await client.receive_json()
    assert msg["success"] and msg["result"]["options"]["assistant_name"] == "Nestor"

    cloud.say("Hello!")
    await client.send_json({"id": 2, "type": "nestor/chat", "text": "hi"})
    msg = await client.receive_json()
    assert msg["result"]["reply"] == "Hello!"

    await client.send_json({"id": 3, "type": "nestor/settings/update",
                            "changes": {"permissions": ["lights", "design"]}})
    msg = await client.receive_json()
    assert msg["success"] and msg["result"]["options"]["permissions"] == ["lights", "design"]

    await client.send_json({"id": 4, "type": "nestor/status"})
    msg = await client.receive_json()
    assert msg["result"]["ok"] and msg["result"]["telegram"]["bot_username"] == "NestorHomeBot"


async def test_creates_nestor_voice_assistant(hass, cloud, setup_nestor) -> None:
    assert await async_setup_component(hass, "assist_pipeline", {})
    await hass.async_block_till_done()
    await setup_nestor({"make_voice_assistant": True, "assistant_name": "Jarvis"})
    from homeassistant.components.assist_pipeline.pipeline import (async_get_pipeline,
                                                                   async_get_pipelines)
    preferred = async_get_pipeline(hass)
    assert preferred.name == "Jarvis"
    assert preferred.conversation_engine == "conversation.nestor"
    # setting up again doesn't create duplicates
    await hass.config_entries.async_reload(hass.config_entries.async_entries(DOMAIN)[0].entry_id)
    await hass.async_block_till_done()
    assert sum(p.conversation_engine == "conversation.nestor"
               for p in async_get_pipelines(hass)) == 1


async def test_telegram_text_message_gets_a_reply(hass, cloud, setup_nestor) -> None:
    entry = await setup_nestor()
    sent = []

    async def reply(chat_id, text, voice=None):
        sent.append((chat_id, text, voice))
    cloud.telegram_reply = reply
    cloud.say("All lights are off.")
    await entry.runtime_data.telegram.handle({"chat_id": 42, "message_id": 7,
                                              "text": "are the lights off?"})
    assert sent == [(42, "All lights are off.", None)]
    assert cloud.requests[-1]["messages"][0]["content"].endswith("are the lights off?")
