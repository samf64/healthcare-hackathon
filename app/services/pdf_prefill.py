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
from app.services.form_templates import build_template_overlay, get_template_or_none


class PDFPrefillService:
    """
    Generates pre-filled requisition PDFs.
    - Uses AcroForm fields when available.
    - Falls back to coordinate overlay for flat PDFs.
    """

    def __init__(self, template_path: str | None = None, template_bytes: bytes | None = None) -> None:
        self.template_path = template_path or settings.requisition_pdf_path
        self.template_bytes = template_bytes

    def inspect_pdf(self) -> dict[str, Any]:
        if self.template_bytes:
            reader = PdfReader(io.BytesIO(self.template_bytes))
            fields = reader.get_fields() or {}
            return {"exists": True, "fillable": bool(fields), "fields": list(fields.keys())}
        if not self.template_path:
            return {"exists": False, "fillable": False, "fields": []}
        path = Path(self.template_path)
        if not path.exists():
            return {"exists": False, "fillable": False, "fields": []}

        reader = PdfReader(str(path))
        fields = reader.get_fields() or {}
        return {"exists": True, "fillable": bool(fields), "fields": list(fields.keys())}

    def generate_prefilled_pdf(
        self,
        profile_data: dict[str, Any],
        user_id: int,
        template_key: str | None = None,
        output_name: str | None = None,
        strict_field_mapping: dict[str, str] | None = None,
        strict_mode: bool = False,
    ) -> str:
        if not self.template_bytes and not self.template_path:
            raise ValueError("No requisition_pdf_path configured.")
        template_source: str | PdfReader
        if self.template_bytes:
            template_source = PdfReader(io.BytesIO(self.template_bytes))
        else:
            template = Path(self.template_path)
            if not template.exists():
                raise FileNotFoundError(f"Template not found: {self.template_path}")
            template_source = str(template)

        output_dir = Path(settings.generated_pdf_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        resolved_name = output_name or f"user_{user_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.pdf"
        output_path = output_dir / resolved_name

        metadata = self.inspect_pdf()
        template_cfg = get_template_or_none(template_key or "") or {}
        has_explicit_mapping = bool(template_cfg.get("text_field_map") or template_cfg.get("checkbox_field_names"))
        if metadata["fillable"]:
            self._fill_form_fields(
                template_source,
                output_path,
                profile_data,
                template_key=template_key,
                strict_field_mapping=strict_field_mapping,
                strict_mode=strict_mode,
            )
            # For templates without explicit field mapping, keep overlay fallback to improve visibility.
            if not strict_mode and not has_explicit_mapping:
                self._overlay_flat_pdf(output_path, output_path, profile_data, template_key=template_key)
        else:
            # Same-layout templates may be flattened; use deterministic fixed overlay in strict mode.
            self._overlay_fixed_layout(
                template_source,
                output_path,
                profile_data,
                strict_field_mapping=strict_field_mapping,
            )
        return str(output_path.resolve())

    @staticmethod
    def _fill_form_fields(
        template: str | PdfReader,
        output_path: Path,
        profile_data: dict[str, Any],
        template_key: str | None = None,
        strict_field_mapping: dict[str, str] | None = None,
        strict_mode: bool = False,
    ) -> None:
        writer = PdfWriter(clone_from=template)
        template_overlay = build_template_overlay(template_key or "", profile_data)
        other_tests = template_overlay.get("other_tests_text", "")
        page = writer.pages[0]
        annots = page.get("/Annots", [])
        template_cfg = get_template_or_none(template_key or "") or {}
        derived = PDFPrefillService._derive_profile_values(profile_data, other_tests)

        text_field_values: dict[str, str] = {}
        mapped_checkbox_fields: list[str] = []
        mapping_override = strict_field_mapping or {}
        if mapping_override:
            for source_key, field_spec in mapping_override.items():
                target_field = ""
                explicit_value: str | None = None
                if isinstance(field_spec, dict):
                    target_field = str(field_spec.get("field", "")).strip()
                    if field_spec.get("value") is not None:
                        explicit_value = str(field_spec.get("value"))
                else:
                    target_field = str(field_spec).strip()

                if not target_field:
                    continue
                if source_key == "sex_m_checkbox" and str(derived.get("sex", "")).upper() == "M":
                    if explicit_value is not None:
                        text_field_values[target_field] = explicit_value
                    else:
                        mapped_checkbox_fields.append(target_field)
                    continue
                if source_key == "sex_f_checkbox" and str(derived.get("sex", "")).upper() == "F":
                    if explicit_value is not None:
                        text_field_values[target_field] = explicit_value
                    else:
                        mapped_checkbox_fields.append(target_field)
                    continue
                value = str(derived.get(source_key, "")).strip()
                if value:
                    text_field_values[target_field] = value

        text_field_map = template_cfg.get("text_field_map", {})
        if not mapping_override and text_field_map:
            text_field_values = {
                field_name: str(derived.get(source_key, "")).strip()
                for source_key, field_name in text_field_map.items()
                if str(derived.get(source_key, "")).strip()
            }
        elif not mapping_override:
            alias_values = PDFPrefillService._resolve_text_fields_by_alias(annots, derived)
            if alias_values:
                text_field_values.update(alias_values)
            # Anchor patient fields to approximate page coordinates, then resolve nearest text widgets.
            text_by_anchor = {
                "patient_last_name": ((130, 336), str(derived.get("patient_last_name", "")).strip()),
                "patient_first_name": ((330, 336), str(derived.get("patient_first_name", "")).strip()),
                "address": ((150, 317), str(derived.get("address", "")).strip()),
                "phone_number": ((420, 282), str(derived.get("phone_number", "")).strip()),
                "date_of_birth": ((355, 265), str(derived.get("date_of_birth", "")).strip()),
                "health_number": ((310, 246), str(derived.get("health_number", "")).strip()),
                "service_date": ((98, 223), str(derived.get("service_date", "")).strip()),
                "clinician_name": ((90, 542), str(derived.get("clinician_name", "")).strip()),
                "clinician_number": ((95, 523), str(derived.get("clinician_number", "")).strip()),
                "additional_info": ((90, 503), str(derived.get("additional_info", "")).strip()),
                "other_tests": ((250, 520), str(derived.get("other_tests", "")).strip()),
            }
            for field_name, field_value in PDFPrefillService._resolve_text_fields_by_coords(annots, text_by_anchor).items():
                text_field_values.setdefault(field_name, field_value)

        checkbox_field_names = list(template_cfg.get("checkbox_field_names", [])) if not mapping_override else mapped_checkbox_fields
        if not mapping_override and not checkbox_field_names:
            checkbox_points = [(m.get("x"), m.get("y")) for m in template_overlay.get("checkbox_marks", [])]
            checkbox_field_names = PDFPrefillService._resolve_checkbox_fields_by_coords(annots, checkbox_points)

        if strict_mode and not text_field_values and not checkbox_field_names:
            raise ValueError("No mapped values could be resolved. Check template field mapping.")

        if mapping_override or text_field_map or checkbox_field_names:
            merged_values = dict(text_field_values)
            for field_name in checkbox_field_names:
                on_state = PDFPrefillService._resolve_checkbox_on_state(annots, field_name)
                if on_state:
                    merged_values[field_name] = on_state
            try:
                writer.update_page_form_field_values(page, merged_values, auto_regenerate=True)
            except TypeError:
                writer.update_page_form_field_values(page, merged_values)
            # Ensure checkbox appearance state is explicitly marked as selected.
            PDFPrefillService._apply_widget_values(page, {}, checkbox_field_names=checkbox_field_names)
        else:
            PDFPrefillService._apply_widget_values(page, text_field_values, checkbox_field_names=checkbox_field_names)
            if checkbox_field_names:
                PDFPrefillService._apply_widget_values(page, {}, checkbox_field_names=checkbox_field_names)

        writer.set_need_appearances_writer(True)

        with output_path.open("wb") as out_stream:
            writer.write(out_stream)

    @staticmethod
    def _overlay_flat_pdf(
        template: str | PdfReader,
        output_path: Path,
        profile_data: dict[str, Any],
        template_key: str | None = None,
    ) -> None:
        writer = PdfWriter(clone_from=template)
        first_page = writer.pages[0]
        template_overlay = build_template_overlay(template_key or "", profile_data)
        template_cfg = get_template_or_none(template_key or "") or {}
        derived = PDFPrefillService._derive_profile_values(profile_data, template_overlay.get("other_tests_text", ""))

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
            value = str(derived.get(field, "")).strip()
            if value:
                c.drawString(x, y, value)

        text_field_map = template_cfg.get("text_field_map", {})
        checkbox_field_names = template_cfg.get("checkbox_field_names", [])
        if text_field_map or checkbox_field_names:
            rects = PDFPrefillService._widget_rects_by_name(first_page)
            for source_key, field_name in text_field_map.items():
                value = str(derived.get(source_key, "")).strip()
                rect = rects.get(field_name)
                if value and rect:
                    c.drawString(float(rect[0]) + 2, float(rect[1]) + 2, value)

            for field_name in checkbox_field_names:
                rect = rects.get(field_name)
                if rect:
                    c.drawString(float(rect[0]) + 1, float(rect[1]) + 1, "X")
        else:
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
    def _overlay_fixed_layout(
        template: str | PdfReader,
        output_path: Path,
        profile_data: dict[str, Any],
        strict_field_mapping: dict[str, object] | None = None,
    ) -> None:
        """
        Deterministic write mode for same-structure templates.
        Uses fixed coordinates aligned to the Ontario requisition structure.
        """
        writer = PdfWriter(clone_from=template)
        first_page = writer.pages[0]
        values = PDFPrefillService._derive_profile_values(profile_data, "")

        field_id_to_position = {
            "Text_11": (240.2175, 624.62866),
            "Text_12": (387.22498, 624.62866),
            "Text_13": (474.285, 625.09564),
            "Text_14": (534.1875, 624.62866),
            "Text_15": (564.3668, 624.62866),
            "Text_16": (240.2175, 598.2717),
            "Text_17": (269.745, 598.27167),
            "Text_18": (453.43, 598.74),
            "Text_19": (491.66498, 598.74),
            "Text_20": (240.2175, 572.61066),
            "Text_21": (240.2175, 544.30304),
            "Text_22": (416.8957, 544.30365),
            "Text_50": (239.33499, 470.4525),
            "Date_2": (343.2075, 125.332504),
        }
        radio_value_to_position = {
            # Sex radio buttons (M/F) in patient header section.
            # Previous values were mistakenly mapped to lower form checkboxes.
            "1": (421.02814, 626.5888),
            "2": (449.96674, 626.5875),
        }
        mapping = strict_field_mapping or {}

        packet = io.BytesIO()
        c = canvas.Canvas(packet, pagesize=letter)
        c.setFont("Helvetica", 9)

        if mapping:
            for source_key, field_spec in mapping.items():
                target_field = ""
                target_value = None
                if isinstance(field_spec, dict):
                    target_field = str(field_spec.get("field", "")).strip()
                    target_value = str(field_spec.get("value")) if field_spec.get("value") is not None else None
                else:
                    target_field = str(field_spec).strip()

                if not target_field:
                    continue

                if source_key in ("sex_m_checkbox", "sex_f_checkbox"):
                    sex = str(values.get("sex", "")).upper()
                    if source_key == "sex_m_checkbox" and sex != "M":
                        continue
                    if source_key == "sex_f_checkbox" and sex != "F":
                        continue
                    radio_key = target_value or ("1" if source_key == "sex_m_checkbox" else "2")
                    pos = radio_value_to_position.get(radio_key)
                    if pos:
                        c.drawString(float(pos[0]) + 1, float(pos[1]) + 1, "X")
                    continue

                value = str(values.get(source_key, "")).strip()
                pos = field_id_to_position.get(target_field)
                if value and pos:
                    c.drawString(float(pos[0]) + 1, float(pos[1]) + 2, value)
        else:
            # Minimal fallback if mapping file is unavailable.
            if values.get("patient_last_name"):
                c.drawString(241.2175, 574.61066, values["patient_last_name"])
            if values.get("patient_first_name"):
                c.drawString(241.2175, 546.30304, values["patient_first_name"])

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
    def _resolve_text_fields_by_alias(annots: list, values: dict[str, str]) -> dict[str, str]:
        aliases = {
            "patient_last_name": ["lastname", "last_name", "surname", "familyname"],
            "patient_first_name": ["firstname", "first_name", "givenname", "given_name"],
            "health_number": ["healthnumber", "health_card", "insurance", "ohip"],
            "date_of_birth": ["dateofbirth", "dob", "birthdate"],
            "service_date": ["servicedate", "dateofservice", "collectiondate"],
            "phone_number": ["phone", "telephone", "contactnumber"],
            "address": ["address", "street"],
        }
        resolved: dict[str, str] = {}
        used: set[str] = set()

        for annot_ref in annots:
            annot = annot_ref.get_object()
            if str(annot.get("/FT") or "") != "/Tx":
                continue
            name = str(annot.get("/T") or "")
            token = name.lower().replace(" ", "").replace("-", "").replace("_", "")
            if not token:
                continue
            for source_key, keys in aliases.items():
                source_value = str(values.get(source_key, "")).strip()
                if not source_value:
                    continue
                if any(key in token for key in keys) and name not in used:
                    resolved[name] = source_value
                    used.add(name)
                    break

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

    @staticmethod
    def _resolve_checkbox_on_state(annots: list, field_name: str) -> str | None:
        for annot_ref in annots:
            annot = annot_ref.get_object()
            if str(annot.get("/T") or "") != field_name or str(annot.get("/FT") or "") != "/Btn":
                continue
            ap = annot.get("/AP", {}).get("/N", {})
            if hasattr(ap, "keys"):
                for state_name in ap.keys():
                    if str(state_name) != "/Off":
                        return str(state_name)
        return None

    @staticmethod
    def _widget_rects_by_name(page) -> dict[str, list]:
        rects: dict[str, list] = {}
        for annot_ref in page.get("/Annots", []):
            annot = annot_ref.get_object()
            name = str(annot.get("/T") or "")
            rect = annot.get("/Rect")
            if name and rect:
                rects[name] = rect
        return rects

    @staticmethod
    def _derive_profile_values(profile_data: dict[str, Any], other_tests_text: str) -> dict[str, str]:
        values = {k: str(v) for k, v in profile_data.items() if v is not None}
        if not values.get("patient_first_name"):
            values["patient_first_name"] = str(profile_data.get("first_and_middle_names", "")).strip()
        if not values.get("patient_last_name"):
            values["patient_last_name"] = str(profile_data.get("last_name", "")).strip()
        first_middle = str(values.get("patient_first_name", "")).strip()
        if first_middle:
            split_idx = -1
            if len(first_middle) > 24:
                midpoint = len(first_middle) // 2
                left_space = first_middle.rfind(" ", 0, midpoint + 1)
                right_space = first_middle.find(" ", midpoint)
                candidates = [idx for idx in [left_space, right_space] if idx != -1]
                if candidates:
                    split_idx = min(candidates, key=lambda x: abs(x - midpoint))
            if split_idx == -1:
                values["patient_first_name_left"] = first_middle
                values["patient_first_name_right"] = ""
            else:
                values["patient_first_name_left"] = first_middle[:split_idx].strip()
                values["patient_first_name_right"] = first_middle[split_idx + 1 :].strip()
        date_of_birth = str(profile_data.get("date_of_birth", "")).strip().replace("/", "-")
        dob_parts = date_of_birth.split("-") if date_of_birth else []
        if len(dob_parts) == 3:
            values["dob_year"], values["dob_month"], values["dob_day"] = dob_parts[0], dob_parts[1], dob_parts[2]

        phone_digits = "".join(ch for ch in str(profile_data.get("phone_number", "")) if ch.isdigit())
        if len(phone_digits) >= 10:
            values["phone_area"] = phone_digits[:3]
            values["phone_rest"] = phone_digits[3:10]

        values.setdefault("province", "ON")
        values.setdefault("service_time", "09:00")
        values["other_tests"] = str(profile_data.get("other_tests", "")).strip() or str(other_tests_text).strip()
        return values

