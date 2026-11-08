# Test report: Gemini migration and full-project run

Date: 2026-11-08. Branch: `main` plus uncommitted Gemini migration. Machine: local, rootless Docker, Python 3.14.

## Summary

| Area | Result |
|---|---|
| AI layer unit and API tests (fake LLM) | **59 / 59 pass** |
| Live AI features against real Gemini (through the HTTP API) | **9 / 9 pass** |
| Live triage evaluation, 60 cases | Urgency **80%**, department **77%**, emergency recall **23 / 23**, 1 under-triage |
| Frontend unit tests (Vitest) | **18 / 18 pass**; ESLint clean; `tsc` clean |
| Browser E2E (Playwright, AI disabled) | **12 / 13 pass**: admin "Sign out" does not return to login |
| Backend full suite | **137 pass / 31 fail**: 22 fail only when run together with other files, 9 fail on their own; none are in the AI layer |

The Gemini migration caused no regressions. The failure set is identical to the run on the code before the migration, apart from two MinIO tests that were skipped then because MinIO was not running.

## 1. Model selection (this API key)

The key is a **free-tier** key. What it can actually use:

| Model | Result |
|---|---|
| `gemini-3.1-pro-preview`, `gemini-2.5-pro` | Not available to this key (404) |
| `gemini-4-argon` | Free-tier quota is 0 (429) |
| `gemini-3.8-flash`, `gemini-3.7-flash` | Work, but took 62–110 s per call, beyond the 30 s request timeout |
| `gemini-3.5-flash` | Fast (~2–3 s) and accurate (4/4 on eval cases it answered), but **20 requests per day** on the free tier, and it returns occasional 503s under high demand |
| `gemini-3.5-flash-lite` | ~1.5–3.5 s, correct tool calls and JSON; completed the full eval |
| `gemini-3.1-flash-lite` | ~1.5 s, correct tool calls and JSON; separate quota bucket |

**Configured now:** `GEMINI_MODEL=gemini-3.5-flash-lite` (triage, briefings, visit summaries) and `GEMINI_FLASH_MODEL=gemini-3.1-flash-lite` (booking assistant, FAQ). Two different models also means two separate daily quotas.

**With a paid key**, switch `GEMINI_MODEL` to `gemini-3.5-flash` or a Pro model, then re-run the eval. This only needs `.env`, no code change.

## 2. Live AI features (real Gemini, through the API)

The local backend was run with the key against the seeded E2E database, then driven as a patient and as a doctor.

| Check | Result | Latency |
|---|---|---|
| Triage, non-emergency (cough + mild fever), two turns | routine / General Medicine, sensible rationale | 3.5 s |
| Triage, emergency ("crushing chest pain…") | Rules short-circuit, emergency banner shown, no LLM call | <0.1 s |
| Booking assistant: search doctors, get slots, propose | Found the cardiologist, picked the earliest slot, showed the confirmation card | 7.8 s (3 turns) |
| Confirm proposal | Appointment created (201) | 0.1 s |
| Replay the same confirmation | Rejected (409) | <0.1 s |
| FAQ, in scope ("visiting hours") | Correct answer, cited `visiting-hours.md` | 1.3 s |
| FAQ, out of scope | "I don't have that information…", no hallucination | <0.1 s |
| Doctor pre-visit briefing | Valid structured JSON, AI-generated | 1.9 s |
| Visit summary | Valid structured JSON, AI-generated | 4.1 s |

## 3. Live triage evaluation (`gemini-3.5-flash-lite`)

The full output is in `backend/app/ai/evals/REPORT.md` (`python -m app.ai.evals.run --live --delay 4`).

- **Rules only:** 23 / 23 emergencies caught, 0 / 37 false positives.
- **Full pipeline (rules first, then the model):** urgency 48 / 60 (80%), department 46 / 60 (77%).
- **Model alone** (the 37 non-emergency cases): urgency 25 / 37 (68%). Of the 12 misses, 11 err on the side of caution:
  - 9 urgent cases called emergency (u04, u05, u07, u08, u09, u10, u11, u13, u15)
  - 1 routine case called urgent (r02)
  - 1 self-care case called routine (s09)
- **One unsafe miss, u12:** shingles-like rash (painful blistering band on one side of the ribs) was triaged **routine**; expected urgent.

The model over-triages to Emergency, which is safe but would load the emergency department in practice. Prompt tuning, or a stronger model on a paid key, is the next step. Re-run the eval after any prompt or model change.

## 4. Bugs found (pre-existing, not caused by the migration)

| # | Bug | Evidence |
|---|---|---|
| 1 | **Forgot-password returns 500.** `api/auth.py:209` passes the `User` object to `create_reset_token`, which expects an email string (`'User' object has no attribute 'lower'`). Password reset is completely broken. | `test_auth::test_password_reset_flow`, `test_email_smtp::test_forgot_password_sends_smtp_email` |
| 2 | **Red-flag rules ignore negation.** "I do not have chest pain" and "no chest pain" trigger the chest-pain emergency. Fail-safe, but a patient answering screening questions with "no" is sent to emergency. | Found in the live check; `detect_red_flags("I do not have chest pain")` returns `chest_pain` |
| 3 | **Data-retention purge crashes.** `scripts/purge_data.py:84` uses `AIConversation.patient_id`, which does not exist. | `test_data_retention` |
| 4 | **Logout and refresh-cookie flow.** An audit-log insert has a NULL `status_code` (NOT NULL constraint). | `test_auth::test_logout_revokes_refresh`, `test_refresh_token_cookie_flow` |
| 5 | **Admin "Sign out" in the browser** stays on the Audit logs page. The backend logout returned 200. Fails every run. | E2E `full-flow.spec.ts:106` |
| 6 | **Key rotation** fails (`MissingGreenlet`, then `InvalidToken`). | `test_key_rotation` |
| 7 | **SMTP STARTTLS detection** assertion fails. | `test_email_smtp::test_send_email_smtp_starttls_detection` |
| 8 | **S3 tests vs local MinIO:** uploads request SSE-KMS, and MinIO has no KMS configured. Probably a test or dev-config issue. | `test_storage_s3` (2) |

`to_Do.md` marks items 15, 18 and 21 (refresh-token cookies, data retention) as done, but bugs 3 and 4 show they are not working.

**Test isolation:** 22 failures (`test_documents` 11, `test_patients_records` 8, `test_rbac_patients` 3) pass when their file runs alone, so earlier tests leave state that breaks them. Fixing this makes the suite trustworthy again. `test_scheduling::test_concurrent_booking_exactly_one_success` is flaky (fails about 1 run in 4).

## 5. Operational notes for Gemini

- **Patient data:** do not send real patient data on this free-tier key. Google may use free-tier content to improve its products. Use a paid project, ideally Vertex AI under Google's BAA (see `docs/COMPLIANCE.md`).
- **Quotas:** free-tier daily caps are per model (20 per day for `gemini-3.5-flash`). When a cap is hit, the client's breaker opens and the app falls back to its non-AI behaviour; it does not error. The Flash-Lite caps were not reached during this run.
- **Retries:** the client retries 429 and 5xx errors with a 0.5–1 s backoff. That helps with momentary 503s but not with per-minute or daily quota errors.

## How to reproduce

```bash
make e2e-up                                              # stack, AI off
cd backend && .venv/bin/python -m pytest                 # backend suite
.venv/bin/python -m app.ai.evals.run --live --delay 4    # needs GEMINI_API_KEY
cd ../frontend && npx vitest run && npx playwright test
```
