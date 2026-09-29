import uuid
from datetime import date, datetime, time

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    description: str | None = None


class DoctorOut(BaseModel):
    id: uuid.UUID
    name: str
    department_id: int
    department: str
    specialization: str | None
    slot_minutes: int


class SlotOut(BaseModel):
    starts_at: datetime
    ends_at: datetime


class AvailabilityIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time

    @model_validator(mode="after")
    def _order(self) -> AvailabilityIn:
        if self.end_time <= self.start_time:
            raise ValueError("end_time must be after start_time")
        return self


class AvailabilityOut(AvailabilityIn):
    model_config = ConfigDict(from_attributes=True)


class SlotConfigIn(BaseModel):
    slot_minutes: int = Field(ge=5, le=240)


class ExceptionIn(BaseModel):
    start_date: date
    end_date: date
    reason: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _order(self) -> ExceptionIn:
        if self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        return self


class ExceptionOut(ExceptionIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class BookIn(BaseModel):
    doctor_id: uuid.UUID
    starts_at: AwareDatetime
    patient_id: uuid.UUID | None = None  # required for staff/admin; ignored for patients
    reason: str | None = Field(default=None, max_length=1000)


class RescheduleIn(BaseModel):
    starts_at: AwareDatetime


class AppointmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    status: str
    reason: str | None


class WaitlistIn(BaseModel):
    doctor_id: uuid.UUID
    desired_date: date
    patient_id: uuid.UUID | None = None


class WaitlistOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    patient_id: uuid.UUID
    doctor_id: uuid.UUID
    desired_date: date
    status: str
