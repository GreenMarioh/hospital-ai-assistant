import uuid
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models import (
    Appointment,
    AvailabilityException,
    Doctor,
    DoctorAvailability,
    Notification,
    Patient,
    WaitlistEntry,
)
from app.services.notify import notify_patient

ACTIVE = ("booked", "completed")
MAX_LOOKAHEAD_DAYS = 180
MAX_RANGE_DAYS = 31


def hospital_tz() -> ZoneInfo:
    return ZoneInfo(get_settings().hospital_timezone)


def local_date(dt: datetime) -> date:
    return dt.astimezone(hospital_tz()).date()


async def _day_slots(
    db: AsyncSession, doctor: Doctor, day: date, templates: list[DoctorAvailability],
    blocked: list[AvailabilityException],
) -> list[tuple[datetime, datetime]]:  # fmt: skip
    if any(e.start_date <= day <= e.end_date for e in blocked):
        return []
    tz = hospital_tz()
    step = timedelta(minutes=doctor.slot_minutes)
    out: list[tuple[datetime, datetime]] = []
    for t in templates:
        if t.weekday != day.weekday():
            continue
        cur = datetime.combine(day, t.start_time, tzinfo=tz)
        end = datetime.combine(day, t.end_time, tzinfo=tz)
        while cur + step <= end:
            out.append((cur.astimezone(UTC), (cur + step).astimezone(UTC)))
            cur += step
    return sorted(set(out))


async def free_slots(
    db: AsyncSession, doctor: Doctor, start: date, end: date
) -> list[tuple[datetime, datetime]]:
    templates = list(
        (
            await db.execute(
                select(DoctorAvailability).where(DoctorAvailability.doctor_id == doctor.id)
            )
        ).scalars()
    )
    blocked = list(
        (
            await db.execute(
                select(AvailabilityException).where(
                    AvailabilityException.doctor_id == doctor.id,
                    AvailabilityException.end_date >= start,
                    AvailabilityException.start_date <= end,
                )
            )
        ).scalars()
    )
    tz = hospital_tz()
    lo = datetime.combine(start, time.min, tzinfo=tz).astimezone(UTC)
    hi = datetime.combine(end + timedelta(days=1), time.min, tzinfo=tz).astimezone(UTC)
    taken = {
        a.starts_at
        for a in (
            await db.execute(
                select(Appointment).where(
                    Appointment.doctor_id == doctor.id,
                    Appointment.status.in_(ACTIVE),
                    Appointment.starts_at >= lo,
                    Appointment.starts_at < hi,
                )
            )
        ).scalars()
    }
    now = datetime.now(UTC)
    slots: list[tuple[datetime, datetime]] = []
    day = start
    while day <= end:
        for s, e in await _day_slots(db, doctor, day, templates, blocked):
            if s > now and s not in taken:
                slots.append((s, e))
        day += timedelta(days=1)
    return slots


async def _lock_doctor(db: AsyncSession, doctor_id: uuid.UUID) -> Doctor:
    """Row lock serializes concurrent bookings for one doctor; the DB exclusion constraint
    remains the final guarantee against double booking."""
    doctor = (
        await db.execute(
            select(Doctor)
            .where(Doctor.id == doctor_id, Doctor.deleted_at.is_(None))
            .with_for_update()
        )
    ).scalar_one_or_none()
    if doctor is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Doctor not found")
    return doctor


async def _require_free_slot(db: AsyncSession, doctor: Doctor, starts_at: datetime) -> datetime:
    now = datetime.now(UTC)
    if starts_at <= now or starts_at > now + timedelta(days=MAX_LOOKAHEAD_DAYS):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Slot outside bookable window")
    day = local_date(starts_at)
    slots = dict(await free_slots(db, doctor, day, day))
    ends_at = slots.get(starts_at.astimezone(UTC))
    if ends_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot is not available")
    return ends_at


async def book(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    doctor_id: uuid.UUID,
    starts_at: datetime,
    reason: str | None,
    created_by: uuid.UUID,
    idempotency_key: str | None,
) -> tuple[Appointment, bool]:
    """Returns (appointment, created). A repeated idempotency key returns the original booking."""
    if idempotency_key:
        existing = (
            await db.execute(
                select(Appointment).where(
                    Appointment.created_by == created_by,
                    Appointment.idempotency_key == idempotency_key,
                )
            )
        ).scalar_one_or_none()
        if existing:
            return existing, False
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient not found")
    doctor = await _lock_doctor(db, doctor_id)
    ends_at = await _require_free_slot(db, doctor, starts_at)
    appt = Appointment(
        patient_id=patient_id,
        doctor_id=doctor_id,
        starts_at=starts_at.astimezone(UTC),
        ends_at=ends_at,
        reason=reason,
        created_by=created_by,
        idempotency_key=idempotency_key,
    )
    db.add(appt)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot is not available") from None
    # A booked patient no longer needs a waitlist place with this doctor.
    waits = (
        await db.execute(
            select(WaitlistEntry).where(
                WaitlistEntry.patient_id == patient_id,
                WaitlistEntry.doctor_id == doctor_id,
                WaitlistEntry.status.in_(("waiting", "notified")),
            )
        )
    ).scalars()
    for w in waits:
        w.status = "fulfilled"
    await db.commit()
    await db.refresh(appt)
    return appt, True


async def reschedule(db: AsyncSession, appt: Appointment, new_start: datetime) -> Appointment:
    if appt.status != "booked":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only booked appointments can be rescheduled")
    doctor = await _lock_doctor(db, appt.doctor_id)
    ends_at = await _require_free_slot(db, doctor, new_start)
    old_start = appt.starts_at
    appt.starts_at, appt.ends_at = new_start.astimezone(UTC), ends_at
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Slot is not available") from None
    await db.commit()
    await db.refresh(appt)
    await _offer_freed_slot(db, appt.doctor_id, old_start, appt.id)
    return appt


async def cancel(db: AsyncSession, appt: Appointment) -> Appointment:
    if appt.status != "booked":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only booked appointments can be cancelled")
    appt.status = "cancelled"
    await db.commit()
    await _offer_freed_slot(db, appt.doctor_id, appt.starts_at, appt.id)
    return appt


async def set_outcome(db: AsyncSession, appt: Appointment, outcome: str) -> Appointment:
    if appt.status != "booked":
        raise HTTPException(status.HTTP_409_CONFLICT, "Appointment is not in a booked state")
    if appt.starts_at > datetime.now(UTC) + timedelta(hours=1):
        raise HTTPException(status.HTTP_409_CONFLICT, "Appointment has not started yet")
    appt.status = outcome
    await db.commit()
    return appt


async def _offer_freed_slot(
    db: AsyncSession, doctor_id: uuid.UUID, freed_start: datetime, appt_id: uuid.UUID
) -> None:
    """Notify the longest-waiting patient for that doctor and date (waitlist)."""
    if freed_start <= datetime.now(UTC):
        return
    entry = (
        await db.execute(
            select(WaitlistEntry)
            .where(
                WaitlistEntry.doctor_id == doctor_id,
                WaitlistEntry.desired_date == local_date(freed_start),
                WaitlistEntry.status == "waiting",
            )
            .order_by(WaitlistEntry.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
    ).scalar_one_or_none()
    if entry is None:
        return
    patient = await db.get(Patient, entry.patient_id)
    doctor = await db.get(Doctor, doctor_id)
    if patient is None or doctor is None:
        return
    when = freed_start.astimezone(hospital_tz()).strftime("%a %d %b %H:%M")
    sent = await notify_patient(
        db,
        patient,
        kind="waitlist_slot",
        dedupe=f"waitlist:{entry.id}:{appt_id}",
        subject="A slot has opened up",
        body=f"A slot at {when} is now available. Log in to book it before someone else does.",
    )
    if sent:
        entry.status = "notified"
    await db.commit()


__all__ = [
    "Notification",
    "book",
    "cancel",
    "free_slots",
    "hospital_tz",
    "local_date",
    "reschedule",
    "set_outcome",
]
