import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import booking, faq, summarize, triage
from app.ai.client import ai_configured, get_llm
from app.ai.errors import AIUnavailable
from app.ai.pii import patient_names
from app.core.db import get_db
from app.core.deps import get_current_user, require_roles
from app.core.ratelimit import limiter
from app.models import AISummary, Appointment, Patient, User
from app.schemas.ai import BookingChatOut, BriefingOut, ChatIn, ConfirmIn, FaqIn, FaqOut, TriageOut
from app.schemas.scheduling import AppointmentOut
from app.services.access import authorize_clinical_access, authorize_visit, get_patient_for_user

router = APIRouter(prefix="/api/ai", tags=["ai"])
AI_LIMIT = "30/minute"


async def _own_patient(db: AsyncSession, user: User) -> Patient:
    patient = await get_patient_for_user(db, user)
    if patient is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Patient profile not found")
    return patient


@router.get("/status")
async def ai_status(_: User = Depends(get_current_user)) -> dict[str, bool]:
    return {"available": ai_configured()}


@router.post("/triage/message", response_model=TriageOut)
@limiter.limit(AI_LIMIT)
async def triage_message(
    request: Request,
    body: ChatIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("patient")),
) -> TriageOut:
    patient = await _own_patient(db, user)
    return await triage.triage_turn(db, user, patient, get_llm, body.message, body.conversation_id)


@router.post("/booking/message", response_model=BookingChatOut)
@limiter.limit(AI_LIMIT)
async def booking_message(
    request: Request,
    body: ChatIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("patient")),
) -> BookingChatOut:
    patient = await _own_patient(db, user)
    try:
        return await booking.booking_turn(
            db, user, get_llm, body.message, body.conversation_id, patient_names(patient)
        )
    except AIUnavailable:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "The booking assistant is unavailable. You can book from the Appointments page.",
        ) from None


@router.post("/booking/confirm", response_model=AppointmentOut, status_code=status.HTTP_201_CREATED)
async def booking_confirm(
    body: ConfirmIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("patient")),
) -> Appointment:
    patient = await _own_patient(db, user)
    return await booking.confirm_booking(db, user, patient, body.conversation_id, body.proposal_id)


@router.post("/faq", response_model=FaqOut)
@limiter.limit(AI_LIMIT)
async def faq_ask(request: Request, body: FaqIn, _: User = Depends(get_current_user)) -> FaqOut:
    return await faq.answer(get_llm, body.question)


@router.post("/patients/{patient_id}/briefing", response_model=BriefingOut)
@limiter.limit(AI_LIMIT)
async def patient_briefing(
    request: Request,
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor")),
) -> BriefingOut:
    patient = await authorize_clinical_access(db, user, patient_id)
    return await summarize.briefing(db, user, patient, get_llm)


@router.post("/visits/{visit_id}/summary", response_model=BriefingOut)
@limiter.limit(AI_LIMIT)
async def visit_summary(
    request: Request,
    visit_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor")),
) -> BriefingOut:
    visit = await authorize_visit(db, user, visit_id)
    patient = await authorize_clinical_access(db, user, visit.patient_id)
    return await summarize.visit_summary(db, user, patient, visit, get_llm)


@router.get("/patients/{patient_id}/summaries", response_model=list[BriefingOut])
async def list_summaries(
    patient_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_roles("doctor")),
) -> list[BriefingOut]:
    await authorize_clinical_access(db, user, patient_id)
    rows = await db.execute(
        select(AISummary)
        .where(AISummary.patient_id == patient_id)
        .order_by(AISummary.created_at.desc())
        .limit(20)
    )
    return [summarize.to_out(r) for r in rows.scalars()]
