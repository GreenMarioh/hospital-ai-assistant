# Decisions & Assumptions
- **Python 3.14** (spec said 3.12): the dev host only has 3.14; all dependencies install cleanly on it. Images use `python:3.14-slim`.
- **Rootless Docker** used on the dev host (no sudo). Postgres published on host port 5433 because 5432 is taken.
- **Background jobs: APScheduler** in a dedicated worker process. Simpler than Celery+Redis; deduplication via the `notifications` table so restarts never double-send.
- **Caddy** replaces Nginx for TLS (automatic Let's Encrypt renewal).
- **RAG**: Postgres full-text search over `knowledge_base/*.md` (pgvector deferred).
- **Field encryption**: Fernet with key from env for insurance ID.
- **Least privilege DB**: `hospital_app` runtime role (DML only); `hospital_migrator` owns schema and runs Alembic.
