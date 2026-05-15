from __future__ import annotations

from veriform.detector.detector import detect_fields

from fake_playwright import FakePage


async def test_detect_fields_extracts_form_controls() -> None:
    page = FakePage(
        controls=[
            {
                "name": "mobile_number",
                "dom_id": "mobile",
                "type": "text",
                "label": "Mobile Number",
                "placeholder": "10-digit number",
                "context_text": "Include country code if required",
                "required": True,
                "min_length": 10,
                "max_length": 10,
                "pattern": "[0-9]{10}",
                "min_val": None,
                "max_val": None,
            },
            {
                "name": "dob",
                "dom_id": "dob",
                "type": "date",
                "label": "Date of Birth",
                "required": True,
                "min_length": None,
                "max_length": None,
                "pattern": None,
                "min_val": None,
                "max_val": None,
            },
        ]
    )

    fields = await detect_fields(page=page, run_id="run-1")

    assert len(fields) == 2
    assert fields[0].field_id == "field_001"
    assert fields[0].name == "mobile_number"
    assert fields[0].placeholder == "10-digit number"
    assert fields[0].context_text == "Include country code if required"
    assert fields[0].max_length == 10
    assert fields[1].type == "date"
