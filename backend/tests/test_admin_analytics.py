import csv
import io
import json
import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.db import SessionLocal
from app.models import AIConversation, AIMessage, Appointment, Doctor, Patient, User
from tests.conftest import ADMIN, login_headers
from tests.helpers import by_email


async def _seed_appts():
    did, pid = (await by_email(Doctor, "doctor1@hospital.example.com")).id, (
        await by_email(Patient, "patient1@example.com")
    ).id
    base = datetime.now(UTC).replace(hour=6, minute=0, second=0, microsecond=0) - timedelta(days=2)
    async with SessionLocal() as db:
        for i, st in enumerate(["completed", "completed", "no_show", "cancelled", "booked"]):
            s = base + timedelta(minutes=30 * i)
            db.add(Appointment(patient_id=pid, doctor_id=did, starts_at=s, ends_at=s + timedelta(minutes=30), status=st, created_at=s - timedelta(hours=48)))  # fmt: skip
        conv = AIConversation(
            user_id=(await by_email(Patient, "patient1@example.com")).user_id,
            kind="triage",
            state={},
        )
        db.add(conv)
        await db.flush()
        db.add(AIMessage(conversation_id=conv.id, role="assistant", content="x", meta={"source": "llm", "latency_ms": 100, "input_tokens": 10, "output_tokens": 5}))  # fmt: skip
        db.add(
            AIMessage(
                conversation_id=conv.id, role="assistant", content="y", meta={"source": "rules"}
            )
        )
        db.add(
            AIMessage(
                conversation_id=conv.id, role="assistant", content="z", meta={"source": "fallback"}
            )
        )
        await db.commit()


async def test_analytics_summary_values(client):
    await _seed_appts()
    ha = await login_headers(client, ADMIN[0], ADMIN[1])
    d = (await client.get("/api/admin/analytics/summary", headers=ha)).json()
    t = d["appointments"]["totals"]
    assert (
        t["total"] == 5
        and t["completed"] == 2
        and t["no_show"] == 1
        and t["cancelled"] == 1
        and t["booked"] == 1
    )
    assert d["no_show_rate"] == pytest.approx(1 / 3, abs=1e-3)
    assert d["avg_booking_lead_hours"] == pytest.approx(48.0, abs=0.2)
    assert d["department_load"][0] == {
        "department": "Cardiology",
        "appointments": 4,
    }  # cancelled excluded
    assert len(d["appointments"]["per_day"]) == 30
    ai = d["ai_usage"]
    assert (
        ai["conversations"] == {"triage": 1}
        and ai["llm_replies"] == 1
        and ai["rule_based_emergency_responses"] == 1
    )
    assert (
        ai["degraded_responses"] == 1 and ai["input_tokens"] == 10 and ai["avg_latency_ms"] == 100.0
    )


async def test_analytics_range_validation_and_auth(client):
    ha = await login_headers(client, ADMIN[0], ADMIN[1])
    assert (
        await client.get(
            "/api/admin/analytics/summary",
            params={"from": "2030-02-01", "to": "2030-01-01"},
            headers=ha,
        )
    ).status_code == 422
    assert (
        await client.get(
            "/api/admin/analytics/summary",
            params={"from": "2020-01-01", "to": "2030-01-01"},
            headers=ha,
        )
    ).status_code == 422
    for email in (
        "staff@hospital.example.com",
        "doctor1@hospital.example.com",
        "patient1@example.com",
    ):
        h = await login_headers(client, email)
        for path in (
            "/api/admin/analytics/summary",
            "/api/admin/analytics/export.csv",
            "/api/admin/audit-logs",
        ):
            assert (await client.get(path, headers=h)).status_code == 403


async def test_csv_export(client):
    await _seed_appts()
    ha = await login_headers(client, ADMIN[0], ADMIN[1])
    r = await client.get("/api/admin/analytics/export.csv", headers=ha)
    assert (
        r.status_code == 200
        and r.headers["content-type"].startswith("text/csv")
        and "attachment" in r.headers["content-disposition"]
    )
    rows = list(csv.reader(io.StringIO(r.text)))
    assert rows[0] == ["date", "total", "booked", "completed", "cancelled", "no_show"]
    assert ["no_show_rate", "0.3333"] in rows and ["Cardiology", "4"] in rows


def test_csv_cell_neutralises_formulas():
    from app.api.analytics import _csv_cell

    assert (
        _csv_cell("=cmd|' /C calc'!A0") == "'=cmd|' /C calc'!A0"
        and _csv_cell("@SUM(1)") == "'@SUM(1)"
        and _csv_cell("ok") == "ok"
        and _csv_cell(5) == 5
    )


async def test_audit_log_viewer_filters(client):
    ha = await login_headers(client, ADMIN[0], ADMIN[1])
    hp = await login_headers(client, "patient1@example.com")
    pid = (await by_email(Patient, "patient1@example.com")).id
    await client.get(f"/api/patients/{pid}", headers=hp)
    await client.get(f"/api/patients/{uuid.uuid4()}", headers=hp)
    page = (
        await client.get(
            "/api/admin/audit-logs",
            params={"resource_type": "patients", "action": "read"},
            headers=ha,
        )
    ).json()
    assert page["total"] >= 2 and all(
        i["resource_type"] == "patients" and i["role"] == "patient" for i in page["items"]
    )
    assert {i["status_code"] for i in page["items"]} == {200, 404}
    only404 = (
        await client.get("/api/admin/audit-logs", params={"status_code": 404}, headers=ha)
    ).json()
    assert only404["total"] >= 1 and all(i["status_code"] == 404 for i in only404["items"])
    by_user = (
        await client.get(
            "/api/admin/audit-logs",
            params={"user_id": str((await by_email(Patient, "patient1@example.com")).user_id)},
            headers=ha,
        )
    ).json()
    assert by_user["total"] >= 2
    today = datetime.now(UTC).date().isoformat()
    assert (
        await client.get(
            "/api/admin/audit-logs", params={"from": today, "to": today, "size": 1}, headers=ha
        )
    ).json()["size"] == 1
    assert (
        await client.get("/api/admin/audit-logs", params={"size": 500}, headers=ha)
    ).status_code == 422


async def test_patient_export_and_deletion_request(client):
    ha = await login_headers(client, ADMIN[0], ADMIN[1])
    pat = await by_email(Patient, "patient3@example.com")
    r = await client.get(f"/api/admin/patients/{pat.id}/export", headers=ha)
    body = r.json()
    assert r.status_code == 200 and body["patient"]["last_name"] == "Patient Three"
    assert "insurance_id_encrypted" not in json.dumps(body) and "storage_key" not in json.dumps(
        body
    )
    assert (
        await client.get(f"/api/admin/patients/{uuid.uuid4()}/export", headers=ha)
    ).status_code == 404
    assert (
        await client.post(f"/api/admin/patients/{pat.id}/deletion-request", headers=ha)
    ).status_code == 202
    assert (
        await client.post(f"/api/admin/patients/{pat.id}/deletion-request", headers=ha)
    ).status_code == 404
    async with SessionLocal() as db:
        assert (await db.get(Patient, pat.id)).deleted_at is not None
        assert (await db.get(User, pat.user_id)).is_active is False
        u = await db.get(User, pat.user_id)
        u.is_active = True  # restore the seeded account for other tests
        (await db.get(Patient, pat.id)).deleted_at = None
        await db.commit()
    hs = await login_headers(client, "staff@hospital.example.com")
    assert (await client.get(f"/api/admin/patients/{pat.id}/export", headers=hs)).status_code == 403
