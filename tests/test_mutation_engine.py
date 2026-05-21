import pytest
from veriform.models.schemas import FieldSchema
from veriform.mutator.mutation_engine import MutationEngine
from veriform.schemas.mutations import MutationCategory, MutationProfile

@pytest.fixture
def phone_field():
    return FieldSchema(
        field_id="field_phone",
        run_id="run_1",
        name="mobile_number",
        type="text",
        min_length=10,
        max_length=10,
        semantic_type="phone"
    )

@pytest.fixture
def email_field():
    return FieldSchema(
        field_id="field_email",
        run_id="run_1",
        name="user_email",
        type="email",
        semantic_type="email"
    )

def test_deterministic_generation(phone_field):
    engine1 = MutationEngine(MutationProfile.BALANCED)
    engine2 = MutationEngine(MutationProfile.BALANCED)
    
    probes1 = engine1.generate_for_field(phone_field)
    probes2 = engine2.generate_for_field(phone_field)
    
    assert len(probes1) == len(probes2)
    assert probes1[0].mutation_id == probes2[0].mutation_id
    assert probes1[-1].value == probes2[-1].value

def test_boundary_correctness(phone_field):
    engine = MutationEngine(MutationProfile.BALANCED)
    probes = engine.generate_for_field(phone_field)
    
    underflow = next(p for p in probes if p.category == MutationCategory.BOUNDARY_UNDERFLOW)
    exact = next(p for p in probes if p.category == MutationCategory.BOUNDARY_EXACT and len(p.value) == 10)
    overflow = next(p for p in probes if p.category == MutationCategory.BOUNDARY_OVERFLOW)
    
    assert len(underflow.value) == 9
    assert len(exact.value) == 10
    assert len(overflow.value) == 11
    # Since it's a phone field, boundary values should be generated using digits (base_char '9')
    assert underflow.value == "9" * 9

def test_semantic_aware_selection(email_field):
    engine = MutationEngine(MutationProfile.BALANCED)
    probes = engine.generate_for_field(email_field)
    
    structure_probes = [p for p in probes if p.category == MutationCategory.STRUCTURE_PROBE]
    assert len(structure_probes) == 3
    assert structure_probes[0].value == "test@example.com"
    assert structure_probes[1].value == "testexample.com"

def test_mutation_caps(phone_field):
    # Lightweight should cap at 8
    engine_light = MutationEngine(MutationProfile.LIGHTWEIGHT)
    probes_light = engine_light.generate_for_field(phone_field)
    assert len(probes_light) == 8
    
    # Balanced should cap at 20 (or max possible for phone)
    engine_balanced = MutationEngine(MutationProfile.BALANCED)
    probes_balanced = engine_balanced.generate_for_field(phone_field)
    assert len(probes_balanced) <= 20
    assert len(probes_balanced) > 8
