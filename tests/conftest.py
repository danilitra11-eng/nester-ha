"""Shared fixtures: load the integration from custom_components/ with a scripted cloud."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.nestor.const import (CONF_CLOUD_URL, CONF_INSTANCE_ID, CONF_LICENSE_KEY,
                                            DEFAULT_OPTIONS, DOMAIN)


@pytest.fixture(autouse=True)
async def auto_enable_custom_integrations(hass, enable_custom_integrations):
    from homeassistant.setup import async_setup_component
    assert await async_setup_component(hass, "homeassistant", {})
    yield


class ScriptedCloud:
    """Stands in for the cloud: each step() returns the next scripted reply.

    A script item is either a dict (returned as-is) or a callable(messages) -> dict.
    """

    def __init__(self) -> None:
        self.script: list[dict | Callable[[list], dict]] = []
        self.requests: list[dict[str, Any]] = []
        self.notified = []

    def say(self, text: str) -> None:
        self.script.append({"content": [{"type": "text", "text": text}], "stop_reason": "end_turn",
                            "quota_remaining": 99})

    def use(self, *calls: tuple[str, dict]) -> None:
        self.script.append({"content": [{"type": "tool_use", "id": f"t{len(self.script)}_{i}",
                                         "name": n, "input": a} for i, (n, a) in enumerate(calls)],
                            "stop_reason": "tool_use"})

    async def step(self, messages, **kw):
        self.requests.append({"messages": [dict(m) for m in messages], **kw})
        item = self.script.pop(0)
        return item(messages) if callable(item) else item

    features = ["control", "structure", "design", "telegram", "alerts_basic", "report", "alerts",
                "doctor", "memory", "profiles", "automations", "suggestions", "vision", "guests",
                "vacation"]
    notified: list = []

    async def verify(self, key=None):
        return {"valid": True, "plan": "pro", "quota_remaining": 100, "features": self.features}

    async def telegram_notify(self, text, buttons=None):
        self.notified.append((text, buttons))
        return 1

    async def vision(self, jpeg, question, language):
        return {"text": "a delivery driver holding a box"}

    async def telegram_status(self):
        return {"linked": False, "bot_username": "NestorHomeBot"}

    async def telegram_poll(self, wait=25):
        import asyncio
        await asyncio.sleep(3600)
        return []

    def last_tool_results(self) -> list[dict]:
        return self.requests[-1]["messages"][-1]["content"]


@pytest.fixture
def cloud():
    return ScriptedCloud()


@pytest.fixture
async def setup_nestor(hass, cloud):
    async def _setup(options: dict | None = None):
        entry = MockConfigEntry(
            domain=DOMAIN, title="Nestor", unique_id=DOMAIN,
            data={CONF_LICENSE_KEY: "KEY", CONF_CLOUD_URL: "http://cloud", CONF_INSTANCE_ID: "i" * 16},
            options={**DEFAULT_OPTIONS, **(options or {})})
        entry.add_to_hass(hass)
        with patch("custom_components.nestor.CloudClient", return_value=cloud):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        return entry
    return _setup
