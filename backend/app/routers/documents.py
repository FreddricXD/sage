from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Document, User
from ..rag.ingest import ingest_document
from ..schemas import DocumentOut
from .collections import get_owned_collection

router = APIRouter(prefix="/api/collections", tags=["documents"])

MAX_BYTES = 20 * 1024 * 1024  # 20 MB
ALLOWED_EXT = (".pdf", ".docx", ".md", ".markdown", ".txt")


def _to_out(d: Document) -> DocumentOut:
    return DocumentOut(
        id=d.id,
        filename=d.filename,
        mime_type=d.mime_type,
        size_bytes=d.size_bytes,
        status=d.status,
        error=d.error,
        chunk_count=d.chunk_count,
        created_at=d.created_at,
    )


@router.get("/{collection_id}/documents", response_model=list[DocumentOut])
def list_documents(
    collection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_owned_collection(collection_id, db, user)
    rows = db.scalars(
        select(Document)
        .where(Document.collection_id == collection_id)
        .order_by(Document.created_at.desc())
    ).all()
    return [_to_out(d) for d in rows]


@router.post("/{collection_id}/documents", response_model=DocumentOut, status_code=201)
async def upload_document(
    collection_id: str,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_owned_collection(collection_id, db, user)

    filename = file.filename or "untitled"
    if not filename.lower().endswith(ALLOWED_EXT):
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed: {', '.join(ALLOWED_EXT)}",
        )

    data = await file.read()
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 20 MB)")

    doc = Document(
        collection_id=collection_id,
        filename=filename,
        mime_type=file.content_type or "",
        size_bytes=len(data),
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # Process (extract -> chunk -> embed) in the background so upload returns fast.
    background.add_task(ingest_document, doc.id, data)

    return _to_out(doc)


@router.delete("/{collection_id}/documents/{document_id}", status_code=204)
def delete_document(
    collection_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_owned_collection(collection_id, db, user)
    doc = db.get(Document, document_id)
    if doc is None or doc.collection_id != collection_id:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(doc)
    db.commit()
