from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import SessionLocal
from app.services.email_notifier import EmailNotifier
from app.services.reminders import run_daily_reminder_job


scheduler = BackgroundScheduler(timezone="UTC")


def _run_scheduled_reminders() -> None:
    db = SessionLocal()
    try:
        run_daily_reminder_job(db=db, notifier=EmailNotifier())
    finally:
        db.close()


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _run_scheduled_reminders,
        trigger=CronTrigger(hour=8, minute=0),
        id="daily-reminder-job",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)

