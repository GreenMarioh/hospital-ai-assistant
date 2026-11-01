# Security & PHI Handling

This system is designed around HIPAA-style safeguards. **It is not a compliance certification.** A real
deployment needs a risk assessment, BAAs with vendors (including the LLM provider), and organisational policy.

## PHI inventory
| Data | Where | Protection |
|---|---|---|
| Demographics, contacts | `patients` | TLS in transit; DB volume encryption (host/cloud); RBAC + audit |
| Insurance ID | `patients.insurance_id_encrypted` | Fernet field encryption (key in env/secret manager); masked in lists |
| Visit notes, diagnoses, prescriptions | `visits`, `prescriptions` | Only the patient and doctors with an appointment/visit relationship; edits versioned |
| Documents | storage backend (local volume / S3) | Type/size/magic-byte validation, scanner hook, 5-minute signed links, private bucket + SSE |
| AI conversations | `ai_conversations`, `ai_messages` | Stored in DB (contain patient-typed symptoms); logs hold metadata only |
| Access history | `audit_logs` | Every `/api/*` request: user, role, action, resource, status, IP, request id |

## Threat model (STRIDE summary)
| Threat | Mitigation | Residual risk |
|---|---|---|
| Spoofing: stolen credentials | argon2id (OWASP profile), lockout after 5 failures (15 min), auth rate limiting, 15-minute access tokens, rotating refresh tokens with reuse detection (reuse revokes all sessions) | No MFA yet |
| Tampering: privilege escalation, IDOR | Role dependencies on every route; central object-level checks (`services/access.py`); unauthorised object access returns 404; cross-patient tests | Any new endpoint must use the access helpers |
| Repudiation | Audit log for all API calls (written after the response; failures logged); versioned record edits with editor id | Audit rows are in the same DB; ship to WORM storage for stronger guarantees |
| Information disclosure | Least-privilege roles (admin/reception cannot read clinical notes); PII minimisation before LLM calls; no PHI in logs; field encryption; CSP + security headers; signed document links | LLM provider still receives symptom text and clinical excerpts: needs a BAA / zero-retention terms |
| Denial of service | Rate limits on auth and AI routes, 10 MB upload cap, pagination caps, DB pools, circuit breaker for the LLM | No WAF; add at the edge |
| Elevation via AI | Rule-based red flags independent of the LLM; output guard against diagnosis/medication; booking assistant tools are read-only and cannot book without an explicit user confirmation call; prompt-injection text in records is wrapped as data | LLMs can still produce poor triage: outputs are advisory and flagged "requires clinician review" |
| Upload attacks | Content-type allowlist + magic bytes, sanitised filenames, random storage keys, path-traversal guard, EICAR-level scanner hook (plug in ClamAV), `nosniff` + attachment disposition | Real AV engine must be configured in production |
| SQL injection / XSS | SQLAlchemy parameterised queries; React escaping; CSP; JSON API only | CSP allows `unsafe-inline` scripts (Next.js bootstrap): move to nonces |
| CSRF | Bearer tokens in the `Authorization` header (no ambient cookies), strict CORS allowlist | See token storage below |
| Log forgery | Audit IP taken from uvicorn's trusted-proxy rewriting, never from a raw `X-Forwarded-For` | Backend must only be reachable through the reverse proxy |

## Authentication design notes
- Access token (15 min JWT, HS256) is kept **in memory**; the refresh token lives in `sessionStorage` (per tab, cleared on close). This avoids
  CSRF but means an XSS bug could steal the refresh token. The CSP and React escaping reduce that risk; the alternative (BFF with httpOnly cookies + CSRF tokens) is a possible future change.
- Password reset tokens are single-use, hashed at rest, valid 1 hour; the API never reveals whether an email exists. The dev email backend logs the token: **use `EMAIL_BACKEND=smtp` in production.**
- Deactivating a user invalidates their access on the next request.

## Data lifecycle
- Clinical tables use `deleted_at` soft deletion; nothing clinical is hard-deleted by the application.
- Admin-only endpoints: patient data export (`GET /api/admin/patients/{id}/export`) and erasure requests (`POST .../deletion-request`, soft-deletes and disables the portal account; hard deletion after the retention period is a documented manual DB operation).
- Backups: daily encrypted dumps (see `docs/RUNBOOK.md`); restore is tested by `infra/scripts/restore-test.sh`.

## Secrets
Only via environment / secret manager. `.env` is git-ignored; `.env.example` holds placeholders. Rotate `SECRET_KEY` (invalidates sessions) and
`FIELD_ENCRYPTION_KEY` (requires re-encrypting `insurance_id_encrypted`; no automated rotation yet).
The runtime DB role (`hospital_app`) has DML only; the migrator role owns the schema.

## Security testing results
Recorded on 2026-09-30. CI on 2026-11-01 found new `npm audit` advisories, including a critical one in Next.js; see `to_Do.md`.

| Check | Result |
|---|---|
| `pip-audit` (backend deps) | No known vulnerabilities |
| `bandit -r app` | No issues (one intentional `random` use for retry jitter is annotated) |
| `npm audit` (frontend, incl. dev) | 0 vulnerabilities (after Next's bundled `postcss` override and upgrading Vitest/Vite) |
| Trivy image scan (HIGH/CRITICAL, fixed only) | See "Trivy" below |
| axe-core WCAG 2.1 A/AA on all main pages of all four roles | 0 violations (automated checks cover only a subset of WCAG; manual screen-reader/keyboard review is still advised) |
| k6 load test | See `docs/LOADTEST.md` |
