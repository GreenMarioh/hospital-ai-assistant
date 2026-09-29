import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment, Patient
from app.services.notify import notify_patient
from app.services.scheduling import hospital_tz

log = logging.getLogger("app.jobs.reminders")


def reminder_kind(now: datetime, starts_at: datetime) -> str | None:
    """'2h' inside the last two hours; '24h' from 24h out until the 2h window opens."""
    until = starts_at - now
    if timedelta(0) < until <= timedelta(hours=2):
        return "2h"
    if timedelta(hours=2) < until <= timedelta(hours=24):
        return "24h"
    return None


async def send_due_reminders(db: AsyncSession, now: datetime | None = None) -> int:
    """Idempotent: each (appointment, kind, channel) is delivered at most once (notifications.dedupe_key)."""
    now = now or datetime.now(UTC)
    rows = (
        await db.execute(
            select(Appointment).where(
                Appointment.status == "booked",
                Appointment.starts_at > now,
                Appointment.starts_at <= now + timedelta(hours=24),
            )
        )
    ).scalars()
    sent = 0
    for appt in list(rows):
        kind = reminder_kind(now, appt.starts_at)
        patient = await db.get(Patient, appt.patient_id)
        if kind is None or patient is None or patient.deleted_at is not None:
            continue
        when = appt.starts_at.astimezone(hospital_tz()).strftime("%a %d %b at %H:%M")
        ok = await notify_patient(
            db,
            patient,
            kind=f"reminder_{kind}",
            dedupe=f"reminder:{appt.id}:{kind}",
            subject="Appointment reminder",
            body=f"You have an appointment on {when}.",
        )
        sent += int(ok)
    if sent:
        log.info("reminders sent", extra={"count": sent})
    return sent
