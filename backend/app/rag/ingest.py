from __future__ import annotations

from sqlalchemy.orm import Session

from ..ai.factory import get_embedding_provider
from ..config import settings
from ..db import SessionLocal
from ..models import Chunk, Document
from ..utils import run_async
from .chunk import chunk_text
from .extract import extract_document


def ingest_document(document_id: str, data: bytes) -> None:
    """Background task: extract -> chunk -> embed -> store.

    Opens its own DB session because it runs after the request that created the
    document has already returned.
    """
    db: Session = SessionLocal()
    try:
        doc = db.get(Document, document_id)
        if doc is None:
            return

        doc.status = "processing"
        db.commit()

        pages = extract_document(doc.filename, doc.mime_type, data)
        chunks = chunk_text(
            pages,
            chunk_size=settings.chunk_size,
            overlap=settings.chunk_overlap,
        )

        if not chunks:
            doc.status = "failed"
            doc.error = "No extractable text found in document."
            db.commit()
            return

        embedder = get_embedding_provider()
        contents = [c.content for c in chunks]

        # Embed in batches to keep request sizes reasonable.
        vectors: list[list[float]] = []
        batch_size = 32
        for i in range(0, len(contents), batch_size):
            batch = contents[i : i + batch_size]
            vectors.extend(run_async(embedder.embed(batch)))

        for c, vec in zip(chunks, vectors):
            db.add(
                Chunk(
                    document_id=doc.id,
                    collection_id=doc.collection_id,
                    content=c.content,
                    embedding=vec,
                    chunk_index=c.chunk_index,
                    page=c.page,
                    token_count=c.token_count,
                )
            )

        doc.chunk_count = len(chunks)
        doc.status = "ready"
        doc.error = ""
        db.commit()
    except Exception as exc:  # noqa: BLE001 - record failure for the UI
        db.rollback()
        doc = db.get(Document, document_id)
        if doc is not None:
            doc.status = "failed"
            doc.error = str(exc)[:1000]
            db.commit()
    finally:
        db.close()
