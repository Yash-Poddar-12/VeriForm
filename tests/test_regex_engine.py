import pytest
from veriform.models.schemas import FieldSchema
from veriform.inference.dynamic_infer import InferredConstraints
from veriform.schemas.mutations import ProbeResult, MutationCategory
from veriform.synthesizer.regex_engine import RegexEngine

@pytest.fixture
def base_field():
    return FieldSchema(
        field_id="field_1",
        run_id="run_1",
        name="test_field",
        type="text"
    )

def test_semantic_phone_synthesis(base_field):
    base_field.semantic_type = "phone"
    constraints = InferredConstraints(
        field_id="field_1",
        required=True,
        exact_length=10,
        allowed_charset="digits",
        prefix_constraint="[6-9]",
        confidence=0.85
    )
    
    # Generate mock results for examples
    results = [
        ProbeResult(mutation_id="phone_exact_1", field_id="field_1", probe_value="9876543210", accepted=True, submit_enabled=True),
        ProbeResult(mutation_id="phone_underflow_1", field_id="field_1", probe_value="987654321", accepted=False, submit_enabled=False),
        ProbeResult(mutation_id="phone_prefix_1", field_id="field_1", probe_value="0876543210", accepted=False, submit_enabled=False)
    ]
    
    engine = RegexEngine()
    result = engine.synthesize(base_field, constraints, results)
    
    assert result.regex == "^[6-9][0-9]{9}$"
    assert "9876543210" in result.accepted_examples
    assert "987654321" in result.rejected_examples
    assert result.confidence >= 0.95  # boosted by semantic handler
    assert "10 digit Indian mobile" in result.description

def test_generic_synthesis(base_field):
    constraints = InferredConstraints(
        field_id="field_1",
        min_length=5,
        max_length=15,
        allowed_charset="alpha",
        confidence=0.7
    )
    results = [
        ProbeResult(mutation_id="gen_exact_1", field_id="field_1", probe_value="ABCDEFG", accepted=True, submit_enabled=True)
    ]
    
    engine = RegexEngine()
    result = engine.synthesize(base_field, constraints, results)
    
    assert result.regex == "^[A-Za-z]{5,15}$"
    assert "ABCDEFG" in result.accepted_examples
    assert result.confidence == 0.7

def test_contradiction_detection(base_field):
    constraints = InferredConstraints(
        field_id="field_1",
        exact_length=10,
        confidence=0.8
    )
    results = [
        # Contradiction: we inferred 10, but 11 was accepted
        ProbeResult(mutation_id="gen_exact_1", field_id="field_1", probe_value="12345678901", accepted=True, submit_enabled=True)
    ]
    
    engine = RegexEngine()
    result = engine.synthesize(base_field, constraints, results)
    
    assert result.confidence < 0.8  # Penalty applied
    assert any("WARNING: exact_length inferred as 10" in ev for ev in result.evidence)
