import pytest
from pydantic import ValidationError
# pyrefly: ignore [missing-import]
from veriform.constraint_ir.models.base import ImmutableIRModel

class DummyModel(ImmutableIRModel):
    string_field: str
    int_field: int

def test_model_is_frozen():
    model = DummyModel(string_field="test", int_field=1)
    
    with pytest.raises(ValidationError) as exc_info:
        model.string_field = "mutated"
        
    assert "Instance is frozen" in str(exc_info.value)

def test_extra_fields_forbidden():
    with pytest.raises(ValidationError) as exc_info:
        DummyModel(string_field="test", int_field=1, extra_field="not allowed")
        
    assert "Extra inputs are not permitted" in str(exc_info.value)

def test_strict_typing_enforced():
    with pytest.raises(ValidationError) as exc_info:
        # strict=True prevents coercion from string to integer
        DummyModel(string_field="test", int_field="1")
        
    assert "Input should be a valid integer" in str(exc_info.value)