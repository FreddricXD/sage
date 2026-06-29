from __future__ import annotations

import json
from typing import AsyncIterator

import httpx

from ...config import settings
from .base import ChatMessage

OPENAI_BASE = "https://api.openai.com/v1"


class OpenAIEmbeddingProvider:
    name = "openai"

    def __init__(self) -> None:
        self.model = settings.openai_embed_model
        self.dim = settings.embedding_dim
        self.api_key = settings.openai_api_key

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # text-embedding-3-* supports a `dimensions` param so the output matches
        # the fixed pgvector column width regardless of provider.
        payload = {"model": self.model, "input": texts, "dimensions": self.dim}
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{OPENAI_BASE}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            resp.raise_for_status()
            data = resp.json()
        return [item["embedding"] for item in data["data"]]


class OpenAIChatProvider:
    name = "openai"

    def __init__(self) -> None:
        self.model = settings.openai_chat_model
        self.api_key = settings.openai_api_key

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        payload = {"model": self.model, "messages": messages, "stream": True}
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{OPENAI_BASE}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[len("data:") :].strip()
                    if data == "[DONE]":
                        break
                    try:
                        obj = json.loads(data)
                    except json.JSONDecodeError:
                        continue
                    delta = obj["choices"][0].get("delta", {})
                    token = delta.get("content")
                    if token:
                        yield token
