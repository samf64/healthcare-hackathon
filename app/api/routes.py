from datetime import datetime
import json
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from dateutil.relativedelta import relativedelta

from app.config import settings
from app.models import Cadence, GeneratedForm, PatientJsonFile, PatientTemplateReminder, RequisitionRequest, RequisitionTemplate, UserProfile
from app.schemas import (
    FillTemplateRequest,
    PatientJsonFileContentOut,
    PatientJsonFileOut,
    FormGenerateResponse,
    FormHistoryItem,
    TemplateFileOut,
    FormTemplateOut,
    GenerateFromTemplateRequest,
    MarkCompleteRequest,
    PatientTemplateReminderRequest,
    PatientTemplateReminderResponse,
    ReminderRunResult,
    ReminderSubscriptionOut,
    ReminderSubscriptionRequest,
    RequisitionRequestCreate,
    RequisitionRequestOut,
    RequisitionTemplateCreate,
    RequisitionTemplateOut,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services.audit import log_audit_event
from app.services.email_notifier import EmailNotifier
from app.services.form_templates import (
    build_preview_profile,
    get_template_or_none,
    list_templates as list_form_templates,
)
from app.services.pdf_prefill import PDFPrefillService
from app.services.reminders import build_patient_template_reminder_message, run_daily_reminder_job
from app.services.template_files import (
    delete_template_file,
    get_template_file_by_name,
    import_templates_from_folder,
    list_template_files,
    load_global_field_mapping,
    upsert_template_file,
)

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


def _patient_value(data: dict, keys: list[str], fallback: str = "") -> str:
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip() != "":
            return str(value).strip()
    return fallback


def _safe_generated_file_path(file_path: str) -> Path:
    raw = Path(file_path)
    resolved = (Path.cwd() / raw).resolve() if not raw.is_absolute() else raw.resolve()
    generated_root = Path(settings.generated_pdf_dir)
    generated_root = (Path.cwd() / generated_root).resolve() if not generated_root.is_absolute() else generated_root.resolve()
    if generated_root != resolved and generated_root not in resolved.parents:
        raise HTTPException(status_code=400, detail="File path is outside generated forms directory.")
    if resolved.suffix.lower() != ".pdf":
        raise HTTPException(status_code=400, detail="Only PDF files can be opened.")
    if not resolved.exists() or not resolved.is_file():
        raise HTTPException(status_code=404, detail="Generated file not found.")
    return resolved


@router.get("/users", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)) -> list[UserProfile]:
    return db.scalars(select(UserProfile).order_by(UserProfile.id)).all()


@router.post("/requisition-templates", response_model=RequisitionTemplateOut)
def create_template(
    payload: RequisitionTemplateCreate,
    db: Session = Depends(get_db),
) -> RequisitionTemplate:
    template = RequisitionTemplate(
        name=payload.name,
        description=payload.description,
        template_json=payload.template_json,
        version=payload.version,
        is_active=payload.is_active,
    )
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.get("/requisition-templates", response_model=list[RequisitionTemplateOut])
def list_templates(db: Session = Depends(get_db)) -> list[RequisitionTemplate]:
    return db.scalars(select(RequisitionTemplate).order_by(RequisitionTemplate.id)).all()


@router.post("/requisition-requests", response_model=RequisitionRequestOut)
def create_requisition_request(
    payload: RequisitionRequestCreate,
    db: Session = Depends(get_db),
) -> RequisitionRequest:
    user = db.get(UserProfile, payload.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    template = db.get(RequisitionTemplate, payload.template_id)
    if not template:
        raise HTTPException(status_code=404, detail="Template not found.")

    request = RequisitionRequest(
        user_id=payload.user_id,
        template_id=payload.template_id,
        status=payload.status,
        reminder_interval_days=payload.reminder_interval_days,
        next_reminder_at=payload.next_reminder_at,
        custom_payload=payload.custom_payload,
        notes=payload.notes,
    )
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


@router.get("/requisition-requests", response_model=list[RequisitionRequestOut])
def list_requisition_requests(db: Session = Depends(get_db)) -> list[RequisitionRequest]:
    return db.scalars(select(RequisitionRequest).order_by(RequisitionRequest.id)).all()


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(user_id: int, payload: UserUpdate, db: Session = Depends(get_db)) -> UserProfile:
    user = db.get(UserProfile, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key == "profile_data" and user.profile_data:
            user.profile_data = {**user.profile_data, **value}
        else:
            setattr(user, key, value)

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    return user


@router.get("/template-files", response_model=list[TemplateFileOut])
def list_template_pdfs(db: Session = Depends(get_db)) -> list[TemplateFileOut]:
    rows = list_template_files(db)
    if not rows:
        imported = import_templates_from_folder(db)
        if imported:
            db.commit()
            rows = list_template_files(db)
    return [TemplateFileOut(name=row.name, preview_url=f"/api/template-files/preview?name={row.name}") for row in rows]


@router.get("/template-files/preview")
def preview_template_pdf(name: str, db: Session = Depends(get_db)) -> Response:
    try:
        row = get_template_file_by_name(db, name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")
    return Response(content=row.file_data, media_type=row.content_type, headers={"Content-Disposition": f'inline; filename=\"{row.name}\"'})


@router.post("/template-files/upload", response_model=TemplateFileOut)
async def upload_template_pdf(file: UploadFile = File(...), db: Session = Depends(get_db)) -> TemplateFileOut:
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only .pdf files are allowed.")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")
    row = upsert_template_file(db, filename, data, "application/pdf")
    db.commit()
    return TemplateFileOut(name=row.name, preview_url=f"/api/template-files/preview?name={row.name}")


@router.delete("/template-files/{name}")
def delete_template_pdf(name: str, db: Session = Depends(get_db)) -> dict:
    try:
        deleted = delete_template_file(db, name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Template not found: {name}")
    db.commit()
    return {"deleted": name}


@router.get("/patient-json-files", response_model=list[PatientJsonFileOut])
def list_patient_json_files(db: Session = Depends(get_db)) -> list[PatientJsonFile]:
    return db.scalars(select(PatientJsonFile).order_by(PatientJsonFile.name)).all()


@router.post("/patient-json-files/upload", response_model=PatientJsonFileOut)
async def upload_patient_json_file(file: UploadFile = File(...), db: Session = Depends(get_db)) -> PatientJsonFileOut:
    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are allowed.")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="Uploaded JSON file is empty.")

    try:
        parsed = json.loads(raw.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="JSON root must be an object.")

    row = db.scalar(select(PatientJsonFile).where(PatientJsonFile.name == filename))
    if row:
        row.data = parsed
        row.updated_at = datetime.utcnow()
    else:
        row = PatientJsonFile(name=filename, data=parsed)
        db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.get("/patient-json-files/{file_id}", response_model=PatientJsonFileContentOut)
def get_patient_json_file(file_id: int, db: Session = Depends(get_db)) -> PatientJsonFileContentOut:
    row = db.get(PatientJsonFile, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="Patient JSON file not found.")
    return PatientJsonFileContentOut(id=row.id, name=row.name, data=row.data or {})


@router.delete("/patient-json-files/{file_id}")
def delete_patient_json_file(file_id: int, db: Session = Depends(get_db)) -> dict:
    row = db.get(PatientJsonFile, file_id)
    if not row:
        raise HTTPException(status_code=404, detail="Patient JSON file not found.")
    deleted_name = row.name
    db.delete(row)
    db.commit()
    return {"deleted": deleted_name}


@router.post("/reminders/patient-template", response_model=PatientTemplateReminderResponse)
def create_patient_template_reminder(
    payload: PatientTemplateReminderRequest,
    db: Session = Depends(get_db),
) -> PatientTemplateReminderResponse:
    patient_row = db.get(PatientJsonFile, payload.patient_json_file_id)
    if not patient_row:
        raise HTTPException(status_code=404, detail="Patient JSON file not found.")

    try:
        template_row = get_template_file_by_name(db, payload.template_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not template_row:
        raise HTTPException(status_code=404, detail=f"Template not found: {payload.template_name}")

    data = patient_row.data or {}
    email = str(payload.recipient_email).strip() if payload.recipient_email else _patient_value(data, ["email"])
    if not email:
        raise HTTPException(status_code=400, detail="Provide `recipient_email` or include `email` in the selected patient JSON.")
    full_name = _patient_value(data, ["full_name", "fullName"], "Patient")

    if payload.mode.value == "instant":
        subject, body = build_patient_template_reminder_message(
            full_name=full_name,
            template_name=payload.template_name,
            patient_file_name=patient_row.name,
        )
        ok, details = EmailNotifier().send_email(email, subject, body)
        return PatientTemplateReminderResponse(
            mode=payload.mode,
            sent_now=ok,
            detail=details if ok else f"failed: {details}",
        )

    months = payload.months or 0
    if months < 1 or months > 24:
        raise HTTPException(status_code=400, detail="For months mode, `months` must be between 1 and 24.")

    next_send = datetime.utcnow().date() + relativedelta(months=+months)
    existing = db.scalar(
        select(PatientTemplateReminder).where(
            PatientTemplateReminder.patient_json_file_id == payload.patient_json_file_id,
            PatientTemplateReminder.template_name == payload.template_name,
            PatientTemplateReminder.email == email,
            PatientTemplateReminder.is_active.is_(True),
        )
    )
    if existing:
        existing.full_name = full_name
        existing.months_interval = months
        existing.next_send_on = next_send
        existing.updated_at = datetime.utcnow()
        row = existing
    else:
        row = PatientTemplateReminder(
            patient_json_file_id=payload.patient_json_file_id,
            template_name=payload.template_name,
            full_name=full_name,
            email=email,
            months_interval=months,
            next_send_on=next_send,
            is_active=True,
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return PatientTemplateReminderResponse(
        mode=payload.mode,
        sent_now=False,
        detail=f"Reminder scheduled every {months} month(s).",
        reminder_id=row.id,
        next_send_on=row.next_send_on,
    )


@router.post("/forms/fill-template", response_model=FormGenerateResponse)
def fill_template_with_patient_info(payload: FillTemplateRequest, db: Session = Depends(get_db)) -> FormGenerateResponse:
    try:
        template_row = get_template_file_by_name(db, payload.template_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not template_row:
        raise HTTPException(status_code=404, detail=f"Template not found: {payload.template_name}")

    user = db.scalar(select(UserProfile).where(UserProfile.email == payload.email))
    profile = {
        "patient_last_name": payload.patient_last_name,
        "patient_first_name": payload.patient_first_name,
        "health_number": payload.health_number,
        "health_version": payload.health_version,
        "sex": payload.sex,
        "province": payload.province,
        "other_provincial_registration_number": payload.other_provincial_registration_number,
        "date_of_birth": payload.date_of_birth,
        "service_date": payload.service_date,
        "phone_number": payload.phone_number or "",
        "address": payload.address or "",
        "template_name": payload.template_name,
        "reminder_enabled": False,
    }

    if user:
        user.full_name = payload.full_name
        user.profile_data = {**(user.profile_data or {}), **profile}
        user.updated_at = datetime.utcnow()
    else:
        user = UserProfile(
            full_name=payload.full_name,
            email=str(payload.email),
            cadence=Cadence.TWELVE_MONTHS,
            last_completed_date=datetime.utcnow().date(),
            profile_data=profile,
        )
        db.add(user)
        db.flush()

    generator = PDFPrefillService(template_bytes=template_row.file_data)
    output_name = f"{Path(payload.template_name).stem}_user_{user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
    active_mapping = load_global_field_mapping()
    try:
        output_file = generator.generate_prefilled_pdf(
            profile,
            user_id=user.id,
            output_name=output_name,
            strict_field_mapping=active_mapping,
            strict_mode=True,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    generated = GeneratedForm(user_id=user.id, file_path=output_file, is_final=False)
    db.add(generated)
    log_audit_event(
        db,
        user_id=user.id,
        action="template_filled",
        details=f"template_file={payload.template_name};file={output_file}",
    )
    db.commit()
    db.refresh(generated)
    return FormGenerateResponse(generated_file=generated.file_path, generated_at=generated.created_at)


@router.get("/forms/open")
def open_generated_form(file_path: str) -> FileResponse:
    resolved = _safe_generated_file_path(file_path)
    return FileResponse(path=str(resolved), media_type="application/pdf", filename=resolved.name)


@router.get("/templates", response_model=list[FormTemplateOut])
def list_templates() -> list[FormTemplateOut]:
    return [
        FormTemplateOut(**item, preview_url=f"/api/templates/{item['key']}/preview")
        for item in list_form_templates()
    ]


@router.get("/templates/{template_key}/preview")
def get_template_preview(template_key: str) -> FileResponse:
    _template_or_404(template_key)
    profile = build_preview_profile(template_key)
    output_name = f"template_preview_{template_key}.pdf"
    generator = PDFPrefillService()
    output_file = generator.generate_prefilled_pdf(
        profile,
        user_id=0,
        template_key=template_key,
        output_name=output_name,
    )
    return FileResponse(path=output_file, media_type="application/pdf", filename=Path(output_file).name)


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

