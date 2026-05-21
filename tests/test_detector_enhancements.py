import pytest
from unittest.mock import AsyncMock
from veriform.detector.detector import detect_fields
from veriform.detector.semantic_classifier import SemanticClassifier
from veriform.models.schemas import FieldSchema

@pytest.fixture
def mock_html_payload():
    return [
        {
            "name": "mobile_number",
            "dom_id": "mobile",
            "type": "text",
            "label": "Mobile Number:*",
            "placeholder": "Enter mobile",
            "inputmode": "tel",
            "autocomplete": "tel",
            "required": "true",
            "minlength": "10",
            "maxlength": "10",
            "validation_message_containers": ["Invalid number"]
        },
        {
            "name": "email_addr",
            "dom_id": "email",
            "type": "email",
            "label": "Email Address",
            "required": None
        },
        {
            "name": "random_field",
            "dom_id": "fld_1",
            "type": "text",
            "placeholder": "Enter something"
        }
    ]

@pytest.mark.asyncio
async def test_detector_extraction_and_classification(mock_html_payload):
    # Mock playwright page
    page = AsyncMock()
    page.evaluate.return_value = mock_html_payload
    
    fields = await detect_fields(page, "run_123")
    
    assert len(fields) == 3
    
    # 1. Phone Field
    phone = fields[0]
    assert phone.name == "mobile_number"
    assert phone.label == "mobile number" # Normalized (lowercase, stripped asterisks/colons)
    assert phone.required is True
    assert phone.min_length == 10
    assert phone.max_length == 10
    assert phone.inputmode == "tel"
    assert phone.autocomplete == "tel"
    assert phone.semantic_type == "phone"
    assert phone.semantic_confidence > 0.8
    assert "inputmode=tel" in phone.matched_signals
    assert phone.validation_message_containers == ["Invalid number"]
    
    # 2. Email Field
    email = fields[1]
    assert email.name == "email_addr"
    assert email.required is False
    assert email.semantic_type == "email"
    assert email.semantic_confidence > 0.8
    assert "type=email" in email.matched_signals
    
    # 3. Unclassified Field
    random = fields[2]
    assert random.name == "random_field"
    assert random.semantic_type is None
    assert random.semantic_confidence == 0.0
