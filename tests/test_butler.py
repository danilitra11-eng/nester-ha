"""Proactive butler, memory, profiles, automations, cameras, vacation and reports."""

from __future__ import annotations

import io
import json
import time
from datetime import timedelta
from unittest.mock import patch

from homeassistant.core import Context, State
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import async_mock_service


# ---- profiles and guests ------------------------------------------------

async def test_guest_and_restricted_family_member(hass, cloud, setup_nestor) -> None:
    hass.states.async_set("light.kitchen", "off")
    hass.states.async_set("climate.living", "off")
    hass.states.async_set("lock.front", "locked")
    lights = async_mock_service(hass, "light", "turn_on")
    climate = async_mock_service(hass, "climate", "turn_on")
    entry = await setup_nestor({"permissions": ["lights", "climate", "security", "structure"],
                                "profiles": {"Kids": {"blocked": ["climate"]}}})
    agent = entry.runtime_data.agent

    # a guest can switch lights, can't unlock, can't change settings, gets no extra tools
    cloud.use(("call_service", {"domain": "light", "service": "turn_on",
                                "entity_ids": ["light.kitchen"], "data": {}}),
              ("call_service", {"domain": "lock", "service": "unlock",
                                "entity_ids": ["lock.front"], "data": {}}),
              ("update_settings", {"personality": "brief"}))
    cloud.say("Light on.")
    await agent.ask("g1", "light on, open the door, be brief", speaker="Dog sitter", guest=True)
    res = cloud.last_tool_results()
    assert [r["is_error"] for r in res] == [False, True, True]
    assert len(lights) == 1
    assert cloud.requests[0]["capabilities"] == []
    assert "GUEST" in cloud.requests[0]["messages"][-1]["content"]

    # the Kids profile can't touch climate
    cloud.use(("call_service", {"domain": "climate", "service": "turn_on",
                                "entity_ids": ["climate.living"], "data": {}}))
    cloud.say("Sorry.")
    await agent.ask("k1", "turn on the AC", speaker="Kids")
    assert cloud.last_tool_results()[0]["is_error"] is True and len(climate) == 0


# ---- memory --------------------------------------------------------------

async def test_memory_is_remembered_and_used(hass, cloud, setup_nestor) -> None:
    entry = await setup_nestor()
    agent = entry.runtime_data.agent
    cloud.use(("remember", {"fact": "Likes the bedroom at 70°F at night", "person": "Dad"}))
    cloud.say("Noted.")
    await agent.ask("m1", "I like the bedroom at 70 at night", speaker="Dad")
    cloud.say("Setting it to 70 as you like.")
    await agent.ask("m2", "make the bedroom comfy", speaker="Dad")
    context = cloud.requests[-1]["messages"][-1]["content"]
    assert "Likes the bedroom at 70°F at night (Dad)" in context
    assert "memory" in cloud.requests[-1]["capabilities"]


# ---- automations ---------------------------------------------------------

async def test_create_automation_and_permission_check(hass, cloud, setup_nestor, tmp_path) -> None:
    hass.config.config_dir = str(tmp_path)
    (tmp_path / "automations.yaml").write_text("[]\n")
    reload = async_mock_service(hass, "automation", "reload")
    entry = await setup_nestor({"permissions": ["lights", "automations"]})
    agent = entry.runtime_data.agent
    auto = {"alias": "Porch light at sunset", "description": "Every evening",
            "triggers": [{"trigger": "sun", "event": "sunset"}],
            "actions": [{"action": "light.turn_on", "target": {"entity_id": "light.porch"}}]}
    bad = {"alias": "Unlock", "triggers": [{"trigger": "time", "at": "07:00:00"}],
           "actions": [{"action": "lock.unlock", "target": {"entity_id": "lock.front"}}]}
    cloud.use(("create_automation", auto), ("create_automation", bad))
    cloud.say("Done.")
    await agent.ask("a1", "porch light on at sunset, and unlock the door at 7")
    res = cloud.last_tool_results()
    assert res[0]["is_error"] is False
    assert res[1]["is_error"] is True and "lock" in res[1]["content"]
    from homeassistant.util.yaml import load_yaml
    saved = load_yaml(str(tmp_path / "automations.yaml"))
    assert len(saved) == 1 and saved[0]["alias"] == "Porch light at sunset"
    assert saved[0]["id"].startswith("nestor_") and "created by Nestor" in saved[0]["description"]
    assert len(reload) == 1


# ---- proactive butler ----------------------------------------------------

async def test_garage_left_open_alert_and_button(hass, cloud, setup_nestor, freezer) -> None:
    hass.states.async_set("person.dana", "not_home")
    hass.states.async_set("cover.garage", "open", {"device_class": "garage",
                                                   "friendly_name": "Garage door"})
    close = async_mock_service(hass, "cover", "close_cover")
    entry = await setup_nestor({"permissions": ["covers"]})
    rt = entry.runtime_data
    freezer.tick(timedelta(minutes=10))
    await rt.watchers._tick()
    assert cloud.notified == []  # not long enough yet
    freezer.tick(timedelta(minutes=31))
    await rt.watchers._tick()
    text, buttons = cloud.notified[-1]
    assert "Garage door" in text and "nobody's home" in text
    assert buttons[0]["text"] == "Close it"
    # the same alert isn't repeated every minute
    await rt.watchers._tick()
    assert len(cloud.notified) == 1
    # pressing the button (via Telegram) closes it
    sent = []

    async def reply(chat_id, text, voice=None):
        sent.append(text)
    cloud.telegram_reply = reply
    await rt.telegram.handle({"chat_id": 1, "callback": buttons[0]["data"]})
    assert sent and len(close) == 1, sent
    assert close[0].data["entity_id"] == ["cover.garage"]
    assert sent[-1].startswith("Done")
    assert rt.stats.summary()["actions"] == 1


async def test_leak_is_urgent_even_in_quiet_hours(hass, cloud, setup_nestor) -> None:
    entry = await setup_nestor({"quiet_hours": {"start": "00:00", "end": "23:59"}})
    hass.states.async_set("binary_sensor.kitchen_leak", "off", {"device_class": "moisture",
                                                                "friendly_name": "Kitchen leak"})
    await hass.async_block_till_done()
    hass.states.async_set("binary_sensor.kitchen_leak", "on", {"device_class": "moisture",
                                                               "friendly_name": "Kitchen leak"})
    await hass.async_block_till_done()
    assert "Kitchen leak detected water" in cloud.notified[-1][0]
    assert entry.runtime_data.notifier.sent_log[-1]["urgent"] is True


async def test_non_urgent_waits_for_quiet_hours_to_end(hass, cloud, setup_nestor) -> None:
    entry = await setup_nestor({"quiet_hours": {"start": "00:00", "end": "23:59"}})
    notifier = entry.runtime_data.notifier
    await notifier.send("Weekly tip")
    assert cloud.notified == []
    await notifier.flush_held()
    assert cloud.notified[-1][0] == "Weekly tip"


async def test_everyone_left_lights_on(hass, cloud, setup_nestor) -> None:
    hass.states.async_set("person.dana", "home")
    hass.states.async_set("light.hall", "on", {"friendly_name": "Hall"})
    entry = await setup_nestor()
    w = entry.runtime_data.watchers
    await w._tick()
    hass.states.async_set("person.dana", "not_home")
    await w._tick()
    text, buttons = cloud.notified[-1]
    assert "1 lights are on: Hall" in text and buttons[0]["text"] == "Turn them off"


async def test_window_open_with_ac(hass, cloud, setup_nestor, freezer) -> None:
    area = ar.async_get(hass).async_create("Living room")
    reg = er.async_get(hass)
    ac = reg.async_get_or_create("climate", "demo", "ac1", suggested_object_id="living_ac")
    win = reg.async_get_or_create("binary_sensor", "demo", "w1", suggested_object_id="living_window")
    reg.async_update_entity(ac.entity_id, area_id=area.id)
    reg.async_update_entity(win.entity_id, area_id=area.id)
    hass.states.async_set(ac.entity_id, "cool", {"hvac_action": "cooling", "friendly_name": "AC"})
    hass.states.async_set(win.entity_id, "on", {"device_class": "window", "friendly_name": "Window"})
    entry = await setup_nestor()
    freezer.tick(timedelta(minutes=11))
    await entry.runtime_data.watchers._tick()
    assert "Window is open while AC is running" in cloud.notified[-1][0]


async def test_home_doctor(hass, cloud, setup_nestor) -> None:
    hass.states.async_set("sensor.door_battery", "9", {"device_class": "battery",
                                                       "friendly_name": "Door sensor battery"})
    entry = await setup_nestor()
    health = await entry.runtime_data.watchers.health_check(notify=True)
    assert health["low_battery"][0]["level"] == "9"
    assert "Door sensor battery (9%)" in cloud.notified[-1][0]


async def test_trial_report_sent_once(hass, cloud, setup_nestor) -> None:
    entry = await setup_nestor()
    rt = entry.runtime_data
    rt.stats.data["installed"] = time.time() - 6 * 86400
    rt.stats.inc("commands", 12)
    rt.stats.add_saving(10)
    await rt.watchers._reports(dt_util.now())
    await rt.watchers._reports(dt_util.now())
    reports = [t for t, _ in cloud.notified if "first days" in t]
    assert len(reports) == 1 and "12 requests" in reports[0] and "10.0 kWh" in reports[0]


async def test_automation_suggestion_from_history(hass, cloud, setup_nestor) -> None:
    hass.states.async_set("light.porch", "off", {"friendly_name": "Porch light"})
    entry = await setup_nestor()
    base = dt_util.now().replace(hour=23, minute=30, second=0, microsecond=0)
    fake = {"light.porch": [State("light.porch", "off",
                                  last_changed=dt_util.as_utc(base - timedelta(days=d)))
                            for d in range(1, 8)]}
    with patch("homeassistant.components.recorder.get_instance") as inst, \
            patch("homeassistant.components.recorder.history.get_significant_states",
                  return_value=fake):
        async def run(job, *a):
            return job(*a)
        inst.return_value.async_add_executor_job = run
        found = await entry.runtime_data.watchers.suggest_automations()
    assert found[0]["entity_id"] == "light.porch" and found[0]["time"] == "23:30"
    text, buttons = cloud.notified[-1]
    assert "Porch light gets turned off around 23:30" in text
    assert buttons[0]["text"] == "Yes, automate it"


# ---- Pro: vacation and cameras -------------------------------------------

async def test_vacation_mode_by_chat(hass, cloud, setup_nestor) -> None:
    entry = await setup_nestor()
    cloud.use(("set_vacation_mode", {"enabled": True}))
    cloud.say("Vacation mode is on.")
    await entry.runtime_data.agent.ask("v1", "we're going away for a week")
    assert entry.options["vacation_mode"] is True


def _jpeg() -> bytes:
    from PIL import Image
    out = io.BytesIO()
    Image.new("RGB", (2000, 1500), "blue").save(out, format="JPEG")
    return out.getvalue()


async def test_camera_look_and_doorbell(hass, cloud, setup_nestor) -> None:
    from homeassistant.components.camera import Image
    hass.states.async_set("camera.front_door", "idle", {"friendly_name": "Front door"})
    hass.states.async_set("event.doorbell", "unknown", {"device_class": "doorbell"})
    entry = await setup_nestor({"permissions": ["lights", "cameras"]})
    with patch("homeassistant.components.camera.async_get_image",
               return_value=Image("image/jpeg", _jpeg())):
        cloud.use(("look_at_camera", {"entity_id": "camera.front_door",
                                      "question": "is there a package?"}))
        cloud.say("Yes, a box by the door.")
        out = await entry.runtime_data.agent.ask("c1", "is there a package at the door?")
        assert out["reply"] == "Yes, a box by the door."
        assert isinstance(cloud.last_tool_results()[0]["content"], list), cloud.last_tool_results()[0]
        img = cloud.last_tool_results()[0]["content"][1]
        assert img["type"] == "image" and img["source"]["media_type"] == "image/jpeg"
        # next time the conversation starts fresh rather than resending the picture
        assert entry.runtime_data.agent._convs["c1"].messages == []

        hass.states.async_set("event.doorbell", "2026-01-01T10:00:00", {"device_class": "doorbell"})
        await hass.async_block_till_done()
    assert "delivery driver" in cloud.notified[-1][0]


async def test_panel_commands_for_new_features(hass, cloud, setup_nestor, hass_ws_client) -> None:
    entry = await setup_nestor()
    rt = entry.runtime_data
    await rt.memory.remember("The dog is called Bruno")
    client = await hass_ws_client(hass)

    await client.send_json({"id": 1, "type": "nestor/memory"})
    facts = (await client.receive_json())["result"]["facts"]
    assert facts[0]["text"] == "The dog is called Bruno"
    rt.memory.facts.clear()

    await client.send_json({"id": 4, "type": "nestor/settings/update", "changes": {
        "profiles": {"Kids": {"blocked": ["climate", "nonsense"]}, " ": {}},
        "alerts": ["safety", "made_up"], "vacation_mode": True}})
    opts = (await client.receive_json())["result"]["options"]
    assert opts["profiles"] == {"Kids": {"blocked": ["climate"], "allowed": []}}
    assert opts["alerts"] == ["safety"] and opts["vacation_mode"] is True

    await client.send_json({"id": 5, "type": "nestor/report"})
    rep = (await client.receive_json())["result"]
    assert "commands" in rep["month"]

    await client.send_json({"id": 6, "type": "nestor/health"})
    assert "low_battery" in (await client.receive_json())["result"]

    async def pair(role="member", profile=None, guest_hours=None):
        pair.args = (role, profile, guest_hours)
        return {"code": "123456", "bot_username": "NestorHomeBot"}
    cloud.telegram_pair = pair
    await client.send_json({"id": 7, "type": "nestor/telegram/pair", "role": "guest",
                            "profile": "Dog sitter", "guest_hours": 48})
    assert (await client.receive_json())["result"]["code"] == "123456"
    assert pair.args == ("guest", "Dog sitter", 48)
