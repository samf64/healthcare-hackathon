from dataclasses import dataclass
from datetime import date

from dateutil.relativedelta import relativedelta
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Cadence, ReminderLog, ReminderStage, UserProfile
from app.security import generate_review_token
from app.services.audit import log_audit_event
from app.services.email_notifier import EmailNotifier


@dataclass
class ReminderOutcome:
    scanned_users: int = 0
    reminders_sent: int = 0
    failures: int = 0


def next_due_date(last_completed_date: date, cadence: Cadence) -> date:
    if cadence == Cadence.SIX_MONTHS:
        return last_completed_date + relativedelta(months=+6)
    return last_completed_date + relativedelta(years=+1)


def determine_stage(today: date, due_date: date) -> ReminderStage | None:
    if today == due_date - relativedelta(days=30):
        return ReminderStage.THIRTY_DAYS_BEFORE
    if today == due_date:
        return ReminderStage.DUE_TODAY
    if today == due_date + relativedelta(days=7):
        return ReminderStage.OVERDUE_7_DAYS
    return None


def _build_message(user: UserProfile, due_date: date, stage: ReminderStage) -> tuple[str, str]:
    token = generate_review_token(user.id, stage.value)
    review_url = f"{settings.base_review_url}/{token}"

    subject = f"Lab requisition reminder for {user.full_name}"
    body = (
        f"Hello {user.full_name},\n\n"
        f"Your laboratory requisition form is due on {due_date.isoformat()} "
        f"({stage.value.replace('_', ' ')}).\n"
        f"Use this secure link to review and pre-fill your form:\n{review_url}\n\n"
        "After review, please submit the generated PDF manually to your provider.\n"
    )
    return subject, body


def run_daily_reminder_job(db: Session, notifier: EmailNotifier, today: date | None = None) -> ReminderOutcome:
    today = today or date.today()
    users = db.scalars(select(UserProfile).where(UserProfile.is_active.is_(True))).all()
    eligible_users = [user for user in users if bool((user.profile_data or {}).get("reminder_enabled", True))]
    outcome = ReminderOutcome(scanned_users=len(eligible_users))

    for user in eligible_users:
        due = next_due_date(user.last_completed_date, user.cadence)
        stage = determine_stage(today=today, due_date=due)
        if not stage:
            continue

        existing = db.scalar(
            select(ReminderLog).where(
                and_(
                    ReminderLog.user_id == user.id,
                    ReminderLog.stage == stage,
                    ReminderLog.due_date == due,
                )
            )
        )
        if existing:
            continue

        subject, body = _build_message(user=user, due_date=due, stage=stage)
        sent_ok, details = notifier.send_email(user.email, subject, body)
        log = ReminderLog(
            user_id=user.id,
            stage=stage,
            due_date=due,
            sent_to=user.email,
            status="sent" if sent_ok else "failed",
            details=details,
        )
        db.add(log)
        log_audit_event(
            db,
            user_id=user.id,
            action="reminder_sent" if sent_ok else "reminder_failed",
            details=f"stage={stage.value};due={due.isoformat()};status={details}",
        )
        if sent_ok:
            outcome.reminders_sent += 1
        else:
            outcome.failures += 1

    db.commit()
    return outcome

