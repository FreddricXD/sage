from __future__ import annotations

from ..config import settings
from .providers.anthropic import AnthropicChatProvider
from .providers.base import ChatProvider, EmbeddingProvider
from .providers.ollama import OllamaChatProvider, OllamaEmbeddingProvider
from .providers.openai import OpenAIChatProvider, OpenAIEmbeddingProvider


def get_embedding_provider() -> EmbeddingProvider:
    provider = settings.embedding_provider.lower()
    if provider == "openai":
        return OpenAIEmbeddingProvider()
    if provider == "ollama":
        return OllamaEmbeddingProvider()
    raise ValueError(f"Unsupported embedding provider: {provider}")


def get_chat_provider() -> ChatProvider:
    provider = settings.ai_provider.lower()
    if provider == "openai":
        return OpenAIChatProvider()
    if provider == "anthropic":
        return AnthropicChatProvider()
    if provider == "ollama":
        return OllamaChatProvider()
    raise ValueError(f"Unsupported chat provider: {provider}")
