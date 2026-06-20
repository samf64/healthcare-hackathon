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

