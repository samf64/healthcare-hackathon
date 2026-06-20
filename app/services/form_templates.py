from __future__ import annotations

from typing import Any


FORM_TEMPLATES: dict[str, dict[str, Any]] = {
    "diabetes-template": {
        "title": "Diabetes Template (Reference-Aligned)",
        "description": "Aligned to your provided Ontario Diabetes reference form placements.",
        "suggested_fields": [
            "patient_last_name",
            "patient_first_name",
            "date_of_birth",
            "health_number",
            "phone_number",
            "address",
            "service_date",
            "other_tests",
        ],
        # Exact widget IDs from user-provided reference PDF.
        "text_field_map": {
            "patient_last_name": "Text_6",
            "patient_first_name": "Text_7",
            "address": "Text_8",
            "health_number": "Text_11",
            "health_version": "Text_12",
            "dob_year": "Text_13",
            "dob_month": "Text_14",
            "dob_day": "Text_15",
            "phone_area": "Text_18",
            "phone_rest": "Text_19",
            "province": "Text_16",
            "service_date": "Date_2",
            "service_time": "Date_1",
            "other_tests": "Text_33",
            "clinician_name": "Text_21",
            "clinician_address": "Text_22",
        },
        "checkbox_field_names": ["Checkbox_2", "Checkbox_7", "Checkbox_8", "Checkbox_21", "Checkbox_49", "Checkbox_51"],
        "other_tests_text": "Insulin",
    },
    "diabetes_blood_test": {
        "title": "Diabetes Blood Test",
        "description": "Diabetes-focused requisition: fasting glucose + HbA1C.",
        "suggested_fields": [
            "patient_last_name",
            "patient_first_name",
            "date_of_birth",
            "health_number",
            "phone_number",
            "service_date",
            "clinician_name",
        ],
        # Coordinates for Ontario requisition checkboxes/lines (tune if form revision changes).
        "checkbox_marks": [
            {"x": 80, "y": 704, "label": "Glucose Fasting"},
            {"x": 80, "y": 690, "label": "HbA1C"},
        ],
        "other_tests_text": "",
    },
    "general_annual_lab": {
        "title": "General Annual Lab Requisition",
        "description": "General yearly panel: CBC, creatinine, lipid assessment.",
        "suggested_fields": [
            "patient_last_name",
            "patient_first_name",
            "date_of_birth",
            "address",
            "health_number",
            "service_date",
            "clinician_name",
            "additional_info",
        ],
        "checkbox_marks": [
            {"x": 80, "y": 676, "label": "CBC"},
            {"x": 80, "y": 662, "label": "Creatinine"},
            {"x": 80, "y": 592, "label": "Lipid Assessment"},
        ],
        "other_tests_text": "Annual monitoring panel",
    },
    "thyroid_monitoring": {
        "title": "Thyroid Monitoring",
        "description": "Template for thyroid follow-up with TSH/T4 as other tests.",
        "suggested_fields": [
            "patient_last_name",
            "patient_first_name",
            "date_of_birth",
            "health_number",
            "service_date",
            "clinician_name",
        ],
        "checkbox_marks": [],
        "other_tests_text": "TSH, Free T4",
    },
}


def list_templates() -> list[dict[str, Any]]:
    return [
        {
            "key": key,
            "title": value["title"],
            "description": value["description"],
            "suggested_fields": value["suggested_fields"],
        }
        for key, value in FORM_TEMPLATES.items()
    ]


def build_preview_profile(template_key: str) -> dict[str, Any]:
    template = get_template_or_none(template_key) or {}
    return {
        "patient_last_name": "Sample",
        "patient_first_name": "Patient",
        "date_of_birth": "1990-01-01",
        "health_number": "0000-000-000",
        "phone_number": "555-000-0000",
        "service_date": "2026-06-20",
        "clinician_name": "Dr Demo",
        "address": "123 Example Street",
        "additional_info": "Template preview only",
        "other_tests": template.get("other_tests_text", ""),
    }


def get_template_or_none(template_key: str) -> dict[str, Any] | None:
    return FORM_TEMPLATES.get(template_key)


def build_template_overlay(template_key: str, profile_data: dict[str, Any]) -> dict[str, Any]:
    template = get_template_or_none(template_key) or {}
    checkbox_marks = list(template.get("checkbox_marks", []))
    custom_marks = profile_data.get("template_checkbox_marks", [])
    if isinstance(custom_marks, list):
        checkbox_marks.extend([m for m in custom_marks if isinstance(m, dict)])

    other_tests = profile_data.get("other_tests") or template.get("other_tests_text", "")
    return {"checkbox_marks": checkbox_marks, "other_tests_text": other_tests}

