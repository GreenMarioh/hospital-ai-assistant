import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment, Doctor, Patient, User, Visit


async def authorize_patient_access(db: AsyncSession, user: User, patient_id: uuid.UUID) -> Patient:
    """Central object-level authorization for patient data.

    admin/staff: any patient. patient: only own record. doctor: only patients they have
    an appointment or visit with. Non-matching access returns 404 to avoid leaking existence.
    """
    patient = (
        await db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    role = user.role.name
    allowed = False
    if patient is not None:
        if role in ("admin", "staff"):
            allowed = True
        elif role == "patient":
            allowed = patient.user_id == user.id
        elif role == "doctor":
            doctor_id = (
                await db.execute(select(Doctor.id).where(Doctor.user_id == user.id))
            ).scalar_one_or_none()
            if doctor_id is not None:
                appt = await db.execute(
                    select(Appointment.id)
                    .where(Appointment.doctor_id == doctor_id, Appointment.patient_id == patient_id)
                    .limit(1)
                )
                visit = await db.execute(
                    select(Visit.id)
                    .where(Visit.doctor_id == doctor_id, Visit.patient_id == patient_id)
                    .limit(1)
                )
                allowed = appt.first() is not None or visit.first() is not None
    if not allowed or patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    return patient
