from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import init_db
from .routers import auth, chat, collections, documents
from .schemas import AIInfo


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Sage API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.client_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(collections.router)
app.include_router(documents.router)
app.include_router(chat.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/ai/info", response_model=AIInfo)
def ai_info():
    chat_model = {
        "ollama": settings.ollama_chat_model,
        "openai": settings.openai_chat_model,
        "anthropic": settings.anthropic_chat_model,
    }.get(settings.ai_provider, "unknown")

    embed_model = {
        "ollama": settings.ollama_embed_model,
        "openai": settings.openai_embed_model,
    }.get(settings.embedding_provider, "unknown")

    return AIInfo(
        chat_provider=settings.ai_provider,
        chat_model=chat_model,
        embedding_provider=settings.embedding_provider,
        embedding_model=embed_model,
        embedding_dim=settings.embedding_dim,
    )
