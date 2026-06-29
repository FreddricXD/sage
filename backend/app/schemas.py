from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


# ---- Auth ----
class RegisterRequest(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=6, max_length=200)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str


class AuthResponse(BaseModel):
    user: UserOut
    access_token: str
    refresh_token: str


# ---- Collections ----
class CollectionCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""


class CollectionOut(BaseModel):
    id: str
    name: str
    description: str
    document_count: int
    created_at: datetime


# ---- Documents ----
class DocumentOut(BaseModel):
    id: str
    filename: str
    mime_type: str
    size_bytes: int
    status: str
    error: str
    chunk_count: int
    created_at: datetime


# ---- Search / Chat ----
class SearchRequest(BaseModel):
    query: str
    top_k: int | None = None


class Citation(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    snippet: str
    score: float
    index: int


class SearchResult(BaseModel):
    results: list[Citation]


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ConversationOut(BaseModel):
    id: str
    title: str
    created_at: datetime


class MessageOut(BaseModel):
    id: str
    role: str
    content: str
    citations: list[dict]
    created_at: datetime


class AIInfo(BaseModel):
    chat_provider: str
    chat_model: str
    embedding_provider: str
    embedding_model: str
    embedding_dim: int
