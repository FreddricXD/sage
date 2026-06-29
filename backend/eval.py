"""Lightweight retrieval evaluation harness.

Measures retrieval hit-rate@k: for a small set of questions with known expected
keywords, checks whether the retrieved chunks contain the expected text. Run
inside the API container after seeding so the demo collection exists:

    docker compose exec api python eval.py

This is intentionally simple (no external eval deps) but demonstrates how you'd
measure retrieval quality and guard against regressions.
"""

import asyncio

from app.db import SessionLocal
from app.models import Collection
from app.rag.retrieve import retrieve

# (question, expected substring that a relevant chunk should contain)
EVAL_SET = [
    ("What database does Sage use for vectors?", "pgvector"),
    ("How are answers grounded?", "context"),
    ("Can the model backend be changed?", "Ollama"),
]


async def main() -> None:
    db = SessionLocal()
    try:
        collection = db.query(Collection).first()
        if not collection:
            print("No collection found. Run `python seed.py` first.")
            return

        hits = 0
        for question, expected in EVAL_SET:
            chunks = await retrieve(db, collection.id, question, top_k=5)
            joined = " ".join(c.content.lower() for c in chunks)
            ok = expected.lower() in joined
            hits += int(ok)
            print(f"[{'PASS' if ok else 'MISS'}] {question}")

        rate = hits / len(EVAL_SET)
        print(f"\nHit-rate@5: {hits}/{len(EVAL_SET)} = {rate:.0%}")
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(main())
