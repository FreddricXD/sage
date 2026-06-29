from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://sage:sage@localhost:5434/sage"

    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    client_url: str = "http://localhost:5173"

    ai_provider: str = "ollama"
    embedding_provider: str = "ollama"
    embedding_dim: int = 768

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.1"
    ollama_embed_model: str = "nomic-embed-text"

    openai_api_key: str = ""
    openai_chat_model: str = "gpt-4o-mini"
    openai_embed_model: str = "text-embedding-3-small"

    anthropic_api_key: str = ""
    anthropic_chat_model: str = "claude-3-5-sonnet-latest"

    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 5
    retrieval_mode: str = "hybrid"  # vector | hybrid
    upload_dir: str = "uploads"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
