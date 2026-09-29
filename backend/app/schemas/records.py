import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class Vitals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    temperature_c: float | None = Field(default=None, ge=25, le=45)
    heart_rate: int | None = Field(default=None, ge=20, le=300)
    systolic_bp: int | None = Field(default=None, ge=40, le=300)
    diastolic_bp: int | None = Field(default=None, ge=20, le=200)
    spo2: int | None = Field(default=None, ge=30, le=100)
    weight_kg: float | None = Field(default=None, ge=0.3, le=500)
    height_cm: float | None = Field(default=None, ge=20, le=280)


class PrescriptionIn(BaseModel):
    drug_name: str = Field(min_length=1, max_length=200)
    dosage: str | None = Field(default=None, max_length=100)
    frequency: str | None = Field(default=None, max_length=100)
    duration: str | None = Field(default=None, max_length=100)
    instructions: str | None = Field(default=None, max_length=2000)


class PrescriptionOut(PrescriptionIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    visit_id: uuid.UUID


class VisitIn(BaseModel):
    appointment_id: uuid.UUID | None = None
    chief_complaint: str | None = Field(default=None, max_length=4000)
    vitals: Vitals = Field(default_factory=Vitals)
    notes: str | None = Field(default=None, max_length=20000)
    diagnosis: str | None = Field(default=None, max_length=4000)
    follow_up_date: date | None = None


class VisitUpdate(BaseModel):
    chief_complaint: str | None = Field(default=None, max_length=4000)
    vitals: Vitals | None = None
    notes: str | None = Field(default=None, max_length=20000)
    diagnosis: str | None = Field(default=None, max_length=4000)
    follow_up_date: date | None = None


class VisitOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    appointment_id: uuid.UUID | None
    chief_complaint: str | None
    vitals: dict
    notes: str | None
    diagnosis: str | None
    follow_up_date: date | None
    version: int
    created_at: datetime
    updated_at: datetime
    prescriptions: list[PrescriptionOut] = []


class VersionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    version: int
    data: dict
    changed_by: uuid.UUID | None
    changed_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    visit_id: uuid.UUID | None
    doc_type: str
    filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class SignedLink(BaseModel):
    url: str
    expires_in: int


class SearchHit(BaseModel):
    visit_id: uuid.UUID
    patient_id: uuid.UUID
    snippet: str
    rank: float
