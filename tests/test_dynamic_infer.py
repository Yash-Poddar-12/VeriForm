import pytest
from veriform.models.schemas import FieldSchema
from veriform.schemas.mutations import MutationCategory, ProbeResult
from veriform.inference.dynamic_infer import BehavioralInferencer

@pytest.fixture
def phone_field():
    return FieldSchema(
        field_id="field_phone",
        run_id="run_1",
        name="mobile_number",
        type="text",
        semantic_type="phone"
    )

def test_infer_exact_length(phone_field):
    results = [
        ProbeResult(mutation_id="phone_boundary_underflow_1", field_id="field_phone", probe_value="999999999", accepted=False, submit_enabled=False),
        ProbeResult(mutation_id="phone_boundary_exact_1", field_id="field_phone", probe_value="9999999999", accepted=True, submit_enabled=True),
        ProbeResult(mutation_id="phone_boundary_overflow_1", field_id="field_phone", probe_value="99999999999", accepted=False, submit_enabled=False)
    ]
    
    inferencer = BehavioralInferencer()
    constraints = inferencer.infer(phone_field, results)
    
    assert constraints.exact_length == 10
    assert constraints.min_length == 10
    assert constraints.max_length == 10

def test_infer_charsets(phone_field):
    results = [
        ProbeResult(mutation_id="phone_charset_digits_1", field_id="field_phone", probe_value="9999999999", accepted=True, submit_enabled=True),
        ProbeResult(mutation_id="phone_charset_alpha_1", field_id="field_phone", probe_value="AAAAAAAAAA", accepted=False, submit_enabled=False),
        ProbeResult(mutation_id="phone_charset_special_1", field_id="field_phone", probe_value="@@@@@@@@@@", accepted=False, submit_enabled=False)
    ]
    
    inferencer = BehavioralInferencer()
    constraints = inferencer.infer(phone_field, results)
    
    assert constraints.allowed_charset == "digits"

def test_infer_required(phone_field):
    results = [
        ProbeResult(mutation_id="phone_null_like_probe_1", field_id="field_phone", probe_value="", accepted=False, submit_enabled=False)
    ]
    
    inferencer = BehavioralInferencer()
    constraints = inferencer.infer(phone_field, results)
    
    assert constraints.required is True

def test_infer_prefix(phone_field):
    results = [
        ProbeResult(mutation_id="phone_prefix_probe_1", field_id="field_phone", probe_value="9111111111", accepted=True, submit_enabled=True),
        ProbeResult(mutation_id="phone_prefix_probe_2", field_id="field_phone", probe_value="0111111111", accepted=False, submit_enabled=False)
    ]
    
    inferencer = BehavioralInferencer()
    constraints = inferencer.infer(phone_field, results)
    
    assert constraints.prefix_constraint == "[9]"
