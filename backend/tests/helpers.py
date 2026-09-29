from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.core.db import SessionLocal
from app.models import Appointment, Doctor, Patient, User


async def by_email(model, email: str):
    fk = model.user_id
    async with SessionLocal() as db:
        return (
            await db.execute(select(model).join(User, fk == User.id).where(User.email == email))
        ).scalar_one()


async def link_doctor_patient(doctor_email: str, patient_email: str, days: int = 1):
    doc = await by_email(Doctor, doctor_email)
    pat = await by_email(Patient, patient_email)
    start = datetime.now(UTC) + timedelta(days=days)
    async with SessionLocal() as db:
        db.add(
            Appointment(
                patient_id=pat.id,
                doctor_id=doc.id,
                starts_at=start,
                ends_at=start + timedelta(minutes=30),
            )
        )
        await db.commit()
    return doc, pat
