from __future__ import annotations

from typing import AsyncIterator, Protocol, TypedDict


class ChatMessage(TypedDict):
    role: str  # system | user | assistant
    content: str


class EmbeddingProvider(Protocol):
    name: str
    model: str
    dim: int

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


class ChatProvider(Protocol):
    name: str
    model: str

    def stream(self, messages: list[ChatMessage]) -> AsyncIterator[str]:
        """Yield answer text chunks (tokens) as they are generated."""
        ...
