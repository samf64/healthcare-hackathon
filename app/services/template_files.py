import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import TemplateFile


DEFAULT_GLOBAL_FIELD_MAPPING: dict[str, object] = {
    "patient_last_name": "Text_20",
    "patient_first_name_left": "Text_21",
    "patient_first_name_right": "Text_22",
    "health_number": "Text_11",
    "health_version": "Text_12",
    "dob_year": "Text_13",
    "dob_month": "Text_14",
    "dob_day": "Text_15",
    "phone_area": "Text_18",
    "phone_rest": "Text_19",
    "address": "Text_50",
    "province": "Text_16",
    "other_provincial_registration_number": "Text_17",
    "sex_m_checkbox": {"field": "Radiobutton", "value": "1"},
    "sex_f_checkbox": {"field": "Radiobutton", "value": "2"},
}

MAPPING_FILE_PATH = Path("mappings/patient_field_mapping.json")


def _library_dir() -> Path:
    path = Path(settings.template_library_dir)
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_global_field_mapping() -> dict[str, object]:
    """
    Source-of-truth mapping loader.
    If mapping file exists and is valid JSON object, use it.
    Otherwise fall back to baked defaults.
    """
    if not MAPPING_FILE_PATH.exists():
        return dict(DEFAULT_GLOBAL_FIELD_MAPPING)
    try:
        loaded = json.loads(MAPPING_FILE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return dict(DEFAULT_GLOBAL_FIELD_MAPPING)
    if not isinstance(loaded, dict):
        return dict(DEFAULT_GLOBAL_FIELD_MAPPING)
    return loaded


def _validate_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned or "/" in cleaned or "\\" in cleaned:
        raise ValueError("Invalid template name.")
    return cleaned


def list_template_files(db: Session) -> list[TemplateFile]:
    return db.scalars(select(TemplateFile).order_by(TemplateFile.name)).all()


def get_template_file_by_name(db: Session, name: str) -> TemplateFile | None:
    safe_name = _validate_name(name)
    return db.scalar(select(TemplateFile).where(TemplateFile.name == safe_name))


def upsert_template_file(db: Session, name: str, file_data: bytes, content_type: str = "application/pdf") -> TemplateFile:
    safe_name = _validate_name(name)
    existing = get_template_file_by_name(db, safe_name)
    if existing:
        existing.file_data = file_data
        existing.content_type = content_type
        db.flush()
        return existing
    row = TemplateFile(name=safe_name, file_data=file_data, content_type=content_type)
    db.add(row)
    db.flush()
    return row


def delete_template_file(db: Session, name: str) -> bool:
    row = get_template_file_by_name(db, name)
    if not row:
        return False
    db.delete(row)
    db.flush()
    return True


def import_templates_from_folder(db: Session) -> int:
    imported = 0
    for path in _library_dir().glob("*.pdf"):
        if not path.is_file():
            continue
        upsert_template_file(db, path.name, path.read_bytes(), "application/pdf")
        imported += 1
    return imported

