#!/usr/bin/env python3
"""Generate docs/API.md from the FastAPI OpenAPI schema (run from repo root: make api-docs)."""

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://x:y@localhost/x")
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
from app.main import app  # noqa: E402

spec = app.openapi()
Path("frontend/openapi.json").write_text(json.dumps(spec, indent=1))
by_tag: dict[str, list[tuple[str, str, dict]]] = defaultdict(list)
for path, ops in sorted(spec["paths"].items()):
    for method, op in ops.items():
        by_tag[(op.get("tags") or ["other"])[0]].append((method.upper(), path, op))

out = [
    "# API reference",
    "",
    "Generated from the OpenAPI schema (`make api-docs`). Interactive docs: `/docs` (Swagger UI) on the API host.",
    "",
    "## Conventions",
    "- Auth: `Authorization: Bearer <access token>` from `POST /api/auth/login` (15 min); renew with `POST /api/auth/refresh` (rotating refresh tokens).",
    "- Roles: `admin`, `doctor`, `staff` (reception), `patient`. Every endpoint enforces its roles server-side; unauthorised object access returns `404`.",
    "- Errors: `{\"detail\": \"...\"}` (validation errors: list of `{loc, msg, type}`); every response carries `X-Request-ID`.",
    "- Booking: send an `Idempotency-Key` header on `POST /api/appointments`; a repeated key returns the original booking (`200` instead of `201`).",
    "- Timestamps are UTC ISO 8601; appointment slots are generated in the hospital timezone.",
    "- AI endpoints return `disclaimer`, `ai_generated` and `requires_clinician_review`; when the AI service is down triage/FAQ/briefings degrade gracefully and the booking assistant returns `503`.",
    "",
]
for tag, ops in sorted(by_tag.items()):
    out += [f"## {tag}", "", "| Method | Path | Summary | Auth |", "|---|---|---|---|"]
    for method, path, op in ops:
        needs_auth = bool(op.get("security")) or any(
            p.get("name") == "authorization" for p in op.get("parameters", [])
        )
        summary = (op.get("summary") or "").replace("|", "/")
        out.append(f"| {method} | `{path}` | {summary} | {'bearer' if needs_auth or path.startswith('/api/') and path not in ('/api/auth/login','/api/auth/register','/api/auth/refresh','/api/auth/logout','/api/auth/forgot-password','/api/auth/reset-password','/api/documents/download') else 'public'} |")
    out.append("")
Path("docs/API.md").write_text("\n".join(out))
print(f"wrote docs/API.md ({sum(len(v) for v in by_tag.values())} operations)")
