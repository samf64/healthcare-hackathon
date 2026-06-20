from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database import Base
from app.services import template_files
from app.services.template_files import (
    DEFAULT_GLOBAL_FIELD_MAPPING,
    delete_template_file,
    get_template_file_by_name,
    load_global_field_mapping,
    list_template_files,
    upsert_template_file,
)


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def test_list_template_files_reads_from_database():
    db = _session()
    upsert_template_file(db, "a.pdf", b"%PDF-1.4 A")
    upsert_template_file(db, "b.pdf", b"%PDF-1.4 B")
    db.commit()
    rows = list_template_files(db)
    assert [r.name for r in rows] == ["a.pdf", "b.pdf"]


def test_get_template_file_blocks_traversal_name():
    db = _session()
    try:
        get_template_file_by_name(db, "../bad.pdf")
        assert False
    except ValueError:
        assert True


def test_upsert_template_file_updates_existing():
    db = _session()
    upsert_template_file(db, "demo.pdf", b"A")
    upsert_template_file(db, "demo.pdf", b"B")
    db.commit()
    row = get_template_file_by_name(db, "demo.pdf")
    assert row is not None
    assert row.file_data == b"B"


def test_delete_template_file_removes_row():
    db = _session()
    upsert_template_file(db, "remove.pdf", b"A")
    db.commit()
    assert delete_template_file(db, "remove.pdf") is True
    db.commit()
    assert get_template_file_by_name(db, "remove.pdf") is None


def test_default_global_mapping_exists():
    assert "patient_last_name" in DEFAULT_GLOBAL_FIELD_MAPPING
    assert "health_number" in DEFAULT_GLOBAL_FIELD_MAPPING


def test_load_global_field_mapping_uses_file_when_present(tmp_path):
    original = template_files.MAPPING_FILE_PATH
    try:
        custom = tmp_path / "patient_field_mapping.json"
        custom.write_text('{"patient_last_name":"Text_99"}', encoding="utf-8")
        template_files.MAPPING_FILE_PATH = custom
        loaded = load_global_field_mapping()
        assert loaded["patient_last_name"] == "Text_99"
    finally:
        template_files.MAPPING_FILE_PATH = original
