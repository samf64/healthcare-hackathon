from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, EmailStr, Field

from app.models import Cadence


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    cadence: Cadence
    last_completed_date: date
    profile_data: dict[str, Any] = Field(default_factory=dict)


class UserUpdate(BaseModel):
    full_name: str | None = None
    cadence: Cadence | None = None
    last_completed_date: date | None = None
    profile_data: dict[str, Any] | None = None
    is_active: bool | None = None


class UserOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    cadence: Cadence
    last_completed_date: date
    profile_data: dict[str, Any]
    is_active: bool

    class Config:
        from_attributes = True


class ReminderRunResult(BaseModel):
    scanned_users: int
    reminders_sent: int
    failures: int


class FormGenerateRequest(BaseModel):
    profile_patch: dict[str, Any] = Field(default_factory=dict)
    is_final: bool = False


class FormGenerateResponse(BaseModel):
    generated_file: str
    generated_at: datetime


class MarkCompleteRequest(BaseModel):
    completed_on: date = Field(default_factory=date.today)

