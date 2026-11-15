"""Long-term memory: preferences and facts about the household, kept in Home Assistant."""

from __future__ import annotations

import json
import secrets
import time
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .tools_home import ToolError

MAX_FACTS = 200
CONTEXT_FACTS = 40


class Memory:
    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        self._store: Store[dict[str, Any]] = Store(hass, 1, f"nestor.memory.{entry_id}")
        self.facts: list[dict[str, Any]] = []

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        self.facts = data.get("facts", [])

    def _save(self) -> None:
        self._store.async_delay_save(lambda: {"facts": self.facts}, 1)

    def context_text(self, speaker: str | None) -> str:
        """The facts that go into each message: the speaker's own first, then household."""
        if not self.facts:
            return ""
        mine = [f for f in self.facts if speaker and f.get("person") == speaker]
        household = [f for f in self.facts if not f.get("person")]
        others = [f for f in self.facts if f.get("person") and f.get("person") != speaker]
        chosen = (mine + household + others)[-CONTEXT_FACTS:]
        lines = [f"- [{f['id']}] {f['text']}" + (f" ({f['person']})" if f.get("person") else "")
                 for f in chosen]
        return "[What you remember about this household:\n" + "\n".join(lines) + "]"

    async def remember(self, fact: str, person: str | None = None) -> str:
        fact = " ".join(fact.split())[:300]
        if not fact:
            raise ToolError("Nothing to remember.")
        for f in self.facts:  # don't store the same thing twice
            if f["text"].lower() == fact.lower() and f.get("person") == person:
                return json.dumps({"ok": True, "id": f["id"], "note": "Already remembered."})
        item = {"id": secrets.token_hex(3), "text": fact, "person": person or None,
                "created": int(time.time())}
        self.facts.append(item)
        del self.facts[:-MAX_FACTS]
        self._save()
        return json.dumps({"ok": True, "id": item["id"]})

    async def forget(self, fact_id: str) -> str:
        before = len(self.facts)
        self.facts = [f for f in self.facts if f["id"] != fact_id]
        if len(self.facts) == before:
            raise ToolError(f"No memory with id {fact_id}.")
        self._save()
        return json.dumps({"ok": True})

    async def list_memories(self) -> str:
        return json.dumps({"memories": self.facts}, ensure_ascii=False)
