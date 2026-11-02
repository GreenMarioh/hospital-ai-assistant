import uuid
from datetime import date

from pydantic import BaseModel, EmailStr, Field

Password = Field(min_length=12, max_length=128)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Password
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    date_of_birth: date
    phone: str | None = Field(default=None, max_length=32)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Password


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Password


class UserOut(BaseModel):
    id: uuid.UUID
    email: str
    full_name: str
    role: str
    is_active: bool


class AdminCreateUser(BaseModel):
    email: EmailStr
    password: str = Password
    full_name: str = Field(min_length=1, max_length=255)
    role: str = Field(pattern="^(admin|doctor|staff)$")
    department_id: int | None = None
    specialization: str | None = None
