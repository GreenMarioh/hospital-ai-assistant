# AI Hospital Management Assistant

Patient management, appointment scheduling, medical record organization and AI-assisted
triage/summaries. The AI provides **decision support and administrative automation only** — it never
diagnoses or prescribes, and all clinical-adjacent output is marked "AI-generated, requires clinician review."

## Quick start (local)
```bash
cp .env.example .env      # set SECRET_KEY, FIELD_ENCRYPTION_KEY, ANTHROPIC_API_KEY (optional)
make dev                  # db + backend (:8000) + frontend (:3000)
curl localhost:8000/healthz
```
Postgres is exposed on `127.0.0.1:5433` for local tooling. See `docs/` for architecture and decisions.

## Layout
`backend/` FastAPI · `frontend/` Next.js · `infra/` compose + scripts · `docs/` · `knowledge_base/` FAQ docs.
