"""Seed a demo user, collection, and a sample document.

Run inside the API container (so it can reach the DB and the model backend):

    docker compose exec api python seed.py

Requires the embedding model to be available (Ollama pulled, or a hosted key set).
"""

from app.db import SessionLocal, init_db
from app.models import Collection, Document, User
from app.rag.ingest import ingest_document
from app.security import hash_password

SAMPLE_TEXT = b"""Sage Project Overview

Sage is a retrieval-augmented generation (RAG) knowledge assistant. Users upload
documents into collections. Each document is split into overlapping chunks, and
every chunk is embedded into a vector and stored in PostgreSQL using the pgvector
extension.

When a user asks a question, Sage embeds the question, finds the most similar
chunks using cosine distance, and passes those chunks to a language model as
grounding context. The model answers using only the retrieved context and cites
its sources with bracketed numbers.

The model layer is pluggable: by default it uses local Ollama models, but it can
be switched to OpenAI or Anthropic with an environment variable.
"""


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@sage.dev").first()
        if not user:
            user = User(
                email="demo@sage.dev",
                name="Demo User",
                password_hash=hash_password("password123"),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        collection = (
            db.query(Collection).filter(Collection.user_id == user.id).first()
        )
        if not collection:
            collection = Collection(
                user_id=user.id,
                name="Getting Started",
                description="Sample collection with one document about Sage.",
            )
            db.add(collection)
            db.commit()
            db.refresh(collection)

        has_docs = (
            db.query(Document).filter(Document.collection_id == collection.id).count()
        )
        if not has_docs:
            doc = Document(
                collection_id=collection.id,
                filename="sage-overview.txt",
                mime_type="text/plain",
                size_bytes=len(SAMPLE_TEXT),
                status="pending",
            )
            db.add(doc)
            db.commit()
            db.refresh(doc)
            print("Ingesting sample document (embedding)...")
            ingest_document(doc.id, SAMPLE_TEXT)

        print("Seed complete!")
        print("Login: demo@sage.dev / password123")
    finally:
        db.close()


if __name__ == "__main__":
    main()
