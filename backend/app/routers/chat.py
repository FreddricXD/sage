import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..ai.factory import get_chat_provider
from ..db import SessionLocal, get_db
from ..deps import get_current_user
from ..models import Conversation, Message, User
from ..rag.retrieve import SYSTEM_PROMPT, build_context_prompt, retrieve
from ..schemas import (
    ChatRequest,
    Citation,
    ConversationOut,
    MessageOut,
    SearchRequest,
    SearchResult,
)
from .collections import get_owned_collection

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/collections/{collection_id}/search", response_model=SearchResult)
async def search(
    collection_id: str,
    body: SearchRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_owned_collection(collection_id, db, user)
    chunks = await retrieve(db, collection_id, body.query, body.top_k)
    return SearchResult(
        results=[
            Citation(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                filename=c.filename,
                snippet=c.content[:300],
                score=c.score,
                index=i + 1,
            )
            for i, c in enumerate(chunks)
        ]
    )


@router.get("/collections/{collection_id}/conversations", response_model=list[ConversationOut])
def list_conversations(
    collection_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_owned_collection(collection_id, db, user)
    rows = db.scalars(
        select(Conversation)
        .where(Conversation.collection_id == collection_id, Conversation.user_id == user.id)
        .order_by(Conversation.created_at.desc())
    ).all()
    return [ConversationOut(id=c.id, title=c.title, created_at=c.created_at) for c in rows]


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def list_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    convo = db.get(Conversation, conversation_id)
    if convo is None or convo.user_id != user.id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    rows = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    ).all()
    return [
        MessageOut(
            id=m.id,
            role=m.role,
            content=m.content,
            citations=m.citations or [],
            created_at=m.created_at,
        )
        for m in rows
    ]


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/collections/{collection_id}/chat")
async def chat(
    collection_id: str,
    body: ChatRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    get_owned_collection(collection_id, db, user)

    # Resolve or create the conversation.
    if body.conversation_id:
        convo = db.get(Conversation, body.conversation_id)
        if convo is None or convo.user_id != user.id:
            raise HTTPException(status_code=404, detail="Conversation not found")
    else:
        convo = Conversation(
            collection_id=collection_id,
            user_id=user.id,
            title=body.message[:60] or "New conversation",
        )
        db.add(convo)
        db.commit()
        db.refresh(convo)

    conversation_id = convo.id

    # Persist the user's message.
    db.add(Message(conversation_id=conversation_id, role="user", content=body.message))
    db.commit()

    # Prior turns for context (exclude the just-added message at generation time
    # by capturing history first).
    history = db.scalars(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
    ).all()

    # Retrieve grounding chunks.
    retrieved = await retrieve(db, collection_id, body.message)
    citations = [
        {
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "filename": c.filename,
            "snippet": c.content[:300],
            "score": c.score,
            "index": i + 1,
        }
        for i, c in enumerate(retrieved)
    ]

    context_prompt = build_context_prompt(retrieved, body.message)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for m in history[:-1]:  # all but the current user message
        messages.append({"role": m.role, "content": m.content})
    messages.append({"role": "user", "content": context_prompt})

    chat_provider = get_chat_provider()

    async def event_stream():
        yield _sse({"type": "meta", "conversation_id": conversation_id})

        full = []
        try:
            async for token in chat_provider.stream(messages):
                full.append(token)
                yield _sse({"type": "token", "value": token})
        except Exception as exc:  # noqa: BLE001
            yield _sse({"type": "error", "message": str(exc)})

        answer = "".join(full)
        yield _sse({"type": "citations", "citations": citations})

        # Persist the assistant message in a fresh session.
        save_db = SessionLocal()
        try:
            save_db.add(
                Message(
                    conversation_id=conversation_id,
                    role="assistant",
                    content=answer,
                    citations=citations,
                )
            )
            save_db.commit()
        finally:
            save_db.close()

        yield _sse({"type": "done"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
