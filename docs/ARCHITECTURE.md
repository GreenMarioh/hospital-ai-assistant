# Architecture
```mermaid
flowchart LR
  Browser --> Caddy --> Frontend[Next.js]
  Caddy --> API[FastAPI]
  Frontend --> API
  API --> DB[(PostgreSQL 16)]
  API --> Storage[(Local / S3)]
  API --> AI[Anthropic API]
  Worker[APScheduler worker] --> DB
```
ER diagram is added in Phase 2.
