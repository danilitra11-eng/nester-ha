"""Client for the Nestor cloud service (license, assistant steps, Telegram relay)."""

from __future__ import annotations

import asyncio
from typing import Any

import aiohttp

from .const import VERSION


class CloudError(Exception):
    """A cloud call failed. `code` is a stable, user-facing error code."""

    def __init__(self, code: str, detail: dict[str, Any] | None = None) -> None:
        super().__init__(code)
        self.code = code
        self.detail = detail or {}


class CloudClient:
    def __init__(self, session: aiohttp.ClientSession, base_url: str, license_key: str,
                 instance_id: str) -> None:
        self._session = session
        self._base = base_url.rstrip("/")
        self._key = license_key.strip()
        self._instance = instance_id

    async def _post(self, path: str, body: dict[str, Any], *, timeout: float = 120,
                    key: str | None = None) -> dict[str, Any]:
        key = (key if key is not None else self._key).strip()
        if not key:
            raise CloudError("missing_key")
        payload = {"license_key": key, "instance_id": self._instance, **body}
        try:
            async with self._session.post(f"{self._base}{path}", json=payload,
                                          timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                data = await resp.json(content_type=None)
                status = resp.status
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as exc:
            raise CloudError("offline") from exc
        if status >= 400:
            detail = data.get("detail") if isinstance(data, dict) else None
            code = detail.get("code", "generic") if isinstance(detail, dict) else "generic"
            raise CloudError(code, detail if isinstance(detail, dict) else None)
        return data

    async def verify(self, key: str | None = None) -> dict[str, Any]:
        return await self._post("/v1/license/verify", {}, timeout=20, key=key)

    async def step(self, messages: list[dict[str, Any]], *, name: str, language: str,
                   personality: str, capabilities: list[str]) -> dict[str, Any]:
        return await self._post("/v1/chat", {
            "messages": messages, "assistant_name": name, "language": language,
            "personality": personality, "capabilities": capabilities,
            "addon_version": VERSION,
        })

    async def vision(self, jpeg: bytes, question: str, language: str) -> dict[str, Any]:
        import base64
        return await self._post("/v1/vision", {"image_b64": base64.b64encode(jpeg).decode(),
                                                "question": question, "language": language},
                                timeout=60)

    # ---- Telegram relay ------------------------------------------------

    async def telegram_pair(self, role: str = "member", profile: str | None = None,
                            guest_hours: int | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {"role": role}
        if profile:
            body["profile"] = profile
        if guest_hours:
            body["guest_hours"] = guest_hours
        return await self._post("/v1/telegram/pair", body, timeout=20)

    async def telegram_notify(self, text: str, buttons: list[dict[str, str]] | None = None) -> int:
        data = await self._post("/v1/telegram/notify", {"text": text, "buttons": buttons or []},
                                timeout=30)
        return int(data.get("sent", 0))

    async def telegram_unlink_chat(self, chat_id: int) -> None:
        await self._post("/v1/telegram/unlink_chat", {"chat_id": chat_id}, timeout=20)

    async def telegram_unpair(self) -> dict[str, Any]:
        return await self._post("/v1/telegram/unpair", {}, timeout=20)

    async def telegram_status(self) -> dict[str, Any]:
        return await self._post("/v1/telegram/status", {}, timeout=20)

    async def telegram_poll(self, wait: int = 25) -> list[dict[str, Any]]:
        data = await self._post("/v1/telegram/poll", {"wait": wait}, timeout=wait + 15)
        return data.get("messages", [])

    async def telegram_file(self, chat_id: int, message_id: int) -> bytes:
        import base64
        data = await self._post("/v1/telegram/file", {"chat_id": chat_id, "message_id": message_id},
                                timeout=60)
        return base64.b64decode(data["data"])

    async def telegram_reply(self, chat_id: int, text: str, voice_ogg: bytes | None = None) -> None:
        import base64
        body: dict[str, Any] = {"chat_id": chat_id, "text": text}
        if voice_ogg:
            body["voice_b64"] = base64.b64encode(voice_ogg).decode()
        await self._post("/v1/telegram/reply", body, timeout=60)
