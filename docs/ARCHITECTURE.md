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

## ER diagram
```mermaid
erDiagram
  roles ||--o{ users : has
  users ||--o| patients : "portal account"
  users ||--o| doctors : "is"
  departments ||--o{ doctors : contains
  doctors ||--o{ doctor_availability : weekly
  doctors ||--o{ availability_exceptions : leave
  patients ||--o{ appointments : books
  doctors ||--o{ appointments : serves
  patients ||--o{ waitlist_entries : waits
  doctors ||--o{ waitlist_entries : for
  patients ||--o{ visits : has
  doctors ||--o{ visits : conducts
  appointments ||--o| visits : produces
  visits ||--o{ prescriptions : has
  patients ||--o{ documents : owns
  patients ||--o{ ai_summaries : has
  users ||--o{ ai_conversations : starts
  ai_conversations ||--o{ ai_messages : contains
  patients ||--o{ notifications : receives
  users ||--o{ audit_logs : generates
  users ||--o{ refresh_tokens : holds
```
Key constraints: GiST exclusion `ex_appointments_no_overlap` (no overlapping booked/completed appointments per doctor);
`visits.search_vector` generated `tsvector` with GIN index; `deleted_at` on clinical tables; `record_versions` snapshots every edit.
