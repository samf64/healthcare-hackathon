from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import GeneratedForm, UserProfile
from app.schemas import (
    FormGenerateRequest,
    FormGenerateResponse,
    MarkCompleteRequest,
    ReminderRunResult,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.security import verify_review_token
from app.services.audit import log_audit_event
from app.services.email_notifier import EmailNotifier
from app.services.pdf_prefill import PDFPrefillService
from app.services.reminders import run_daily_reminder_job

router = APIRouter(prefix="/api", tags=["lab-automation"])


@router.post("/users", response_model=UserOut)
def create_user(payload: UserCreate, db: Session = Depends(get_db)) -> UserProfile:
    existing = db.scalar(select(UserProfile).where(UserProfile.email == payload.email))
    if existing:
        raise HTTPException(status_code=400, detail="Email already exists.")

    user = UserProfile(
        full_name=payload.full_name,
        email=str(payload.email),
        cadence=payload.cadence,
        last_completed_date=payload.last_completed_date,
        profile_data=payload.profile_data,
    )
    db.add(user)
    db.flush()
    log_audit_event(db, user_id=user.id, action="user_created", details=f"cadence={user.cadence.value}")
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[UserProfile]:
    return db.scalars(select(UserProfile).order_by(UserProfile.id)).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> UserProfile:
    user = db.get(UserProfile, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)
    user.updated_at = datetime.utcnow()
    log_audit_event(db, user_id=user.id, action="user_updated", details="profile updated")
    db.commit()
    db.refresh(user)
    return user


@router.get("/review/{token}")
def open_review_link(token: str, db: Session = Depends(get_db)) -> dict:
    try:
        token_data = verify_review_token(token)
    except Exception as exc:  # pragma: no cover
        raise HTTPException(status_code=400, detail=f"Invalid or expired token: {exc}") from exc

    user = db.get(UserProfile, token_data["user_id"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    log_audit_event(db, user_id=user.id, action="review_link_opened", details=f"stage={token_data['stage']}")
    db.commit()
    return {
        "user_id": user.id,
        "full_name": user.full_name,
        "email": user.email,
        "profile_data": user.profile_data,
        "reminder_stage": token_data["stage"],
    }


@router.post("/users/{user_id}/forms", response_model=FormGenerateResponse)
def generate_form(
    user_id: int,
    payload: FormGenerateRequest,
    db: Session = Depends(get_db),
) -> FormGenerateResponse:
    user = db.get(UserProfile, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    merged_profile = dict(user.profile_data or {})
    merged_profile.update(payload.profile_patch)

    generator = PDFPrefillService()
    try:
        output_file = generator.generate_prefilled_pdf(merged_profile, user_id=user.id)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    user.profile_data = merged_profile
    generated = GeneratedForm(user_id=user.id, file_path=output_file, is_final=payload.is_final)
    db.add(generated)
    log_audit_event(
        db,
        user_id=user.id,
        action="form_generated",
        details=f"is_final={payload.is_final};file={output_file}",
    )
    db.commit()
    db.refresh(generated)
    return FormGenerateResponse(generated_file=generated.file_path, generated_at=generated.created_at)


@router.post("/users/{user_id}/mark-complete", response_model=UserOut)
def mark_complete(
    user_id: int,
    payload: MarkCompleteRequest,
    db: Session = Depends(get_db),
) -> UserProfile:
    user = db.get(UserProfile, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.last_completed_date = payload.completed_on
    user.updated_at = datetime.utcnow()
    log_audit_event(db, user_id=user.id, action="form_marked_complete", details=payload.completed_on.isoformat())
    db.commit()
    db.refresh(user)
    return user


@router.post("/jobs/run-reminders", response_model=ReminderRunResult)
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

