from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from ...config import settings
from .base import ChatMessage


class OllamaEmbeddingProvider:
    name = "ollama"

    def __init__(self) -> None:
        self.model = settings.ollama_embed_model
        self.dim = settings.embedding_dim
        self.base_url = settings.ollama_base_url.rstrip("/")

    async def embed(self, texts: list[str]) -> list[list[float]]:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts},
            )
            resp.raise_for_status()
            data = resp.json()
        return data["embeddings"]


class OllamaChatProvider:
    name = "ollama"

    def __init__(self) -> None:
        self.model = settings.ollama_chat_model
        self.base_url = settings.ollama_base_url.rstrip("/")

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={"model": self.model, "messages": messages, "stream": True},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = obj.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if obj.get("done"):
                        break
