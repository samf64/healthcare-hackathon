from __future__ import annotations

import io
from datetime import datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, TextStringObject
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from app.config import settings
from app.services.form_templates import build_template_overlay


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

    def generate_prefilled_pdf(self, profile_data: dict[str, Any], user_id: int, template_key: str | None = None) -> str:
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
            # For this Ontario form, explicit overlay is the most reliable way to ensure
            # visible output across PDF viewers, even when AcroForm values are present.
            self._fill_form_fields(template, output_path, profile_data, template_key=template_key)
            self._overlay_flat_pdf(output_path, output_path, profile_data, template_key=template_key)
        else:
            self._overlay_flat_pdf(template, output_path, profile_data, template_key=template_key)
        return str(output_path.resolve())

    @staticmethod
    def _fill_form_fields(
        template: Path,
        output_path: Path,
        profile_data: dict[str, Any],
        template_key: str | None = None,
    ) -> None:
        writer = PdfWriter(clone_from=str(template))
        template_overlay = build_template_overlay(template_key or "", profile_data)
        other_tests = template_overlay.get("other_tests_text", "")
        page = writer.pages[0]
        annots = page.get("/Annots", [])

        # Anchor patient fields to approximate page coordinates, then resolve nearest text widgets.
        text_by_anchor = {
            "patient_last_name": ((130, 336), str(profile_data.get("patient_last_name", "")).strip()),
            "patient_first_name": ((330, 336), str(profile_data.get("patient_first_name", "")).strip()),
            "address": ((150, 317), str(profile_data.get("address", "")).strip()),
            "phone_number": ((420, 282), str(profile_data.get("phone_number", "")).strip()),
            "date_of_birth": ((355, 265), str(profile_data.get("date_of_birth", "")).strip()),
            "health_number": ((310, 246), str(profile_data.get("health_number", "")).strip()),
            "service_date": ((98, 223), str(profile_data.get("service_date", "")).strip()),
            "clinician_name": ((90, 542), str(profile_data.get("clinician_name", "")).strip()),
            "clinician_number": ((95, 523), str(profile_data.get("clinician_number", "")).strip()),
            "additional_info": ((90, 503), str(profile_data.get("additional_info", "")).strip()),
            "other_tests": ((250, 520), str(other_tests).strip()),
        }

        text_field_values = PDFPrefillService._resolve_text_fields_by_coords(annots, text_by_anchor)
        PDFPrefillService._apply_widget_values(page, text_field_values, checkbox_field_names=[])

        checkbox_points = [(m.get("x"), m.get("y")) for m in template_overlay.get("checkbox_marks", [])]
        checkbox_field_names = PDFPrefillService._resolve_checkbox_fields_by_coords(annots, checkbox_points)
        if checkbox_field_names:
            PDFPrefillService._apply_widget_values(page, {}, checkbox_field_names)

        writer.set_need_appearances_writer(True)

        with output_path.open("wb") as out_stream:
            writer.write(out_stream)

    @staticmethod
    def _overlay_flat_pdf(
        template: Path,
        output_path: Path,
        profile_data: dict[str, Any],
        template_key: str | None = None,
    ) -> None:
        writer = PdfWriter(clone_from=str(template))
        first_page = writer.pages[0]
        template_overlay = build_template_overlay(template_key or "", profile_data)

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

        for mark in template_overlay.get("checkbox_marks", []):
            x = mark.get("x")
            y = mark.get("y")
            if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                c.drawString(float(x), float(y), "X")

        other_tests_text = str(template_overlay.get("other_tests_text", "")).strip()
        if other_tests_text:
            c.drawString(250, 520, other_tests_text)
        c.save()
        packet.seek(0)

        overlay_pdf = PdfReader(packet)
        first_page.merge_page(overlay_pdf.pages[0])

        with output_path.open("wb") as out_stream:
            writer.write(out_stream)

    @staticmethod
    def _resolve_text_fields_by_coords(annots: list, anchors: dict[str, tuple[tuple[float, float], str]]) -> dict[str, str]:
        resolved: dict[str, str] = {}
        used: set[str] = set()

        for _, (target, value) in anchors.items():
            if not value:
                continue
            name = PDFPrefillService._closest_widget_name(annots, target, allowed_ft="/Tx", used_names=used)
            if name:
                resolved[name] = value
                used.add(name)
        return resolved

    @staticmethod
    def _resolve_checkbox_fields_by_coords(annots: list, points: list[tuple[Any, Any]]) -> list[str]:
        names: list[str] = []
        used: set[str] = set()

        for x, y in points:
            if not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
                continue
            name = PDFPrefillService._closest_widget_name(annots, (float(x), float(y)), allowed_ft="/Btn", used_names=used)
            if name:
                names.append(name)
                used.add(name)
        return names

    @staticmethod
    def _closest_widget_name(
        annots: list,
        target: tuple[float, float],
        allowed_ft: str,
        used_names: set[str],
    ) -> str | None:
        tx, ty = target
        best_name: str | None = None
        best_dist = float("inf")

        for annot_ref in annots:
            annot = annot_ref.get_object()
            name = annot.get("/T")
            if not name or name in used_names or str(annot.get("/FT")) != allowed_ft:
                continue
            rect = annot.get("/Rect")
            if not rect:
                continue
            cx = (float(rect[0]) + float(rect[2])) / 2
            cy = (float(rect[1]) + float(rect[3])) / 2
            dist = (cx - tx) ** 2 + (cy - ty) ** 2
            if dist < best_dist:
                best_dist = dist
                best_name = str(name)
        return best_name

    @staticmethod
    def _apply_widget_values(page, text_values: dict[str, str], checkbox_field_names: list[str]) -> None:
        for annot_ref in page.get("/Annots", []):
            annot = annot_ref.get_object()
            name = str(annot.get("/T") or "")
            ft = str(annot.get("/FT") or "")

            if ft == "/Tx" and name in text_values:
                value = text_values[name]
                annot.update({NameObject("/V"): TextStringObject(value), NameObject("/DV"): TextStringObject(value)})

            if ft == "/Btn" and name in checkbox_field_names:
                on_state = NameObject("/Off")
                ap = annot.get("/AP", {}).get("/N", {})
                if hasattr(ap, "keys"):
                    for state_name in ap.keys():
                        if str(state_name) != "/Off":
                            on_state = state_name
                            break
                annot.update({NameObject("/V"): on_state, NameObject("/AS"): on_state})

