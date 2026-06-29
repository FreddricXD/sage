from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from ...config import settings
from .base import ChatMessage

ANTHROPIC_BASE = "https://api.anthropic.com/v1"


class AnthropicChatProvider:
    name = "anthropic"

    def __init__(self) -> None:
        self.model = settings.anthropic_chat_model
        self.api_key = settings.anthropic_api_key

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        # Anthropic takes the system prompt as a top-level field, not a message.
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        convo = [m for m in messages if m["role"] != "system"]

        payload = {
            "model": self.model,
            "system": system,
            "messages": convo,
            "max_tokens": 1024,
            "stream": True,
        }
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST", f"{ANTHROPIC_BASE}/messages", headers=headers, json=payload
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    if obj.get("type") == "content_block_delta":
                        token = obj.get("delta", {}).get("text")
                        if token:
                            yield token
                    elif obj.get("type") == "message_stop":
                        break
