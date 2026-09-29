import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

BLOOD = "^(A|B|AB|O)[+-]$"


class PatientBase(BaseModel):
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    sex: str | None = Field(default=None, max_length=16)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=1000)
    emergency_contact_name: str | None = Field(default=None, max_length=200)
    emergency_contact_phone: str | None = Field(default=None, max_length=32)
    insurance_provider: str | None = Field(default=None, max_length=200)
    allergies: list[str] = Field(default_factory=list, max_length=50)
    blood_group: str | None = Field(default=None, pattern=BLOOD)


class PatientCreate(PatientBase):
    insurance_id: str | None = Field(default=None, max_length=64)


class PatientUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    date_of_birth: date | None = None
    sex: str | None = Field(default=None, max_length=16)
    phone: str | None = Field(default=None, max_length=32)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=1000)
    emergency_contact_name: str | None = Field(default=None, max_length=200)
    emergency_contact_phone: str | None = Field(default=None, max_length=32)
    insurance_provider: str | None = Field(default=None, max_length=200)
    insurance_id: str | None = Field(default=None, max_length=64)
    allergies: list[str] | None = Field(default=None, max_length=50)
    blood_group: str | None = Field(default=None, pattern=BLOOD)


class PatientOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    date_of_birth: date
    sex: str | None = None
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    emergency_contact_name: str | None = None
    emergency_contact_phone: str | None = None
    insurance_provider: str | None = None
    insurance_id_masked: str | None = None
    allergies: list[str] = []
    blood_group: str | None = None


class PatientPage(BaseModel):
    items: list[PatientOut]
    total: int
    page: int
    size: int


class TimelineEvent(BaseModel):
    kind: str  # appointment | visit | document | ai_summary
    id: uuid.UUID
    at: datetime
    title: str
    detail: str | None = None
