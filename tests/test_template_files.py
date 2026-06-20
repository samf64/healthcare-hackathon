from pathlib import Path

from app.config import settings
from app.services.template_files import list_template_files, resolve_template_file


def test_list_template_files_reads_pdf_only(tmp_path):
    original = settings.template_library_dir
    settings.template_library_dir = str(tmp_path)
    try:
        (tmp_path / "a.pdf").write_bytes(b"%PDF-1.4")
        (tmp_path / "b.txt").write_text("x", encoding="utf-8")
        files = list_template_files()
        assert files == ["a.pdf"]
    finally:
        settings.template_library_dir = original


def test_resolve_template_file_blocks_traversal(tmp_path):
    original = settings.template_library_dir
    settings.template_library_dir = str(tmp_path)
    try:
        (tmp_path / "ok.pdf").write_bytes(b"%PDF-1.4")
        assert resolve_template_file("ok.pdf") == Path(tmp_path / "ok.pdf").resolve()
        try:
            resolve_template_file("../bad.pdf")
            assert False, "Expected ValueError for traversal"
        except ValueError:
            assert True
    finally:
        settings.template_library_dir = original
