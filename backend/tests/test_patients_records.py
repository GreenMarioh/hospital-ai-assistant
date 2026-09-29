import uuid

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Patient, RecordVersion
from tests.conftest import ADMIN, login_headers
from tests.helpers import by_email, link_doctor_patient

D1, S, P1, P2 = (
    "doctor1@hospital.example.com",
    "staff@hospital.example.com",
    "patient1@example.com",
    "patient2@example.com",
)
NEW = {"first_name": "Zed", "last_name": "Testerson", "date_of_birth": "1980-02-03",
       "phone": "5550001111", "allergies": ["peanut"], "blood_group": "A+", "insurance_id": "INS-1234567"}  # fmt: skip


async def test_staff_creates_searches_updates_patient(client):
    h = await login_headers(client, S)
    r = await client.post("/api/patients", json=NEW, headers=h)
    assert r.status_code == 201
    pid = r.json()["id"]
    assert r.json()["insurance_id_masked"] == "*******4567"  # encrypted at rest, masked on list
    got = (await client.get(f"/api/patients/{pid}", headers=h)).json()
    assert got["insurance_id_masked"] == "INS-1234567"
    async with SessionLocal() as db:
        raw = (await db.get(Patient, uuid.UUID(pid))).insurance_id_encrypted
    assert raw and "INS-1234567" not in raw
    page = (await client.get("/api/patients", params={"q": "testerson"}, headers=h)).json()
    assert page["total"] == 1 and page["items"][0]["id"] == pid
    assert (await client.get("/api/patients", params={"q": "5550001"}, headers=h)).json()[
        "total"
    ] == 1
    assert (await client.get("/api/patients", params={"q": pid}, headers=h)).json()["total"] == 1
    assert (await client.get("/api/patients", params={"q": "%"}, headers=h)).json()[
        "total"
    ] == 0  # escaped wildcard
    r = await client.patch(
        f"/api/patients/{pid}", json={"phone": "999", "insurance_id": "NEW-9999"}, headers=h
    )
    assert r.json()["phone"] == "999" and r.json()["insurance_id_masked"] == "NEW-9999"


async def test_pagination(client):
    h = await login_headers(client, S)
    page = (await client.get("/api/patients", params={"size": 2, "page": 2}, headers=h)).json()
    assert (
        page["size"] == 2 and page["page"] == 2 and len(page["items"]) >= 1 and page["total"] >= 3
    )
    assert (await client.get("/api/patients", params={"size": 500}, headers=h)).status_code == 422


async def test_patient_creation_validation_and_permissions(client):
    hp = await login_headers(client, P1)
    assert (await client.post("/api/patients", json=NEW, headers=hp)).status_code == 403
    hs = await login_headers(client, S)
    assert (
        await client.post("/api/patients", json={**NEW, "blood_group": "Z9"}, headers=hs)
    ).status_code == 422
    assert (await client.get("/api/patients", headers=hp)).status_code == 403


async def test_patient_can_edit_only_contact_details(client):
    h = await login_headers(client, P1)
    me = (await client.get("/api/patients/me", headers=h)).json()
    assert (
        await client.patch(f"/api/patients/{me['id']}", json={"phone": "12345"}, headers=h)
    ).status_code == 200
    assert (
        await client.patch(f"/api/patients/{me['id']}", json={"blood_group": "O+"}, headers=h)
    ).status_code == 403
    other = (await by_email(Patient, P2)).id
    assert (
        await client.patch(f"/api/patients/{other}", json={"phone": "1"}, headers=h)
    ).status_code == 404


async def test_soft_delete_admin_only(client):
    hs, ha = await login_headers(client, S), await login_headers(client, ADMIN[0], ADMIN[1])
    pid = (await client.post("/api/patients", json=NEW, headers=hs)).json()["id"]
    assert (await client.delete(f"/api/patients/{pid}", headers=hs)).status_code == 403
    assert (await client.delete(f"/api/patients/{pid}", headers=ha)).status_code == 204
    assert (await client.get(f"/api/patients/{pid}", headers=hs)).status_code == 404
    async with SessionLocal() as db:  # row still exists
        assert (await db.get(Patient, uuid.UUID(pid))).deleted_at is not None


async def test_doctor_lists_only_own_patients(client):
    h = await login_headers(client, D1)
    assert (await client.get("/api/patients", headers=h)).json()["total"] == 0
    await link_doctor_patient(D1, P1)
    page = (await client.get("/api/patients", headers=h)).json()
    assert page["total"] == 1


async def test_visit_lifecycle_versioning_and_prescriptions(client):
    _, pat = await link_doctor_patient(D1, P1)
    h = await login_headers(client, D1)
    r = await client.post(f"/api/patients/{pat.id}/visits", headers=h, json={
        "chief_complaint": "persistent cough", "notes": "dry cough two weeks",
        "diagnosis": "bronchitis", "vitals": {"heart_rate": 80, "spo2": 97}, "follow_up_date": "2030-01-01"})  # fmt: skip
    assert r.status_code == 201
    v = r.json()
    assert v["version"] == 1 and v["vitals"]["heart_rate"] == 80
    r = await client.patch(f"/api/visits/{v['id']}", headers=h, json={"notes": "cough improving"})
    assert r.json()["version"] == 2 and r.json()["notes"] == "cough improving"
    await client.patch(f"/api/visits/{v['id']}", headers=h, json={"diagnosis": "resolved"})
    versions = (await client.get(f"/api/visits/{v['id']}/versions", headers=h)).json()
    assert [x["version"] for x in versions] == [1, 2]
    assert versions[0]["data"]["notes"] == "dry cough two weeks" and versions[0]["changed_by"]
    rx = await client.post(
        f"/api/visits/{v['id']}/prescriptions",
        headers=h,
        json={"drug_name": "Drug A", "dosage": "5mg"},
    )
    assert rx.status_code == 201
    rx_id = rx.json()["id"]
    assert (
        await client.patch(
            f"/api/prescriptions/{rx_id}", headers=h, json={"drug_name": "Drug A", "dosage": "10mg"}
        )
    ).json()["dosage"] == "10mg"
    assert len((await client.get(f"/api/visits/{v['id']}", headers=h)).json()["prescriptions"]) == 1
    assert (await client.delete(f"/api/prescriptions/{rx_id}", headers=h)).status_code == 204
    assert (await client.get(f"/api/visits/{v['id']}", headers=h)).json()["prescriptions"] == []
    async with SessionLocal() as db:
        n = len(
            (
                await db.execute(
                    select(RecordVersion).where(RecordVersion.entity_type == "prescription")
                )
            )
            .scalars()
            .all()
        )
    assert n == 2
    assert (await client.delete(f"/api/visits/{v['id']}", headers=h)).status_code == 204
    assert (await client.get(f"/api/visits/{v['id']}", headers=h)).status_code == 404


async def test_visit_validation(client):
    _, pat = await link_doctor_patient(D1, P1)
    h = await login_headers(client, D1)
    bad = await client.post(
        f"/api/patients/{pat.id}/visits", headers=h, json={"vitals": {"spo2": 500}}
    )
    assert bad.status_code == 422
    bad = await client.post(
        f"/api/patients/{pat.id}/visits", headers=h, json={"appointment_id": str(uuid.uuid4())}
    )
    assert bad.status_code == 422


async def test_clinical_data_access_control(client):
    _, p1 = await link_doctor_patient(D1, P1)
    hd = await login_headers(client, D1)
    v = (
        await client.post(
            f"/api/patients/{p1.id}/visits", headers=hd, json={"chief_complaint": "x"}
        )
    ).json()
    # patient can read their own visit but not edit
    hp1 = await login_headers(client, P1)
    assert (await client.get(f"/api/visits/{v['id']}", headers=hp1)).status_code == 200
    assert (
        await client.patch(f"/api/visits/{v['id']}", headers=hp1, json={"notes": "n"})
    ).status_code == 403
    # other patient, unrelated doctor, staff and admin cannot
    for email, pw in [
        (P2, None),
        ("doctor2@hospital.example.com", None),
        (S, None),
        (ADMIN[0], ADMIN[1]),
    ]:
        h = await login_headers(client, email, pw) if pw else await login_headers(client, email)
        assert (await client.get(f"/api/visits/{v['id']}", headers=h)).status_code in (403, 404)
        assert (await client.get(f"/api/patients/{p1.id}/visits", headers=h)).status_code in (
            403,
            404,
        )
    # a related but different doctor cannot edit
    await link_doctor_patient("doctor2@hospital.example.com", P1, days=2)
    h2 = await login_headers(client, "doctor2@hospital.example.com")
    assert (await client.get(f"/api/visits/{v['id']}", headers=h2)).status_code == 200
    assert (
        await client.patch(f"/api/visits/{v['id']}", headers=h2, json={"notes": "n"})
    ).status_code == 403


async def test_fulltext_search_is_scoped(client):
    _, p1 = await link_doctor_patient(D1, P1)
    hd = await login_headers(client, D1)
    await client.post(
        f"/api/patients/{p1.id}/visits",
        headers=hd,
        json={"chief_complaint": "migraine with aura", "notes": "photophobia"},
    )
    hits = (await client.get("/api/search/records", params={"q": "migraine"}, headers=hd)).json()
    assert len(hits) == 1 and "migraine" in hits[0]["snippet"].lower()
    assert (
        await client.get(
            "/api/search/records",
            params={"q": "photophobia"},
            headers=await login_headers(client, P1),
        )
    ).json()
    assert (
        await client.get(
            "/api/search/records", params={"q": "migraine"}, headers=await login_headers(client, P2)
        )
    ).json() == []
    assert (
        await client.get(
            "/api/search/records",
            params={"q": "migraine"},
            headers=await login_headers(client, "doctor2@hospital.example.com"),
        )
    ).json() == []
    assert (
        await client.get(
            "/api/search/records", params={"q": "migraine"}, headers=await login_headers(client, S)
        )
    ).status_code == 403


async def test_timeline_visibility_by_role(client):
    _, p1 = await link_doctor_patient(D1, P1)
    hd = await login_headers(client, D1)
    await client.post(
        f"/api/patients/{p1.id}/visits", headers=hd, json={"chief_complaint": "checkup"}
    )
    kinds_doc = {
        e["kind"] for e in (await client.get(f"/api/patients/{p1.id}/timeline", headers=hd)).json()
    }
    kinds_staff = {
        e["kind"]
        for e in (
            await client.get(
                f"/api/patients/{p1.id}/timeline", headers=await login_headers(client, S)
            )
        ).json()
    }
    assert kinds_doc == {"appointment", "visit"} and kinds_staff == {"appointment"}


async def test_ai_summaries_hidden_from_patient_timeline(client):
    from app.models import AISummary

    _, p1 = await link_doctor_patient(D1, P1)
    async with SessionLocal() as db:
        db.add(AISummary(patient_id=p1.id, kind="briefing", content={"summary": "x"}))
        await db.commit()
    hd, hp = await login_headers(client, D1), await login_headers(client, P1)
    assert "ai_summary" in {
        e["kind"] for e in (await client.get(f"/api/patients/{p1.id}/timeline", headers=hd)).json()
    }
    assert "ai_summary" not in {
        e["kind"] for e in (await client.get(f"/api/patients/{p1.id}/timeline", headers=hp)).json()
    }
