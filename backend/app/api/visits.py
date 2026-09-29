import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.models import Appointment, Prescription, RecordVersion, User, Visit
from app.schemas.records import (
    PrescriptionIn,
    PrescriptionOut,
    VersionOut,
    VisitIn,
    VisitOut,
    VisitUpdate,
)
from app.services.access import (
    authorize_clinical_access,
    authorize_visit,
    get_doctor_for_user,
)
from app.services.versioning import snapshot

router = APIRouter(prefix="/api", tags=["records"])

VISIT_COLUMNS = ["chief_complaint", "vitals", "notes", "diagnosis", "follow_up_date", "version"]
RX_COLUMNS = ["drug_name", "dosage", "frequency", "duration", "instructions", "deleted_at"]


async def _visit_out(db: AsyncSession, visit: Visit) -> VisitOut:
    rx = (
        await db.execute(
            select(Prescription)
            .where(Prescription.visit_id == visit.id, Prescription.deleted_at.is_(None))
            .order_by(Prescription.created_at)
        )
    ).scalars()
    out = VisitOut.model_validate(visit)
    out.prescriptions = [PrescriptionOut.model_validate(r) for r in rx]
    return out


@router.post(
    "/patients/{patient_id}/visits", response_model=VisitOut, status_code=status.HTTP_201_CREATED
)
async def create_visit(
    patient_id: uuid.UUID,
    body: VisitIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor")),
) -> VisitOut:
    await authorize_clinical_access(db, user, patient_id)
    doctor = await get_doctor_for_user(db, user)
    if doctor is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Doctor profile required")
    if body.appointment_id is not None:
        appt = await db.get(Appointment, body.appointment_id)
        if appt is None or appt.patient_id != patient_id or appt.doctor_id != doctor.id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Appointment mismatch")
    visit = Visit(
        patient_id=patient_id,
        doctor_id=doctor.id,
        appointment_id=body.appointment_id,
        chief_complaint=body.chief_complaint,
        vitals=body.vitals.model_dump(exclude_none=True),
        notes=body.notes,
        diagnosis=body.diagnosis,
        follow_up_date=body.follow_up_date,
    )
    db.add(visit)
    await db.commit()
    await db.refresh(visit)
    return await _visit_out(db, visit)


@router.get("/patients/{patient_id}/visits", response_model=list[VisitOut])
async def list_visits(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[VisitOut]:
    await authorize_clinical_access(db, user, patient_id)
    visits = (
        await db.execute(
            select(Visit)
            .where(Visit.patient_id == patient_id, Visit.deleted_at.is_(None))
            .order_by(Visit.created_at.desc())
        )
    ).scalars()
    return [await _visit_out(db, v) for v in visits]


@router.get("/visits/{visit_id}", response_model=VisitOut)
async def get_visit(
    visit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> VisitOut:
    return await _visit_out(db, await authorize_visit(db, user, visit_id))


@router.patch("/visits/{visit_id}", response_model=VisitOut)
async def update_visit(
    visit_id: uuid.UUID,
    body: VisitUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor")),
) -> VisitOut:
    visit = await authorize_visit(db, user, visit_id, write=True)
    changes = body.model_dump(exclude_unset=True)
    if "vitals" in changes and body.vitals is not None:
        changes["vitals"] = body.vitals.model_dump(exclude_none=True)
    visit.version = await snapshot(db, "visit", visit, VISIT_COLUMNS, user)
    for k, v in changes.items():
        setattr(visit, k, v)
    await db.commit()
    await db.refresh(visit)
    return await _visit_out(db, visit)


@router.delete("/visits/{visit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_visit(
    visit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor")),
) -> Response:
    visit = await authorize_visit(db, user, visit_id, write=True)
    visit.version = await snapshot(db, "visit", visit, VISIT_COLUMNS, user)
    visit.deleted_at = datetime.now(UTC)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/visits/{visit_id}/versions", response_model=list[VersionOut])
async def visit_versions(
    visit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor")),
) -> list[RecordVersion]:
    await authorize_visit(db, user, visit_id)
    rows = (
        await db.execute(
            select(RecordVersion)
            .where(RecordVersion.entity_type == "visit", RecordVersion.entity_id == visit_id)
            .order_by(RecordVersion.version)
        )
    ).scalars()
    return list(rows)


@router.post(
    "/visits/{visit_id}/prescriptions",
    response_model=PrescriptionOut,
    status_code=status.HTTP_201_CREATED,
)
async def add_prescription(
    visit_id: uuid.UUID,
    body: PrescriptionIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor")),
) -> Prescription:
    await authorize_visit(db, user, visit_id, write=True)
    rx = Prescription(visit_id=visit_id, **body.model_dump())
    db.add(rx)
    await db.commit()
    await db.refresh(rx)
    return rx


async def _get_rx(db: AsyncSession, user: User, rx_id: uuid.UUID) -> Prescription:
    rx = (
        await db.execute(
            select(Prescription).where(Prescription.id == rx_id, Prescription.deleted_at.is_(None))
        )
    ).scalar_one_or_none()
    if rx is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Prescription not found")
    await authorize_visit(db, user, rx.visit_id, write=True)
    return rx


@router.patch("/prescriptions/{rx_id}", response_model=PrescriptionOut)
async def update_prescription(
    rx_id: uuid.UUID,
    body: PrescriptionIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor")),
) -> Prescription:
    rx = await _get_rx(db, user, rx_id)
    await snapshot(db, "prescription", rx, RX_COLUMNS, user)
    for k, v in body.model_dump().items():
        setattr(rx, k, v)
    await db.commit()
    await db.refresh(rx)
    return rx


@router.delete("/prescriptions/{rx_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prescription(
    rx_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor")),
) -> Response:
    rx = await _get_rx(db, user, rx_id)
    await snapshot(db, "prescription", rx, RX_COLUMNS, user)
    rx.deleted_at = datetime.now(UTC)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
