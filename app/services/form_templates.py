from __future__ import annotations

from typing import Any


FORM_TEMPLATES: dict[str, dict[str, Any]] = {
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

