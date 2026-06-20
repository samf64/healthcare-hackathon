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


class FormTemplateOut(BaseModel):
    key: str
    title: str
    description: str
    suggested_fields: list[str]
    preview_url: str | None = None


class ReminderSubscriptionRequest(BaseModel):
    full_name: str
    email: EmailStr
    cadence: Cadence | None = None
    reminder_enabled: bool = True
    template_key: str
    last_completed_date: date = Field(default_factory=date.today)
    profile_data: dict[str, Any] = Field(default_factory=dict)


class ReminderSubscriptionOut(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    cadence: Cadence
    template_key: str
    last_completed_date: date
    reminder_enabled: bool

    class Config:
        from_attributes = True


class GenerateFromTemplateRequest(BaseModel):
    full_name: str
    email: EmailStr
    template_key: str
    cadence: Cadence | None = None
    reminder_enabled: bool = False
    last_completed_date: date = Field(default_factory=date.today)
    profile_patch: dict[str, Any] = Field(default_factory=dict)
    is_final: bool = False


class FormHistoryItem(BaseModel):
    file_path: str
    created_at: datetime
    is_final: bool


class TemplateFileOut(BaseModel):
    name: str
    preview_url: str


class FillTemplateRequest(BaseModel):
    template_name: str
    full_name: str
    email: EmailStr
    patient_last_name: str
    patient_first_name: str
    health_number: str
    date_of_birth: str
    service_date: str
    phone_number: str | None = ""
    address: str | None = ""

