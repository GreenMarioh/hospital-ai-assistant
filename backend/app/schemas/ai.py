import uuid
from typing import Literal

from pydantic import BaseModel, Field, model_validator

Urgency = Literal["emergency", "urgent", "routine", "self-care"]


class ChatIn(BaseModel):
    conversation_id: uuid.UUID | None = None
    message: str = Field(min_length=1, max_length=2000)


class TriageLLMOutput(BaseModel):
    reply: str = Field(min_length=1, max_length=2000)
    ready: bool
    urgency: Urgency | None = None
    department: str | None = None
    rationale: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _complete_when_ready(self) -> TriageLLMOutput:
        if self.ready and not (self.urgency and self.department and self.rationale):
            raise ValueError("urgency, department and rationale are required when ready")
        return self


class TriageResult(BaseModel):
    urgency: Urgency
    department: str | None
    rationale: str


class TriageOut(BaseModel):
    conversation_id: uuid.UUID
    reply: str
    done: bool
    result: TriageResult | None = None
    emergency: bool = False
    emergency_banner: str | None = None
    red_flags: list[str] = []
    ai_available: bool = True
    ai_generated: bool = True
    requires_clinician_review: bool = True
    disclaimer: str


class BookingProposal(BaseModel):
    proposal_id: str
    doctor_id: uuid.UUID
    doctor_name: str
    starts_at: str
    reason: str | None = None


class BookingChatOut(BaseModel):
    conversation_id: uuid.UUID
    reply: str
    proposal: BookingProposal | None = None
    disclaimer: str


class ConfirmIn(BaseModel):
    conversation_id: uuid.UUID
    proposal_id: str


class FaqIn(BaseModel):
    question: str = Field(min_length=2, max_length=500)


class FaqSource(BaseModel):
    title: str
    file: str


class FaqOut(BaseModel):
    answer: str
    sources: list[FaqSource]
    ai_generated: bool
    disclaimer: str


class BriefingLLMOutput(BaseModel):
    summary: str = Field(max_length=3000)
    key_history: list[str] = Field(default_factory=list, max_length=30)
    recent_visits: list[str] = Field(default_factory=list, max_length=30)
    flags: list[str] = Field(default_factory=list, max_length=30)


class BriefingOut(BriefingLLMOutput):
    id: uuid.UUID
    kind: str
    ai_generated: bool
    requires_clinician_review: bool = True
    prompt_version: str | None = None
    disclaimer: str
    created_at: str
