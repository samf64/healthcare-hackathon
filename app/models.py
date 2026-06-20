from datetime import date, datetime
from enum import Enum

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum as SQLEnum, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Cadence(str, Enum):
    SIX_MONTHS = "6_months"
    TWELVE_MONTHS = "12_months"


class ReminderStage(str, Enum):
    THIRTY_DAYS_BEFORE = "30_days_before"
    DUE_TODAY = "due_today"
    OVERDUE_7_DAYS = "overdue_7_days"


class RequisitionStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    SENT = "sent"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ReminderEventType(str, Enum):
    SENT = "sent"
    FAILED = "failed"
    VIEWED = "viewed"
    COMPLETED = "completed"


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    cadence: Mapped[Cadence] = mapped_column(SQLEnum(Cadence), nullable=False)
    last_completed_date: Mapped[date] = mapped_column(Date, nullable=False)
    profile_data: Mapped[dict] = mapped_column(JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    reminders: Mapped[list["ReminderLog"]] = relationship(back_populates="user", cascade="all,delete")
    generated_forms: Mapped[list["GeneratedForm"]] = relationship(back_populates="user", cascade="all,delete")
    audit_events: Mapped[list["AuditLog"]] = relationship(back_populates="user", cascade="all,delete")
    requisition_requests: Mapped[list["RequisitionRequest"]] = relationship(
        back_populates="user",
        cascade="all,delete",
    )


class ReminderLog(Base):
    __tablename__ = "reminder_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    stage: Mapped[ReminderStage] = mapped_column(SQLEnum(ReminderStage), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    sent_to: Mapped[str] = mapped_column(String(255), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    details: Mapped[str] = mapped_column(String(500), default="")

    user: Mapped["UserProfile"] = relationship(back_populates="reminders")


class RequisitionTemplate(Base):
    __tablename__ = "requisition_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(String(500), default="")
    template_json: Mapped[dict] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requisition_requests: Mapped[list["RequisitionRequest"]] = relationship(
        back_populates="template",
        cascade="all,delete",
    )


class RequisitionRequest(Base):
    __tablename__ = "requisition_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    template_id: Mapped[int] = mapped_column(ForeignKey("requisition_templates.id"), index=True)
    status: Mapped[RequisitionStatus] = mapped_column(SQLEnum(RequisitionStatus), nullable=False, default=RequisitionStatus.DRAFT)
    reminder_interval_days: Mapped[int] = mapped_column(Integer, default=0)
    next_reminder_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    custom_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    notes: Mapped[str] = mapped_column(String(1000), default="")

    user: Mapped["UserProfile"] = relationship(back_populates="requisition_requests")
    template: Mapped["RequisitionTemplate"] = relationship(back_populates="requisition_requests")
    reminder_events: Mapped[list["ReminderEvent"]] = relationship(
        back_populates="requisition_request",
        cascade="all,delete",
    )


class ReminderEvent(Base):
    __tablename__ = "reminder_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requisition_request_id: Mapped[int] = mapped_column(
        ForeignKey("requisition_requests.id"),
        index=True,
    )
    event_type: Mapped[ReminderEventType] = mapped_column(
        SQLEnum(ReminderEventType),
        nullable=False,
    )
    sent_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    details: Mapped[str] = mapped_column(String(500), default="")

    requisition_request: Mapped["RequisitionRequest"] = relationship(back_populates="reminder_events")


class GeneratedForm(Base):
    __tablename__ = "generated_forms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_final: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["UserProfile"] = relationship(back_populates="generated_forms")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("user_profiles.id"), index=True)
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    details: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["UserProfile"] = relationship(back_populates="audit_events")

