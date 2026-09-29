from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Appointment, Doctor, Patient, User
from tests.conftest import ADMIN, login_headers


async def _ids():
    async with SessionLocal() as db:
        p1 = (
            await db.execute(
                select(Patient)
                .join(User, Patient.user_id == User.id)
                .where(User.email == "patient1@example.com")
            )
        ).scalar_one()
        p2 = (
            await db.execute(
                select(Patient)
                .join(User, Patient.user_id == User.id)
                .where(User.email == "patient2@example.com")
            )
        ).scalar_one()
        d1 = (
            await db.execute(
                select(Doctor)
                .join(User, Doctor.user_id == User.id)
                .where(User.email == "doctor1@hospital.example.com")
            )
        ).scalar_one()
        return p1.id, p2.id, d1.id


async def test_unauthenticated_denied(client):
    p1, _, _ = await _ids()
    assert (await client.get(f"/api/patients/{p1}")).status_code == 401
    assert (await client.get("/api/admin/users")).status_code == 401


async def test_patient_reads_own_but_not_other_patient(client):
    p1, p2, _ = await _ids()
    h = await login_headers(client, "patient1@example.com")
    assert (await client.get(f"/api/patients/{p1}", headers=h)).status_code == 200
    assert (await client.get(f"/api/patients/{p2}", headers=h)).status_code == 404


async def test_staff_and_admin_read_any_patient(client):
    _, p2, _ = await _ids()
    for email, pw in [("staff@hospital.example.com", None), (ADMIN[0], ADMIN[1])]:
        h = await login_headers(client, email, pw) if pw else await login_headers(client, email)
        assert (await client.get(f"/api/patients/{p2}", headers=h)).status_code == 200


async def test_doctor_only_sees_patients_with_relationship(client):
    p1, p2, d1 = await _ids()
    h = await login_headers(client, "doctor1@hospital.example.com")
    assert (await client.get(f"/api/patients/{p1}", headers=h)).status_code == 404
    start = datetime.now(UTC) + timedelta(days=1)
    async with SessionLocal() as db:
        db.add(
            Appointment(
                patient_id=p1, doctor_id=d1, starts_at=start, ends_at=start + timedelta(minutes=30)
            )
        )
        await db.commit()
    assert (await client.get(f"/api/patients/{p1}", headers=h)).status_code == 200
    assert (await client.get(f"/api/patients/{p2}", headers=h)).status_code == 404


async def test_non_patient_cannot_use_patients_me(client):
    h = await login_headers(client, "staff@hospital.example.com")
    assert (await client.get("/api/patients/me", headers=h)).status_code == 403


async def test_soft_deleted_patient_hidden(client):
    p1, _, _ = await _ids()
    async with SessionLocal() as db:
        (await db.get(Patient, p1)).deleted_at = datetime.now(UTC)
        await db.commit()
    h = await login_headers(client, ADMIN[0], ADMIN[1])
    try:
        assert (await client.get(f"/api/patients/{p1}", headers=h)).status_code == 404
    finally:
        async with SessionLocal() as db:
            (await db.get(Patient, p1)).deleted_at = None
            await db.commit()
