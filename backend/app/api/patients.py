import re
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_field, encrypt_field
from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.models import AISummary, Appointment, Doctor, Document, Patient, User, Visit
from app.schemas.patients import (
    PatientCreate,
    PatientOut,
    PatientPage,
    PatientUpdate,
    TimelineEvent,
)
from app.services.access import authorize_patient_access, get_patient_for_user

router = APIRouter(prefix="/api/patients", tags=["patients"])


def to_out(p: Patient, reveal_insurance: bool = False) -> PatientOut:
    out = PatientOut.model_validate(p)
    if p.insurance_id_encrypted:
        plain = decrypt_field(p.insurance_id_encrypted)
        out.insurance_id_masked = (
            plain if reveal_insurance else "*" * max(len(plain) - 4, 0) + plain[-4:]
        )
    return out


def _like(q: str) -> str:
    return "%" + re.sub(r"([\\%_])", r"\\\1", q.strip()) + "%"


@router.post("", response_model=PatientOut, status_code=status.HTTP_201_CREATED)
async def create_patient(
    body: PatientCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("staff", "admin")),
) -> PatientOut:
    data = body.model_dump(exclude={"insurance_id"})
    patient = Patient(**data)
    if body.insurance_id:
        patient.insurance_id_encrypted = encrypt_field(body.insurance_id)
    db.add(patient)
    await db.commit()
    await db.refresh(patient)
    return to_out(patient)


@router.get("", response_model=PatientPage)
async def list_patients(
    q: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("staff", "admin", "doctor")),
) -> PatientPage:
    stmt = select(Patient).where(Patient.deleted_at.is_(None))
    if user.role.name == "doctor":
        doctor_id = select(Doctor.id).where(Doctor.user_id == user.id).scalar_subquery()
        related = (
            select(Appointment.patient_id)
            .where(Appointment.doctor_id == doctor_id)
            .union(select(Visit.patient_id).where(Visit.doctor_id == doctor_id))
        )
        stmt = stmt.where(Patient.id.in_(related))
    if q:
        conds: list[ColumnElement[bool]] = [
            Patient.first_name.ilike(_like(q)),
            Patient.last_name.ilike(_like(q)),
            Patient.phone.ilike(_like(q)),
            func.concat(Patient.first_name, " ", Patient.last_name).ilike(_like(q)),
        ]
        try:
            conds.append(Patient.id == uuid.UUID(q.strip()))
        except ValueError:
            pass
        stmt = stmt.where(or_(*conds))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Patient.last_name, Patient.first_name, Patient.id)
            .offset((page - 1) * size)
            .limit(size)
        )
    ).scalars()
    return PatientPage(items=[to_out(p) for p in rows], total=total, page=page, size=size)


@router.get("/me", response_model=PatientOut)
async def my_profile(
    db: AsyncSession = Depends(get_db), user: User = Depends(require_roles("patient"))
) -> PatientOut:
    patient = await get_patient_for_user(db, user)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient profile not found")
    return to_out(patient)


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> PatientOut:
    patient = await authorize_patient_access(db, user, patient_id)
    return to_out(patient, reveal_insurance=user.role.name in ("staff", "admin"))


@router.patch("/{patient_id}", response_model=PatientOut)
async def update_patient(
    patient_id: uuid.UUID,
    body: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("staff", "admin", "patient")),
) -> PatientOut:
    patient = await authorize_patient_access(db, user, patient_id)
    changes = body.model_dump(exclude_unset=True)
    if user.role.name == "patient":  # patients may only maintain contact details
        allowed = {"phone", "email", "address", "emergency_contact_name", "emergency_contact_phone"}
        if set(changes) - allowed:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Patients may only edit contact details")
    insurance_id = changes.pop("insurance_id", None)
    for k, v in changes.items():
        setattr(patient, k, v)
    if insurance_id is not None:
        patient.insurance_id_encrypted = encrypt_field(insurance_id)
    await db.commit()
    await db.refresh(patient)
    return to_out(patient, reveal_insurance=user.role.name in ("staff", "admin"))


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_patient(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("admin")),
) -> Response:
    """Soft delete only; clinical data is never hard-deleted."""
    patient = await authorize_patient_access(db, user, patient_id)
    patient.deleted_at = datetime.now(UTC)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{patient_id}/timeline", response_model=list[TimelineEvent])
async def timeline(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[TimelineEvent]:
    await authorize_patient_access(db, user, patient_id)
    role = user.role.name
    events: list[TimelineEvent] = []
    appts = (
        await db.execute(select(Appointment).where(Appointment.patient_id == patient_id))
    ).scalars()
    events += [
        TimelineEvent(
            kind="appointment",
            id=a.id,
            at=a.starts_at,
            title=f"Appointment ({a.status})",
            detail=a.reason,
        )
        for a in appts
    ]
    docs = (
        await db.execute(
            select(Document).where(Document.patient_id == patient_id, Document.deleted_at.is_(None))
        )
    ).scalars()
    events += [
        TimelineEvent(
            kind="document",
            id=d.id,
            at=d.created_at,
            title=f"Document: {d.filename}",
            detail=d.doc_type,
        )
        for d in docs
    ]
    if role in ("doctor", "patient"):
        visits = (
            await db.execute(
                select(Visit).where(Visit.patient_id == patient_id, Visit.deleted_at.is_(None))
            )
        ).scalars()
        events += [
            TimelineEvent(
                kind="visit", id=v.id, at=v.created_at, title="Visit", detail=v.chief_complaint
            )
            for v in visits
        ]
        sums = (
            await db.execute(select(AISummary).where(AISummary.patient_id == patient_id))
        ).scalars()
        events += [
            TimelineEvent(
                kind="ai_summary",
                id=s.id,
                at=s.created_at,
                title="AI summary (requires clinician review)",
            )
            for s in sums
        ]
    return sorted(events, key=lambda e: e.at, reverse=True)
