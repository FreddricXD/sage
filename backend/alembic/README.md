# Migrations

At runtime the app calls `init_db()` on startup (see `app/db.py`), which creates
the `vector` extension, all tables, and the HNSW index. This makes a clean
`docker compose up` work with no extra steps.

Alembic is configured here for teams that prefer versioned migrations. To
generate and apply migrations instead:

```bash
alembic revision --autogenerate -m "init"
alembic upgrade head
```
