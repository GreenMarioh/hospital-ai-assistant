"""Natural-language booking assistant. Tools are read-only; booking needs explicit user confirmation."""

import json
import uuid
from collections.abc import Callable
from datetime import UTC, date, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LLM
from app.ai.errors import AIUnavailable
from app.ai.guards import DISCLAIMER, sanitize_reply
from app.ai.pii import scrub
from app.ai.prompts import load_prompt
from app.models import AIConversation, AIMessage, Appointment, Department, Doctor, Patient, User
from app.schemas.ai import BookingChatOut, BookingProposal
from app.services import scheduling as sched

MAX_TOOL_ROUNDS = 6
MAX_SLOTS_RETURNED = 20

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_doctors",
        "description": "List doctors, optionally filtered by department name or specialization text.",
        "input_schema": {
            "type": "object",
            "properties": {
                "department": {"type": "string", "description": "Department name, e.g. Cardiology"},
                "specialization": {"type": "string"},
            },
        },
    },
    {
        "name": "get_available_slots",
        "description": "Free appointment slots for one doctor between two dates (inclusive, max 14 days).",
        "input_schema": {
            "type": "object",
            "properties": {
                "doctor_id": {"type": "string"},
                "date_from": {"type": "string", "description": "YYYY-MM-DD"},
                "date_to": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["doctor_id", "date_from", "date_to"],
        },
    },
    {
        "name": "propose_booking",
        "description": (
            "Show the patient a booking confirmation card for a specific slot. This does NOT book; "
            "the patient must confirm."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "doctor_id": {"type": "string"},
                "starts_at": {
                    "type": "string",
                    "description": "ISO 8601 start time of an available slot",
                },
                "reason": {
                    "type": "string",
                    "description": "Short reason for visit, no medical detail needed",
                },
            },
            "required": ["doctor_id", "starts_at"],
        },
    },
]


def _parse_uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


async def _doctor_name(db: AsyncSession, doctor: Doctor) -> str:
    user = await db.get(User, doctor.user_id)
    return user.full_name if user else "Doctor"


async def run_tool(
    db: AsyncSession, name: str, args: dict[str, Any], proposals: dict[str, Any]
) -> Any:
    tz = sched.hospital_tz()
    if name == "search_doctors":
        stmt = (
            select(Doctor, Department)
            .join(Department, Doctor.department_id == Department.id)
            .where(Doctor.deleted_at.is_(None))
        )
        if args.get("department"):
            stmt = stmt.where(Department.name.ilike(f"%{args['department']}%"))
        if args.get("specialization"):
            stmt = stmt.where(Doctor.specialization.ilike(f"%{args['specialization']}%"))
        rows = (await db.execute(stmt.limit(20))).all()
        return [
            {
                "doctor_id": str(d.id),
                "name": await _doctor_name(db, d),
                "department": dept.name,
                "specialization": d.specialization,
            }
            for d, dept in rows
        ]
    if name == "get_available_slots":
        doc_id = _parse_uuid(args.get("doctor_id"))
        try:
            d_from, d_to = date.fromisoformat(args["date_from"]), date.fromisoformat(
                args["date_to"]
            )
        except (KeyError, ValueError):
            return {"error": "date_from and date_to must be YYYY-MM-DD"}
        if doc_id is None or d_to < d_from or (d_to - d_from).days > 14:
            return {"error": "invalid doctor_id or date range (max 14 days)"}
        doctor = await db.get(Doctor, doc_id)
        if doctor is None or doctor.deleted_at is not None:
            return {"error": "doctor not found"}
        slots = await sched.free_slots(db, doctor, d_from, d_to)
        return {
            "timezone": str(tz),
            "slots": [s.astimezone(tz).isoformat() for s, _ in slots[:MAX_SLOTS_RETURNED]],
            "more_available": len(slots) > MAX_SLOTS_RETURNED,
        }
    if name == "propose_booking":
        doc_id = _parse_uuid(args.get("doctor_id"))
        try:
            start = datetime.fromisoformat(str(args.get("starts_at")))
        except ValueError:
            return {"error": "starts_at must be ISO 8601"}
        if start.tzinfo is None:
            start = start.replace(tzinfo=tz)
        doctor = await db.get(Doctor, doc_id) if doc_id else None
        if doctor is None or doctor.deleted_at is not None:
            return {"error": "doctor not found"}
        day = sched.local_date(start)
        free = {s for s, _ in await sched.free_slots(db, doctor, day, day)}
        if start.astimezone(UTC) not in free:
            return {"error": "that slot is not available; pick one returned by get_available_slots"}
        pid = uuid.uuid4().hex
        proposals[pid] = {
            "doctor_id": str(doctor.id),
            "doctor_name": await _doctor_name(db, doctor),
            "starts_at": start.astimezone(UTC).isoformat(),
            "reason": scrub(str(args.get("reason") or ""))[:200] or None,
            "status": "pending",
        }
        return {"status": "confirmation_card_shown_to_patient", "proposal_id": pid}
    return {"error": f"unknown tool {name}"}


async def booking_turn(
    db: AsyncSession,
    user: User,
    llm_getter: Callable[[], LLM],
    message: str,
    conversation_id: uuid.UUID | None,
    names: tuple[str, ...] = (),
) -> BookingChatOut:
    if conversation_id is None:
        conv = AIConversation(user_id=user.id, kind="booking", state={"proposals": {}})
        db.add(conv)
        await db.flush()
    else:
        found = await db.get(AIConversation, conversation_id)
        if found is None or found.user_id != user.id or found.kind != "booking":
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
        conv = found
    db.add(AIMessage(conversation_id=conv.id, role="user", content=message))
    await db.flush()

    rows = await db.execute(
        select(AIMessage).where(AIMessage.conversation_id == conv.id).order_by(AIMessage.id)
    )
    messages: list[dict[str, Any]] = [
        {
            "role": m.role,
            "content": (
                f"<patient_message>{scrub(m.content, names)}</patient_message>"
                if m.role == "user"
                else m.content
            ),
        }
        for m in rows.scalars()
    ]
    now = datetime.now(sched.hospital_tz())
    system = load_prompt("booking").render(
        today=now.date().isoformat(), weekday=now.strftime("%A"), timezone=str(sched.hospital_tz())
    )
    state = dict(conv.state or {})
    proposals: dict[str, Any] = dict(state.get("proposals", {}))
    new_proposal: str | None = None
    try:
        llm = llm_getter()
        reply = ""
        for _ in range(MAX_TOOL_ROUNDS):
            resp = await llm.complete(
                purpose="booking", system=system, messages=messages, tools=TOOLS, max_tokens=1200
            )
            if not resp.tool_uses:
                reply = resp.text.strip()
                break
            messages.append({"role": "assistant", "content": resp.raw_content})
            results = []
            for tu in resp.tool_uses:
                before = set(proposals)
                out = await run_tool(db, tu.name, tu.input, proposals)
                new_proposal = next(iter(set(proposals) - before), new_proposal)
                results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "name": tu.name,
                        "content": json.dumps(out),
                    }
                )
            messages.append({"role": "user", "content": results})
        else:
            reply = (
                "I couldn't finish that. Could you tell me the department and preferred day again?"
            )
    except AIUnavailable:
        await db.rollback()
        raise
    reply, _ = sanitize_reply(reply)
    reply = reply or "How can I help you book an appointment?"
    conv.state = {**state, "proposals": proposals}
    db.add(
        AIMessage(
            conversation_id=conv.id,
            role="assistant",
            content=reply,
            meta={"proposal": new_proposal},
        )
    )
    await db.commit()
    proposal = None
    if new_proposal:
        p = proposals[new_proposal]
        proposal = BookingProposal(
            proposal_id=new_proposal,
            doctor_id=uuid.UUID(p["doctor_id"]),
            doctor_name=p["doctor_name"],
            starts_at=p["starts_at"],
            reason=p["reason"],
        )
    return BookingChatOut(
        conversation_id=conv.id, reply=reply, proposal=proposal, disclaimer=DISCLAIMER
    )


async def confirm_booking(
    db: AsyncSession, user: User, patient: Patient, conversation_id: uuid.UUID, proposal_id: str
) -> Appointment:
    """The only path that creates an appointment from the assistant: an explicit user request."""
    conv = await db.get(AIConversation, conversation_id)
    if conv is None or conv.user_id != user.id or conv.kind != "booking":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    state = dict(conv.state or {})
    proposals = dict(state.get("proposals", {}))
    p = proposals.get(proposal_id)
    if p is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Proposal not found")
    if p["status"] != "pending":
        raise HTTPException(status.HTTP_409_CONFLICT, "Proposal already used")
    appt, _ = await sched.book(
        db,
        patient_id=patient.id,
        doctor_id=uuid.UUID(p["doctor_id"]),
        starts_at=datetime.fromisoformat(p["starts_at"]),
        reason=p["reason"],
        created_by=user.id,
        idempotency_key=f"ai:{proposal_id}",
    )
    proposals[proposal_id] = {**p, "status": "confirmed", "appointment_id": str(appt.id)}
    conv.state = {**state, "proposals": proposals}
    await db.commit()
    return appt
