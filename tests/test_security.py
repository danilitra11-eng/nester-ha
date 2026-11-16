"""Security guards: risky actions need confirmation, automations can't sneak past permissions."""

from __future__ import annotations

import json

import pytest
from pytest_homeassistant_custom_component.common import async_mock_service

from custom_components.nestor.automations import _called_services
from custom_components.nestor.config_flow import url_is_safe
from custom_components.nestor.tools_home import ToolError


def grab_token_then_confirm(store):
    def step(messages):
        token = json.loads(messages[-1]["content"][0]["content"])["token"]
        store["token"] = token
        return {"content": [{"type": "text", "text": "Unlock the front door?"}],
                "stop_reason": "end_turn"}
    return step


async def test_unlock_needs_confirmation_in_a_later_message(hass, cloud, setup_nestor) -> None:
    hass.states.async_set("lock.front_door", "locked", {"friendly_name": "Front Door"})
    calls = async_mock_service(hass, "lock", "unlock")
    entry = await setup_nestor({"permissions": ["lights", "security"]})
    agent = entry.runtime_data.agent

    held = {}
    cloud.use(("call_service", {"domain": "lock", "service": "unlock",
                                "entity_ids": ["lock.front_door"]}))
    cloud.script.append(grab_token_then_confirm(held))
    await agent.ask("c1", "unlock the front door")
    assert calls == []  # nothing happened yet

    # the model can't confirm on its own in the same turn
    cloud.use(("call_service", {"domain": "lock", "service": "unlock",
                                "entity_ids": ["lock.front_door"]}))
    cloud.use(("confirm_action", {"token": "nope"}))
    cloud.say("I need you to confirm.")
    await agent.ask("c2", "unlock the front door")
    assert calls == []

    # the user's next message confirms
    cloud.use(("confirm_action", {"token": held["token"]}))
    cloud.say("Unlocked.")
    await agent.ask("c1", "yes")
    assert len(calls) == 1 and calls[0].data["entity_id"] == ["lock.front_door"]


async def test_unlock_without_permission_is_refused_not_queued(hass, cloud, setup_nestor) -> None:
    hass.states.async_set("lock.front_door", "locked")
    entry = await setup_nestor()  # default permissions: no "security"
    cloud.use(("call_service", {"domain": "lock", "service": "unlock",
                                "entity_ids": ["lock.front_door"]}))
    cloud.say("Not allowed.")
    await entry.runtime_data.agent.ask("c1", "unlock")
    res = cloud.last_tool_results()[0]
    assert res["is_error"] is True and "not allowed" in res["content"]


async def test_garage_door_needs_confirmation_but_blinds_dont(hass, cloud, setup_nestor) -> None:
    hass.states.async_set("cover.garage", "closed", {"device_class": "garage"})
    hass.states.async_set("cover.blinds", "closed", {"device_class": "blind"})
    calls = async_mock_service(hass, "cover", "open_cover")
    entry = await setup_nestor({"permissions": ["covers"]})
    cloud.use(("call_service", {"domain": "cover", "service": "open_cover",
                                "entity_ids": ["cover.blinds"]}))
    cloud.use(("call_service", {"domain": "cover", "service": "open_cover",
                                "entity_ids": ["cover.garage"]}))
    cloud.say("Blinds open; confirm the garage?")
    await entry.runtime_data.agent.ask("c1", "open the blinds and the garage")
    assert [c.data["entity_id"] for c in calls] == [["cover.blinds"]]
    assert json.loads(cloud.last_tool_results()[0]["content"])["needs_confirmation"] is True


@pytest.mark.parametrize("actions", [
    [{"variables": {"svc": "shell_command.wipe"}}, {"action": "{{ svc }}"}],
    [{"action": "{{ 'shell_command.wipe' }}"}],
    [{"service_template": "shell_command.wipe"}],
    [{"if": [], "then": [{"action": ["light.turn_on"]}]}],
])
def test_templated_actions_are_rejected(actions) -> None:
    with pytest.raises(ToolError):
        _called_services(actions)


def test_device_and_scene_actions_are_seen() -> None:
    found = _called_services([{"device_id": "d1", "domain": "lock", "type": "unlock"},
                              {"scene": "scene.movie"},
                              {"if": [{"condition": "device", "device_id": "d2",
                                       "domain": "light", "type": "is_on"}],
                               "then": [{"action": "light.turn_on"}]}])
    assert found == {"lock.unlock", "scene.turn_on", "light.turn_on"}


async def test_automation_cannot_unlock_or_open_garage(hass, cloud, setup_nestor) -> None:
    hass.states.async_set("cover.garage", "closed", {"device_class": "garage"})
    entry = await setup_nestor({"permissions": ["security", "covers", "automations"]})
    autos = entry.runtime_data.automations
    for actions in ([{"action": "lock.unlock", "target": {"entity_id": "lock.front_door"}}],
                    [{"action": "cover.open_cover", "target": {"entity_id": "cover.garage"}}],
                    [{"device_id": "d1", "domain": "lock", "type": "unlock"}]):
        with pytest.raises(ToolError, match="safety"):
            autos._check_actions(actions)
    # ordinary actions still pass
    autos._check_actions([{"action": "lock.lock", "target": {"entity_id": "lock.front_door"}}])


@pytest.mark.parametrize("url,ok", [
    ("https://api.example.com", True),
    ("http://api.example.com", False),
    ("http://8.8.8.8:8000", False),
    ("http://192.168.1.20:8000", True),
    ("http://nestor.local:8000", True),
    ("ftp://192.168.1.20", False),
    ("javascript:alert(1)", False),
])
def test_cloud_url_must_be_https_unless_local(url, ok) -> None:
    assert url_is_safe(url) is ok


async def test_setup_rejects_insecure_service_address(hass) -> None:
    from homeassistant import config_entries
    from custom_components.nestor.const import DOMAIN
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"license_key": "KEY", "cloud_url": "http://evil.example.com"})
    assert result["errors"] == {"base": "insecure_url"}
