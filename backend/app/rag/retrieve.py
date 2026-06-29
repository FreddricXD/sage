from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..ai.factory import get_embedding_provider
from ..config import settings
from ..models import Chunk, Document


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    filename: str
    content: str
    score: float
    page: int


def reciprocal_rank_fusion(rankings: list[list[str]], k: int = 60) -> dict[str, float]:
    """Combine multiple ranked id lists into one fused score map.

    RRF score for an item = sum over rankings of 1 / (k + rank), where rank is
    0-based position. Robust to differing score scales between rankers (e.g.
    cosine distance vs. ts_rank), which is why it is a standard hybrid-search
    fusion method.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, item_id in enumerate(ranking):
            scores[item_id] = scores.get(item_id, 0.0) + 1.0 / (k + rank)
    return scores


def _vector_candidates(db: Session, collection_id: str, query_vec: list[float], limit: int):
    distance = Chunk.embedding.cosine_distance(query_vec).label("distance")
    return db.execute(
        select(Chunk.id, distance)
        .where(Chunk.collection_id == collection_id)
        .order_by(distance)
        .limit(limit)
    ).all()


def _text_candidates(db: Session, collection_id: str, query: str, limit: int):
    tsv = func.to_tsvector("english", Chunk.content)
    tsq = func.plainto_tsquery("english", query)
    rank = func.ts_rank(tsv, tsq).label("rank")
    return db.execute(
        select(Chunk.id, rank)
        .where(Chunk.collection_id == collection_id, tsv.op("@@")(tsq))
        .order_by(rank.desc())
        .limit(limit)
    ).all()


async def retrieve(
    db: Session, collection_id: str, query: str, top_k: int | None = None
) -> list[RetrievedChunk]:
    k = top_k or settings.top_k
    pool = max(k * 3, k)

    embedder = get_embedding_provider()
    query_vec = (await embedder.embed([query]))[0]

    vector_rows = _vector_candidates(db, collection_id, query_vec, pool)
    # similarity in [0,1] for display, keyed by chunk id
    sim_by_id = {row[0]: max(0.0, 1.0 - float(row[1])) for row in vector_rows}
    vector_ids = [row[0] for row in vector_rows]

    if settings.retrieval_mode == "hybrid":
        text_rows = _text_candidates(db, collection_id, query, pool)
        text_ids = [row[0] for row in text_rows]
        fused = reciprocal_rank_fusion([vector_ids, text_ids])
        ordered_ids = sorted(fused, key=lambda i: fused[i], reverse=True)[:k]
    else:
        ordered_ids = vector_ids[:k]

    if not ordered_ids:
        return []

    # Load full chunk data for the chosen ids and preserve ranking order.
    rows = db.execute(
        select(Chunk, Document.filename)
        .join(Document, Document.id == Chunk.document_id)
        .where(Chunk.id.in_(ordered_ids))
    ).all()
    by_id = {chunk.id: (chunk, filename) for chunk, filename in rows}

    results: list[RetrievedChunk] = []
    for cid in ordered_ids:
        if cid not in by_id:
            continue
        chunk, filename = by_id[cid]
        # Prefer true cosine similarity; fall back for text-only matches.
        score = sim_by_id.get(cid, 0.5)
        results.append(
            RetrievedChunk(
                chunk_id=chunk.id,
                document_id=chunk.document_id,
                filename=filename,
                content=chunk.content,
                score=round(score, 4),
                page=chunk.page,
            )
        )
    return results


SYSTEM_PROMPT = (
    "You are Sage, a helpful research assistant. Answer the user's question "
    "using ONLY the numbered context sources below. Cite the sources you use "
    "inline with bracketed numbers like [1] or [2]. If the answer is not in the "
    "context, say you don't have enough information from the provided documents. "
    "Be concise and accurate."
)


def build_context_prompt(chunks: list[RetrievedChunk], question: str) -> str:
    if not chunks:
        return f"No context sources were found.\n\nQuestion: {question}"

    blocks = []
    for i, c in enumerate(chunks, start=1):
        loc = f" (p.{c.page})" if c.page else ""
        blocks.append(f"[{i}] {c.filename}{loc}:\n{c.content}")
    context = "\n\n".join(blocks)
    return f"Context sources:\n{context}\n\nQuestion: {question}"
