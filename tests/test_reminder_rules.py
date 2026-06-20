from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import (
    Cadence,
    RequisitionRequest,
    RequisitionStatus,
    RequisitionTemplate,
    ReminderStage,
    UserProfile,
)
from app.services.reminders import determine_stage, next_due_date, run_daily_reminder_job


class FakeNotifier:
    def __init__(self) -> None:
        self.calls = 0

    def send_email(self, *_args, **_kwargs):
        self.calls += 1
        return True, "ok"


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_next_due_date_for_six_months():
    due = next_due_date(date(2026, 1, 31), Cadence.SIX_MONTHS)
    assert due == date(2026, 7, 31)


def test_next_due_date_for_twelve_months():
    due = next_due_date(date(2024, 2, 29), Cadence.TWELVE_MONTHS)
    assert due == date(2025, 2, 28)


def test_determine_stage():
    due = date(2026, 12, 1)
    assert determine_stage(date(2026, 11, 1), due) == ReminderStage.THIRTY_DAYS_BEFORE
    assert determine_stage(date(2026, 12, 1), due) == ReminderStage.DUE_TODAY
    assert determine_stage(date(2026, 12, 8), due) == ReminderStage.OVERDUE_7_DAYS
    assert determine_stage(date(2026, 11, 2), due) is None


def test_run_daily_reminder_job_deduplicates_same_stage():
    db = _session()
    db.add(
        UserProfile(
            full_name="Test Person",
            email="test@example.com",
            cadence=Cadence.SIX_MONTHS,
            last_completed_date=date(2026, 6, 1),
            profile_data={"patient_last_name": "Person"},
        )
    )
    db.commit()

    notifier = FakeNotifier()
    first = run_daily_reminder_job(db, notifier=notifier, today=date(2026, 11, 1))
    second = run_daily_reminder_job(db, notifier=notifier, today=date(2026, 11, 1))

    assert first.reminders_sent == 1
    assert second.reminders_sent == 0
    assert notifier.calls == 1


def test_run_daily_reminder_job_skips_disabled_reminders():
    db = _session()
    db.add(
        UserProfile(
            full_name="No Reminder",
            email="noreminder@example.com",
            cadence=Cadence.SIX_MONTHS,
            last_completed_date=date(2026, 6, 1),
            profile_data={"reminder_enabled": False},
        )
    )
    db.commit()

    notifier = FakeNotifier()
    result = run_daily_reminder_job(db, notifier=notifier, today=date(2026, 11, 1))
    assert result.scanned_users == 0
    assert result.reminders_sent == 0
    assert notifier.calls == 0
def test_requisition_models_can_store_template_and_request():
    db = _session()

    user = UserProfile(
        full_name="Jane Doe",
        email="jane@example.com",
        cadence=Cadence.SIX_MONTHS,
        last_completed_date=date(2026, 1, 1),
        profile_data={"patient_last_name": "Doe"},
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    template = RequisitionTemplate(
        name="Diabetes Blood Tests",
        description="Baseline diabetic screening panel",
        template_json={"tests": ["A1C", "Glucose", "Lipids"]},
        version=1,
        is_active=True,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    request = RequisitionRequest(
        user_id=user.id,
        template_id=template.id,
        status=RequisitionStatus.DRAFT,
        reminder_interval_days=90,
        next_reminder_at=date(2026, 4, 1),
        custom_payload={"priority": "routine"},
    )
    db.add(request)
    db.commit()
    db.refresh(request)

    assert request.id is not None
    assert request.template_id == template.id
    assert request.user_id == user.id
    assert request.status == RequisitionStatus.DRAFT
    assert request.template.name == "Diabetes Blood Tests"

