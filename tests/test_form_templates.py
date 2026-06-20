from app.services.form_templates import build_template_overlay, get_template_or_none, list_templates


def test_template_registry_contains_diabetes():
    keys = {item["key"] for item in list_templates()}
    assert "diabetes_blood_test" in keys


def test_build_template_overlay_applies_default_other_tests():
    overlay = build_template_overlay("thyroid_monitoring", {})
    assert "TSH" in overlay["other_tests_text"]


def test_build_template_overlay_merges_custom_checkbox_marks():
    overlay = build_template_overlay(
        "diabetes_blood_test",
        {"template_checkbox_marks": [{"x": 100, "y": 100, "label": "Custom"}]},
    )
    assert any(mark.get("label") == "Custom" for mark in overlay["checkbox_marks"])


def test_unknown_template_returns_none():
    assert get_template_or_none("does_not_exist") is None

