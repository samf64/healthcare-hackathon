from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.config import settings
from app.services.pdf_prefill import PDFPrefillService


def _create_flat_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawString(50, 750, "Ontario Lab Requisition Test Template")
    c.save()


def _create_fillable_pdf(path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawString(80, 740, "Fillable template")
    form = c.acroForm
    form.textfield(name="PatientLastName", x=100, y=700, width=200, height=20)
    c.save()


def test_inspect_pdf_detects_fillable(tmp_path):
    pdf_path = tmp_path / "fillable.pdf"
    _create_fillable_pdf(pdf_path)
    service = PDFPrefillService(template_path=str(pdf_path))
    info = service.inspect_pdf()
    assert info["exists"] is True
    assert info["fillable"] is True
    assert "PatientLastName" in info["fields"]


def test_generate_prefilled_pdf_with_overlay_fallback(tmp_path):
    pdf_path = tmp_path / "flat.pdf"
    _create_flat_pdf(pdf_path)
    out_dir = tmp_path / "out"
    settings.generated_pdf_dir = str(out_dir)

    service = PDFPrefillService(template_path=str(pdf_path))
    result = service.generate_prefilled_pdf(
        {
            "patient_last_name": "Doe",
            "patient_first_name": "Jane",
            "date_of_birth": "1990-04-01",
        },
        user_id=99,
    )
    generated_path = Path(result)
    assert generated_path.exists()
    assert generated_path.suffix.lower() == ".pdf"

