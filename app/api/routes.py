from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Cadence
from app.models import GeneratedForm, UserProfile
from app.schemas import (
    FormGenerateResponse,
    FormHistoryItem,
    FormTemplateOut,
    GenerateFromTemplateRequest,
    MarkCompleteRequest,
    ReminderRunResult,
    ReminderSubscriptionOut,
    ReminderSubscriptionRequest,
)
from app.services.audit import log_audit_event
from app.services.email_notifier import EmailNotifier
from app.services.form_templates import get_template_or_none, list_templates as list_form_templates
from app.services.pdf_prefill import PDFPrefillService
from app.services.reminders import run_daily_reminder_job

router = APIRouter(prefix="/api", tags=["lab-automation"])

def _template_or_404(template_key: str) -> dict:
    template = get_template_or_none(template_key)
    if not template:
        raise HTTPException(status_code=404, detail="Unknown template_key.")
    return template


def _get_user_by_email_or_404(db: Session, email: str) -> UserProfile:
    user = db.scalar(select(UserProfile).where(UserProfile.email == email))
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.get("/templates", response_model=list[FormTemplateOut])
def list_templates() -> list[FormTemplateOut]:
    return [FormTemplateOut(**item) for item in list_form_templates()]


@router.post("/reminders/subscribe", response_model=ReminderSubscriptionOut)
def subscribe_to_reminders(
    payload: ReminderSubscriptionRequest,
    db: Session = Depends(get_db),
) -> ReminderSubscriptionOut:
    _template_or_404(payload.template_key)
    user = db.scalar(select(UserProfile).where(UserProfile.email == payload.email))

    merged_profile = dict(payload.profile_data)
    merged_profile["template_key"] = payload.template_key
    merged_profile["reminder_enabled"] = payload.reminder_enabled
    cadence = payload.cadence or Cadence.TWELVE_MONTHS

    if user:
        user.full_name = payload.full_name
        user.cadence = cadence
        user.last_completed_date = payload.last_completed_date
        user.profile_data = {**(user.profile_data or {}), **merged_profile}
        user.updated_at = datetime.utcnow()
        action = "subscription_updated"
    else:
        user = UserProfile(
            full_name=payload.full_name,
            email=str(payload.email),
            cadence=cadence,
            last_completed_date=payload.last_completed_date,
            profile_data=merged_profile,
        )
        db.add(user)
        db.flush()
        action = "subscription_created"

    log_audit_event(
        db,
        user_id=user.id,
        action=action,
        details=f"template={payload.template_key};cadence={cadence.value};reminder_enabled={payload.reminder_enabled}",
    )
    db.commit()
    db.refresh(user)
    return ReminderSubscriptionOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        cadence=user.cadence,
        template_key=user.profile_data.get("template_key", ""),
        last_completed_date=user.last_completed_date,
        reminder_enabled=bool((user.profile_data or {}).get("reminder_enabled", True)),
    )


@router.get("/reminders/subscriptions", response_model=list[ReminderSubscriptionOut])
def list_subscriptions(db: Session = Depends(get_db)) -> list[ReminderSubscriptionOut]:
    users = db.scalars(select(UserProfile).where(UserProfile.is_active.is_(True)).order_by(UserProfile.id)).all()
    return [
        ReminderSubscriptionOut(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            cadence=user.cadence,
            template_key=(user.profile_data or {}).get("template_key", ""),
            last_completed_date=user.last_completed_date,
            reminder_enabled=bool((user.profile_data or {}).get("reminder_enabled", True)),
        )
        for user in users
    ]


@router.post("/forms/generate", response_model=FormGenerateResponse)
def generate_form_from_template(
    payload: GenerateFromTemplateRequest,
    db: Session = Depends(get_db),
) -> FormGenerateResponse:
    _template_or_404(payload.template_key)
    user = db.scalar(select(UserProfile).where(UserProfile.email == payload.email))
    reminder_cadence = payload.cadence or Cadence.TWELVE_MONTHS

    if user:
        merged_profile = dict(user.profile_data or {})
        merged_profile["template_key"] = payload.template_key
        merged_profile["reminder_enabled"] = payload.reminder_enabled
        merged_profile.update(payload.profile_patch)
        user.full_name = payload.full_name
        user.cadence = reminder_cadence
        user.last_completed_date = payload.last_completed_date
        user.profile_data = merged_profile
        user.updated_at = datetime.utcnow()
    else:
        merged_profile = dict(payload.profile_patch)
        merged_profile["template_key"] = payload.template_key
        merged_profile["reminder_enabled"] = payload.reminder_enabled
        user = UserProfile(
            full_name=payload.full_name,
            email=str(payload.email),
            cadence=reminder_cadence,
            last_completed_date=payload.last_completed_date,
            profile_data=merged_profile,
        )
        db.add(user)
        db.flush()

    generator = PDFPrefillService()
    try:
        output_file = generator.generate_prefilled_pdf(merged_profile, user_id=user.id, template_key=payload.template_key)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    generated = GeneratedForm(user_id=user.id, file_path=output_file, is_final=payload.is_final)
    db.add(generated)
    log_audit_event(
        db,
        user_id=user.id,
        action="form_generated",
        details=(
            f"template={payload.template_key};is_final={payload.is_final};"
            f"reminder_enabled={payload.reminder_enabled};file={output_file}"
        ),
    )
    db.commit()
    db.refresh(generated)
    return FormGenerateResponse(generated_file=generated.file_path, generated_at=generated.created_at)


@router.get("/forms/history/{email}", response_model=list[FormHistoryItem])
def get_form_history(email: str, db: Session = Depends(get_db)) -> list[FormHistoryItem]:
    user = _get_user_by_email_or_404(db, email)
    forms = db.scalars(
        select(GeneratedForm)
        .where(GeneratedForm.user_id == user.id)
        .order_by(GeneratedForm.created_at.desc())
    ).all()
    return [FormHistoryItem(file_path=form.file_path, created_at=form.created_at, is_final=form.is_final) for form in forms]


@router.post("/forms/{email}/mark-complete", response_model=ReminderSubscriptionOut)
def mark_complete(
    email: str,
    payload: MarkCompleteRequest,
    db: Session = Depends(get_db),
) -> ReminderSubscriptionOut:
    user = _get_user_by_email_or_404(db, email)
    user.last_completed_date = payload.completed_on
    user.updated_at = datetime.utcnow()
    log_audit_event(db, user_id=user.id, action="form_marked_complete", details=payload.completed_on.isoformat())
    db.commit()
    db.refresh(user)
    return ReminderSubscriptionOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        cadence=user.cadence,
        template_key=(user.profile_data or {}).get("template_key", ""),
        last_completed_date=user.last_completed_date,
        reminder_enabled=bool((user.profile_data or {}).get("reminder_enabled", True)),
    )


@router.post("/reminders/run", response_model=ReminderRunResult)
def run_reminders(db: Session = Depends(get_db)) -> ReminderRunResult:
    result = run_daily_reminder_job(db=db, notifier=EmailNotifier())
    return ReminderRunResult(
        scanned_users=result.scanned_users,
        reminders_sent=result.reminders_sent,
        failures=result.failures,
    )


@router.get("/pdf/inspect")
def inspect_pdf_template() -> dict:
    return PDFPrefillService().inspect_pdf()

