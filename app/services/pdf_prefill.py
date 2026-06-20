from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.config import settings


class PDFPrefillService:
    """
    Generates pre-filled requisition PDFs.
    - Uses AcroForm fields when available.
    - Falls back to coordinate overlay for flat PDFs.
    """

    def __init__(self, template_path: str | None = None) -> None:
        self.template_path = template_path or settings.requisition_pdf_path

    def inspect_pdf(self) -> dict[str, Any]:
        if not self.template_path:
            return {"exists": False, "fillable": False, "fields": []}
        path = Path(self.template_path)
        if not path.exists():
            return {"exists": False, "fillable": False, "fields": []}

        reader = PdfReader(str(path))
        fields = reader.get_fields() or {}
        return {"exists": True, "fillable": bool(fields), "fields": list(fields.keys())}

    def generate_prefilled_pdf(self, profile_data: dict[str, Any], user_id: int) -> str:
        if not self.template_path:
            raise ValueError("No requisition_pdf_path configured.")
        template = Path(self.template_path)
        if not template.exists():
            raise FileNotFoundError(f"Template not found: {self.template_path}")

        output_dir = Path(settings.generated_pdf_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        output_name = f"user_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        output_path = output_dir / output_name

        metadata = self.inspect_pdf()
        if metadata["fillable"]:
            self._fill_form_fields(template, output_path, profile_data)
        else:
            self._overlay_flat_pdf(template, output_path, profile_data)
        return str(output_path.resolve())

    @staticmethod
    def _fill_form_fields(template: Path, output_path: Path, profile_data: dict[str, Any]) -> None:
        writer = PdfWriter(clone_from=str(template))

        # Field names must be mapped to the actual PDF AcroForm names.
        mapped_fields = {
            "PatientLastName": profile_data.get("patient_last_name", ""),
            "PatientFirstName": profile_data.get("patient_first_name", ""),
            "DateOfBirth": profile_data.get("date_of_birth", ""),
            "HealthNumber": profile_data.get("health_number", ""),
            "Address": profile_data.get("address", ""),
            "Phone": profile_data.get("phone_number", ""),
            "ClinicianName": profile_data.get("clinician_name", ""),
            "ServiceDate": profile_data.get("service_date", ""),
        }
        writer.update_page_form_field_values(writer.pages[0], mapped_fields)

        with output_path.open("wb") as out_stream:
            writer.write(out_stream)

    @staticmethod
    def _overlay_flat_pdf(template: Path, output_path: Path, profile_data: dict[str, Any]) -> None:
        writer = PdfWriter(clone_from=str(template))
        first_page = writer.pages[0]

        # Coordinate map for Ontario requisition first page (tune as needed).
        overlay_fields = {
            "patient_last_name": (130, 336),
            "patient_first_name": (330, 336),
            "address": (150, 317),
            "phone_number": (420, 282),
            "date_of_birth": (355, 265),
            "health_number": (310, 246),
            "service_date": (98, 223),
            "sex": (480, 246),
            "clinician_name": (90, 542),
            "clinician_number": (95, 523),
            "additional_info": (90, 503),
        }

        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)
        c.setFont("Helvetica", 9)
        for field, (x, y) in overlay_fields.items():
            value = str(profile_data.get(field, "")).strip()
            if value:
                c.drawString(x, y, value)
        c.save()
        packet.seek(0)

        overlay_pdf = PdfReader(packet)
        first_page.merge_page(overlay_pdf.pages[0])

        with output_path.open("wb") as out_stream:
            writer.write(out_stream)

