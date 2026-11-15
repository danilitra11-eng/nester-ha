"""Cameras (Pro): Nestor looks through a camera and describes what it sees."""

from __future__ import annotations

import base64
import io
import json
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import HomeAssistant

from .cloud import CloudError
from .tools_home import ToolError

if TYPE_CHECKING:
    from . import NestorRuntime

_LOGGER = logging.getLogger(__name__)
MAX_SIDE = 1024  # keeps each image to roughly a thousand tokens


def shrink_jpeg(data: bytes) -> bytes:
    from PIL import Image
    img = Image.open(io.BytesIO(data))
    img = img.convert("RGB")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=80)
    return out.getvalue()


class Cameras:
    def __init__(self, runtime: "NestorRuntime") -> None:
        self.rt = runtime
        self.hass: HomeAssistant = runtime.hass

    async def snapshot(self, entity_id: str) -> bytes:
        from homeassistant.components.camera import async_get_image
        if not entity_id.startswith("camera.") or self.hass.states.get(entity_id) is None:
            raise ToolError(f"No camera {entity_id}. Use find_entities with domain camera.")
        try:
            image = await async_get_image(self.hass, entity_id, timeout=10)
        except Exception as err:
            raise ToolError(f"Couldn't get a picture from {entity_id}: {err}") from err
        return await self.hass.async_add_executor_job(shrink_jpeg, image.content)

    async def look(self, entity_id: str, question: str | None = None) -> list[dict[str, Any]]:
        """Tool result with the picture, for the model to look at in the conversation."""
        jpeg = await self.snapshot(entity_id)
        st = self.hass.states.get(entity_id)
        text = f"Snapshot from {st.name if st else entity_id} just now."
        if question:
            text += f" The user wants to know: {question}"
        return [{"type": "text", "text": text},
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                             "data": base64.b64encode(jpeg).decode()}}]

    async def describe(self, entity_id: str, question: str) -> str | None:
        """One-off description (doorbell alerts). None if anything fails."""
        try:
            jpeg = await self.snapshot(entity_id)
            data = await self.rt.cloud.vision(jpeg, question, self.rt.options.get("language", "auto"))
            return data.get("text") or None
        except (ToolError, CloudError) as err:
            _LOGGER.info("Camera description unavailable: %s", err)
            return None

    async def list_cameras(self) -> str:
        cams = [{"entity_id": s.entity_id, "name": s.name, "state": s.state}
                for s in self.hass.states.async_all("camera")]
        return json.dumps({"cameras": cams}, ensure_ascii=False)
