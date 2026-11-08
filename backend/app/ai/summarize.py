"""Doctor-side summaries: pre-visit briefing and single-visit summary. Advisory, clinician-reviewed."""

import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LLM
from app.ai.errors import AIError
from app.ai.guards import DISCLAIMER
from app.ai.pii import patient_context, patient_names, scrub
from app.ai.prompts import load_prompt
from app.ai.structured import complete_json
from app.models import AISummary, Appointment, Document, Patient, Prescription, User, Visit
from app.schemas.ai import BriefingLLMOutput, BriefingOut

MAX_VISITS = 5
NOTE_CHARS = 800


async def _prescriptions(db: AsyncSession, visit_id: uuid.UUID) -> list[str]:
    rows = await db.execute(
        select(Prescription).where(
            Prescription.visit_id == visit_id, Prescription.deleted_at.is_(None)
        )
    )
    return [f"{r.drug_name} {r.dosage or ''} {r.frequency or ''}".strip() for r in rows.scalars()]


async def _visit_dict(db: AsyncSession, v: Visit, names: tuple[str, ...]) -> dict[str, Any]:
    return {
        "date": v.created_at.date().isoformat(),
        "chief_complaint": scrub(v.chief_complaint, names),
        "vitals": v.vitals or {},
        "notes": scrub(v.notes, names)[:NOTE_CHARS],
        "diagnosis": scrub(v.diagnosis, names),
        "follow_up_date": v.follow_up_date.isoformat() if v.follow_up_date else None,
        "prescriptions": [scrub(p, names) for p in await _prescriptions(db, v.id)],
    }


def rule_flags(
    patient: Patient, visits: list[dict[str, Any]], today: datetime | None = None
) -> list[str]:
    """Deterministic flags, computed without the LLM so they are always present."""
    flags: list[str] = []
    today_d = (today or datetime.now(UTC)).date()
    if patient.allergies:
        flags.append(f"Documented allergies: {', '.join(patient.allergies)}")
    if visits:
        latest = visits[0]
        fu = latest.get("follow_up_date")
        if fu and fu < today_d.isoformat():
            flags.append(f"Follow-up date {fu} from the last visit has passed")
    complaints = [v["chief_complaint"].strip().lower() for v in visits if v.get("chief_complaint")]
    for c in set(complaints):
        if complaints.count(c) >= 2:
            flags.append(f"Repeated complaint across visits: {c[:80]}")
    for v in visits:
        vit = v.get("vitals") or {}
        if vit.get("spo2") is not None and vit["spo2"] < 92:
            flags.append(f"Low SpO2 ({vit['spo2']}%) recorded on {v['date']}")
        if vit.get("systolic_bp") is not None and vit["systolic_bp"] >= 180:
            flags.append(f"Very high systolic BP ({vit['systolic_bp']}) recorded on {v['date']}")
    return flags


def _fallback(patient: Patient, visits: list[dict[str, Any]]) -> BriefingLLMOutput:
    recent = [
        f"{v['date']}: {v['chief_complaint'] or 'no complaint recorded'}"
        + (f" / {v['diagnosis']}" if v["diagnosis"] else "")
        for v in visits
    ]
    return BriefingLLMOutput(
        summary=f"AI summary unavailable. {len(visits)} recent visit(s) on record; structured overview below.",
        key_history=[],
        recent_visits=recent,
        flags=[],
    )


async def _persist(
    db: AsyncSession,
    doctor_user: User,
    patient: Patient,
    kind: str,
    visit_id: uuid.UUID | None,
    out: BriefingLLMOutput,
    ai: bool,
    model: str | None,
    version: str | None,
) -> BriefingOut:
    row = AISummary(
        patient_id=patient.id,
        visit_id=visit_id,
        kind=kind,
        content={**out.model_dump(), "ai_generated": ai},
        model=model,
        prompt_version=version,
        created_by=doctor_user.id,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return to_out(row)


def to_out(row: AISummary) -> BriefingOut:
    c = row.content
    return BriefingOut(
        id=row.id,
        kind=row.kind,
        summary=c.get("summary", ""),
        key_history=c.get("key_history", []),
        recent_visits=c.get("recent_visits", []),
        flags=c.get("flags", []),
        ai_generated=bool(c.get("ai_generated")),
        prompt_version=row.prompt_version,
        disclaimer=DISCLAIMER,
        created_at=row.created_at.isoformat(),
    )


async def _run(
    llm_getter: Callable[[], LLM], prompt_name: str, record: dict[str, Any], purpose: str
) -> tuple[BriefingLLMOutput | None, str | None, str | None]:
    try:
        llm = llm_getter()
        prompt = load_prompt(prompt_name)
        out, resp = await complete_json(
            llm,
            BriefingLLMOutput,
            purpose=purpose,
            system=prompt.render(),
            messages=[{"role": "user", "content": f"<record>\n{record}\n</record>"}],
            max_tokens=1500,
        )
        return out, resp.model or getattr(llm, "model", None), prompt.version
    except AIError:
        return None, None, None


async def briefing(
    db: AsyncSession, doctor_user: User, patient: Patient, llm_getter: Callable[[], LLM]
) -> BriefingOut:
    names = patient_names(patient)
    rows = await db.execute(
        select(Visit)
        .where(Visit.patient_id == patient.id, Visit.deleted_at.is_(None))
        .order_by(Visit.created_at.desc())
        .limit(MAX_VISITS)
    )
    visits = [await _visit_dict(db, v, names) for v in rows.scalars()]
    upcoming = (
        await db.execute(
            select(Appointment)
            .where(
                Appointment.patient_id == patient.id,
                Appointment.status == "booked",
                Appointment.starts_at > datetime.now(UTC),
            )
            .order_by(Appointment.starts_at)
            .limit(1)
        )
    ).scalar_one_or_none()
    doc_types = [
        d.doc_type
        for d in (
            await db.execute(
                select(Document).where(
                    Document.patient_id == patient.id, Document.deleted_at.is_(None)
                )
            )
        ).scalars()
    ]
    record = {
        "patient": patient_context(patient, include_allergies=True),
        "recent_visits": visits,
        "upcoming_appointment_reason": scrub(upcoming.reason, names) if upcoming else None,
        "document_types_on_file": doc_types,
    }
    flags = rule_flags(patient, visits)
    out, model, version = await _run(llm_getter, "summary_briefing", record, "briefing")
    ai = out is not None
    out = out or _fallback(patient, visits)
    merged = list(dict.fromkeys([*flags, *out.flags]))
    out = out.model_copy(update={"flags": merged})
    return await _persist(db, doctor_user, patient, "briefing", None, out, ai, model, version)


async def visit_summary(
    db: AsyncSession,
    doctor_user: User,
    patient: Patient,
    visit: Visit,
    llm_getter: Callable[[], LLM],
) -> BriefingOut:
    names = patient_names(patient)
    v = await _visit_dict(db, visit, names)
    record = {"patient": patient_context(patient, include_allergies=True), "visit": v}
    flags = rule_flags(patient, [v])
    out, model, version = await _run(llm_getter, "summary_visit", record, "visit_summary")
    ai = out is not None
    out = out or BriefingLLMOutput(
        summary="AI summary unavailable for this visit.",
        key_history=[],
        recent_visits=[f"{v['date']}: {v['chief_complaint']}"],
        flags=[],
    )
    out = out.model_copy(update={"flags": list(dict.fromkeys([*flags, *out.flags]))})
    return await _persist(db, doctor_user, patient, "visit", visit.id, out, ai, model, version)
