from datetime import date

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.models import Cadence, ReminderStage, UserProfile
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

