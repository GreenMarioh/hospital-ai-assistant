import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Patient, User
from app.schemas.patients import PatientOut
from app.services.access import authorize_patient_access

router = APIRouter(prefix="/api/patients", tags=["patients"])


@router.get("/me", response_model=PatientOut)
async def my_profile(
    db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("patient"))
) -> Patient:
    patient = (
        await db.execute(
            select(Patient).where(Patient.user_id == user.id, Patient.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient profile not found")
    return patient


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Patient:
    return await authorize_patient_access(db, user, patient_id)
