import logging

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, Patient
from app.services.email import send_email

log = logging.getLogger("app.notify")


def send_sms(phone: str, body: str) -> None:
    """SMS provider stub: replace with Twilio/SNS. Logs only, never message content with PHI."""
    log.info("sms (stub)", extra={"to_suffix": phone[-4:], "chars": len(body)})


async def notify_patient(
    db: AsyncSession, patient: Patient, *, kind: str, dedupe: str, subject: str, body: str
) -> bool:
    """Send via each available channel exactly once per dedupe key. Returns True if anything was sent."""
    sent = False
    for channel, address in (("email", patient.email), ("sms", patient.phone)):
        if not address:
            continue
        result = await db.execute(
            insert(Notification)
            .values(
                patient_id=patient.id,
                channel=channel,
                kind=kind,
                dedupe_key=f"{dedupe}:{channel}",
                payload={"subject": subject},
            )
            .on_conflict_do_nothing(index_elements=["dedupe_key"])
            .returning(Notification.id)
        )
        if result.first() is None:
            continue  # already delivered on an earlier run
        await db.commit()
        if channel == "email":
            send_email(address, subject, body)
        else:
            send_sms(address, f"{subject}: {body}")
        sent = True
    return sent
