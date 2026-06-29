from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create the pgvector extension, all tables, and the vector index.

    Idempotent: safe to run on every startup. Used instead of running Alembic
    at boot so a clean `docker compose up` just works.
    """
    from . import models  # noqa: F401  (ensure models are registered)

    with engine.begin() as conn:
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS chunks_embedding_idx "
                "ON chunks USING hnsw (embedding vector_cosine_ops)"
            )
        )
        # GIN index for hybrid (full-text) search over chunk content.
        conn.execute(
            text(
                "CREATE INDEX IF NOT EXISTS chunks_content_fts_idx "
                "ON chunks USING gin (to_tsvector('english', content))"
            )
        )
