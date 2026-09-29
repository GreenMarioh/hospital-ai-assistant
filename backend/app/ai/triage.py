"""Symptom intake + triage. Rule-based red flags run first and cannot be overridden by the LLM."""

import uuid
from collections.abc import Callable

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import LLM
from app.ai.errors import AIError, AIUnavailable
from app.ai.guards import DISCLAIMER, sanitize_reply
from app.ai.pii import patient_context, patient_names, scrub
from app.ai.prompts import load_prompt
from app.ai.redflags import EMERGENCY_BANNER, detect_red_flags
from app.ai.structured import complete_json
from app.models import AIConversation, AIMessage, Department, Patient, User
from app.schemas.ai import TriageLLMOutput, TriageOut, TriageResult

MAX_TURNS = 8
FALLBACK_DEPARTMENT = "General Medicine"
UNAVAILABLE_REPLY = (
    "The symptom assistant is not available right now. You can still book an appointment directly "
    "from the Appointments page or contact the front desk. If this is an emergency, call your local "
    "emergency number."
)


def _out(conv_id: uuid.UUID, reply: str, **kw) -> TriageOut:  # type: ignore[no-untyped-def]
    return TriageOut(conversation_id=conv_id, reply=reply, disclaimer=DISCLAIMER, **kw)


async def _load_conversation(
    db: AsyncSession, user: User, conversation_id: uuid.UUID | None
) -> AIConversation:
    if conversation_id is None:
        conv = AIConversation(user_id=user.id, kind="triage", state={"turns": 0})
        db.add(conv)
        await db.flush()
        return conv
    found = await db.get(AIConversation, conversation_id)
    if found is None or found.user_id != user.id or found.kind != "triage":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conversation not found")
    return found


async def _history(db: AsyncSession, conv_id: uuid.UUID) -> list[AIMessage]:
    rows = await db.execute(
        select(AIMessage).where(AIMessage.conversation_id == conv_id).order_by(AIMessage.id)
    )
    return list(rows.scalars())


def _emergency_out(conv: AIConversation, flags: list[str]) -> TriageOut:
    return _out(
        conv.id,
        EMERGENCY_BANNER,
        done=True,
        emergency=True,
        emergency_banner=EMERGENCY_BANNER,
        red_flags=flags,
        ai_generated=False,
        requires_clinician_review=True,
        result=TriageResult(
            urgency="emergency",
            department="Emergency",
            rationale="Symptoms you described match emergency warning signs.",
        ),
    )


async def triage_turn(
    db: AsyncSession,
    user: User,
    patient: Patient,
    llm_getter: Callable[[], LLM],
    message: str,
    conversation_id: uuid.UUID | None,
) -> TriageOut:
    conv = await _load_conversation(db, user, conversation_id)
    state = dict(conv.state or {})
    if state.get("done") and not state.get("emergency"):
        raise HTTPException(status.HTTP_409_CONFLICT, "Triage complete; start a new conversation")

    db.add(AIMessage(conversation_id=conv.id, role="user", content=message))
    await db.flush()

    # 1) Deterministic red-flag check: independent of the LLM and sticky for the conversation.
    flags = [f.label for f in detect_red_flags(message)]
    if flags or state.get("emergency"):
        all_flags = sorted(set(flags) | set(state.get("flags", [])))
        conv.state = {**state, "emergency": True, "flags": all_flags, "done": True}
        db.add(
            AIMessage(
                conversation_id=conv.id,
                role="assistant",
                content=EMERGENCY_BANNER,
                meta={"source": "rules", "red_flags": all_flags},
            )
        )
        await db.commit()
        return _emergency_out(conv, all_flags)

    # 2) LLM-assisted intake, with graceful degradation.
    turns = int(state.get("turns", 0)) + 1
    history = await _history(db, conv.id)
    messages = [
        {
            "role": m.role,
            "content": (
                f"<patient_message>{scrub(m.content, patient_names(patient))}</patient_message>"
                if m.role == "user"
                else m.content
            ),
        }
        for m in history
    ]
    depts = [
        d.name for d in (await db.execute(select(Department).order_by(Department.name))).scalars()
    ]
    try:
        llm = llm_getter()
        prompt = load_prompt("triage")
        system = prompt.render(
            max_turns=str(MAX_TURNS),
            patient_context=str(patient_context(patient)),
            departments=", ".join(depts),
        )
        if turns >= MAX_TURNS:
            system += "\nThis is the final turn: you must finish now with ready=true."
        parsed, resp = await complete_json(
            llm, TriageLLMOutput, purpose="triage", system=system, messages=messages, max_tokens=800
        )
    except AIError as exc:
        conv.state = {**state, "turns": turns}
        reason = "unavailable" if isinstance(exc, AIUnavailable) else "invalid_output"
        db.add(
            AIMessage(
                conversation_id=conv.id,
                role="assistant",
                content=UNAVAILABLE_REPLY,
                meta={"source": "fallback", "reason": reason},
            )
        )
        await db.commit()
        return _out(conv.id, UNAVAILABLE_REPLY, done=False, ai_available=False, ai_generated=False)

    reply, replaced = sanitize_reply(parsed.reply)
    ready, result = parsed.ready, None
    if not ready and turns >= MAX_TURNS:
        parsed = TriageLLMOutput(
            reply=reply,
            ready=True,
            urgency="urgent",
            department=FALLBACK_DEPARTMENT,
            rationale="Triage could not be completed; a clinician should review you soon.",
        )
        ready = True
    emergency = False
    if ready and parsed.urgency and parsed.department and parsed.rationale:
        dept = next((d for d in depts if d.lower() == parsed.department.lower()), None)
        dept = dept or (FALLBACK_DEPARTMENT if FALLBACK_DEPARTMENT in depts else None)
        rationale, _ = sanitize_reply(parsed.rationale)
        result = TriageResult(urgency=parsed.urgency, department=dept, rationale=rationale)
        emergency = parsed.urgency == "emergency"

    new_state = {**state, "turns": turns, "done": ready}
    if emergency:
        new_state["emergency"] = True
    conv.state = new_state
    db.add(
        AIMessage(
            conversation_id=conv.id,
            role="assistant",
            content=reply,
            meta={
                "source": "llm",
                "prompt_version": load_prompt("triage").version,
                "input_tokens": resp.input_tokens,
                "output_tokens": resp.output_tokens,
                "latency_ms": round(resp.latency_ms, 1),
                "guard_replaced": replaced,
                "result": result.model_dump() if result else None,
            },
        )
    )
    await db.commit()
    return _out(
        conv.id,
        reply,
        done=ready,
        result=result,
        emergency=emergency,
        emergency_banner=EMERGENCY_BANNER if emergency else None,
    )
