# Sage - AI Knowledge Assistant (RAG)

Sage is a full-stack Retrieval-Augmented Generation app. Upload documents into a
collection, then chat with an AI that answers **grounded in your documents** and
cites the exact sources it used.

**Stack:** FastAPI - PostgreSQL + pgvector - SQLAlchemy - React + TypeScript + Vite + Tailwind - TanStack Query

The model layer is **pluggable**: it runs free and fully local with
[Ollama](https://ollama.com) by default, or you can switch to OpenAI / Anthropic
with one environment variable.

## Features

- JWT auth (access + refresh tokens)
- Collections (knowledge bases) with document upload (PDF, DOCX, MD, TXT)
- Async ingestion pipeline: extract -> chunk (with overlap) -> embed -> store, with live status
- Semantic retrieval over pgvector (cosine), with optional hybrid (vector + full-text) search
- Streaming chat (Server-Sent Events) with live tokens and inline `[n]` citations
- Pluggable providers: Ollama (local) / OpenAI / Anthropic
- Raw semantic search endpoint for debugging/demo

## Architecture

```
React SPA (Vite)  ->  FastAPI  ->  PostgreSQL + pgvector
   :5173              :8000           :5434
                        |
                        +--> Ollama / OpenAI / Anthropic
```

Ingestion: `upload -> extract text -> chunk -> embed (batch) -> store vectors -> status: ready`

Query: `question -> embed -> vector/hybrid top-k -> build context prompt -> stream answer + citations`

## Prerequisites

- Docker Desktop (runs Postgres, the API, and Ollama)
- Node.js 20+ (for the frontend dev server)

## Quick start

```powershell
# 1. From the repo root, start Postgres + API + Ollama
docker compose up -d --build

# 2. Pull the local models (first time only; this is a large download)
docker compose exec ollama ollama pull nomic-embed-text
docker compose exec ollama ollama pull llama3.1

# 3. (Optional) seed a demo user + sample document
docker compose exec api python seed.py

# 4. Start the frontend
cd frontend
copy .env.example .env
npm install
npm run dev
```

Open http://localhost:5173

- API:        http://localhost:8000
- API docs:   http://localhost:8000/docs (interactive OpenAPI/Swagger)
- Postgres:   localhost:5434  (mapped to avoid clashing with a local 5432)

Demo login after seeding: `demo@sage.dev` / `password123`

## Prefer hosted models (no local download)?

Set these (root `.env` for compose, or `backend/.env` for local runs) and skip the Ollama pulls:

```env
AI_PROVIDER=openai
EMBEDDING_PROVIDER=openai
OPENAI_API_KEY=sk-...
```

Anthropic can serve chat (`AI_PROVIDER=anthropic`) but has no embeddings API, so
keep `EMBEDDING_PROVIDER=ollama` or `openai`.

## API overview

- `POST /api/auth/register|login|refresh`, `GET /api/auth/me`
- `GET|POST /api/collections`, `GET|DELETE /api/collections/{id}`
- `GET|POST /api/collections/{id}/documents`, `DELETE .../documents/{docId}`
- `POST /api/collections/{id}/search` - raw top-k retrieval with scores
- `POST /api/collections/{id}/chat` - SSE streaming answer + citations
- `GET /api/collections/{id}/conversations`, `GET /api/conversations/{id}/messages`
- `GET /api/ai/info` - active providers/models, `GET /api/health`

## Development (without Docker for the backend)

```powershell
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env   # point DATABASE_URL at your Postgres+pgvector
uvicorn app.main:app --reload --port 8000
```

## Tests

```powershell
cd backend
python -m pytest -q
```

Covers chunking (overlap, page tracking, edge cases), prompt assembly, and the
hybrid-search rank-fusion logic.

## How it works

- **Chunking** (`app/rag/chunk.py`): word-aware splitting with character-budget
  overlap so context isn't cut mid-sentence.
- **Embeddings**: provider-agnostic; OpenAI requests `dimensions=768` so vectors
  always match the fixed pgvector column regardless of provider.
- **Vector search** (`app/rag/retrieve.py`): pgvector `cosine_distance` with an
  HNSW index (`vector_cosine_ops`).
- **Hybrid search**: fuses vector ranking with Postgres full-text (`ts_rank`)
  using Reciprocal Rank Fusion.
- **Streaming**: FastAPI `StreamingResponse` emits SSE token events, then a final
  citations event; the React client reads the stream and renders tokens live.

## Deploy

- **Frontend:** Vercel/Netlify (`frontend/`, set `VITE_API_URL`), or the included
  `frontend/Dockerfile` (nginx).
- **API + DB:** any host that runs Docker + managed Postgres with pgvector
  (Fly.io, Render, Railway, Supabase). Use a hosted model in production
  (`AI_PROVIDER=openai`) since Ollama needs significant resources.

## License

MIT
