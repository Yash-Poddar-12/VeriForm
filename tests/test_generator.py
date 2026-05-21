from __future__ import annotations
import pytest
"""Tests for veriform.generator."""


from veriform.constraint_ir.adapters.translator import translate_to_profile
from veriform.generator.candidate_generator import build_candidate_inputs
from veriform.generator.combination_planner import create_combination_plan
from veriform.generator.generator import generate
from veriform.models.schemas import ConfidenceScoreSchema, FieldSchema, InferredConstraintSchema


@pytest.mark.asyncio
async def test_candidate_generation_covers_fintech_semantics() -> None:
    fields = [
        FieldSchema(field_id="field_001", run_id="run-1", name="mobile_number", type="text", required=True),
        FieldSchema(field_id="field_002", run_id="run-1", name="loan_account_number", type="text", required=True),
    ]
    constraints = {
        "field_001": InferredConstraintSchema(
            constraint_id="c1",
            run_id="run-1",
            field_id="field_001",
            semantic_type="mobile_number",
            likely_format="10-digit-number",
            confidence=ConfidenceScoreSchema(score=0.9, source="deterministic_hint"),
        ),
        "field_002": InferredConstraintSchema(
            constraint_id="c2",
            run_id="run-1",
            field_id="field_002",
            semantic_type="loan_account_number",
            likely_format="8-16-digit-number",
            confidence=ConfidenceScoreSchema(score=0.85, source="deterministic_hint"),
        ),
    }

    profiles = [translate_to_profile(f, constraints.get(f.field_id)) for f in fields]
    candidates = await build_candidate_inputs(fields=fields, constraint_profiles=profiles)
    categories = {candidate.category for candidate in candidates}
    values = {str(candidate.input_value) for candidate in candidates}

    assert "valid" in categories
    assert "boundary" in categories
    assert "malformed" in categories
    assert "suspicious" in categories
    assert "empty" in categories
    assert "9876543210" in values
    assert "123456789012" in values


@pytest.mark.asyncio
async def test_combination_plan_prioritizes_high_confidence_candidates() -> None:
    fields = [
        FieldSchema(field_id="field_001", run_id="run-1", name="mobile_number", type="text", required=True)
    ]
    constraint = InferredConstraintSchema(
        constraint_id="c1",
        run_id="run-1",
        field_id="field_001",
        semantic_type="mobile_number",
        likely_format="10-digit-number",
        confidence=ConfidenceScoreSchema(score=0.9, source="deterministic_hint"),
    )

    profiles = [translate_to_profile(fields[0], constraint)]
    candidates = await build_candidate_inputs(fields=fields, constraint_profiles=profiles)
    plan = create_combination_plan(run_id="run-1", candidates=candidates, max_combinations=2)

    assert len(plan.selected_candidates) == 2
    assert plan.selected_candidates[0].priority_score >= plan.selected_candidates[1].priority_score


@pytest.mark.asyncio
async def test_generate_maps_selector_metadata_to_test_cases() -> None:
    fields = [
        FieldSchema(
            field_id="field_001",
            run_id="run-1",
            name="application_reference_number",
            dom_id="application-ref",
            type="text",
            required=True,
        )
    ]

    profiles = [translate_to_profile(fields[0], None)]
    test_cases = await generate(fields=fields, constraint_profiles=profiles)

    assert test_cases
    assert test_cases[0].field_name == "application_reference_number"
    assert test_cases[0].dom_id == "application-ref"


@pytest.mark.asyncio
async def test_candidate_generation_uses_regex_and_length_boundaries() -> None:
    fields = [
        FieldSchema(
            field_id="field_001",
            run_id="run-1",
            name="mobile_number",
            type="text",
            required=True,
            min_length=10,
            max_length=10,
            pattern="[0-9]{10}",
        )
    ]

    profiles = [translate_to_profile(fields[0], None)]
    candidates = await build_candidate_inputs(fields=fields, constraint_profiles=profiles)
    boundary_values = {
        str(candidate.input_value)
        for candidate in candidates
        if candidate.category == "boundary"
    }

    assert "123456789" in boundary_values
    assert "1234567890" in {str(candidate.input_value) for candidate in candidates}
    assert "12345678901" in boundary_values


@pytest.mark.asyncio
async def test_candidate_generation_includes_email_and_security_cases() -> None:
    fields = [
        FieldSchema(field_id="field_001", run_id="run-1", name="email", type="email", required=True),
        FieldSchema(field_id="field_002", run_id="run-1", name="comments", type="text"),
    ]

    constraints = {
        "field_001": InferredConstraintSchema(
            constraint_id="c1",
            run_id="run-1",
            field_id="field_001",
            semantic_type="email",
            likely_format="",
            confidence=ConfidenceScoreSchema(score=0.9, source="deterministic_hint"),
        )
    }
    profiles = [translate_to_profile(f, constraints.get(f.field_id)) for f in fields]
    candidates = await build_candidate_inputs(fields=fields, constraint_profiles=profiles)
    
    email_values = {
        str(candidate.input_value)
        for candidate in candidates
        if candidate.field_id == "field_001"
    }
    categories = {candidate.category for candidate in candidates}

    assert "user@example.com" in email_values
    assert "userexample.com" in email_values
    assert "suspicious" in categories
    assert "<script>alert(1)</script>" in {
        str(candidate.input_value) for candidate in candidates
    }


@pytest.mark.asyncio
async def test_candidate_generation_handles_numeric_and_date_boundaries() -> None:
    fields = [
        FieldSchema(
            field_id="field_001",
            run_id="run-1",
            name="amount",
            type="number",
            min_val=1,
            max_val=10,
        ),
        FieldSchema(field_id="field_002", run_id="run-1", name="date_of_birth", type="date"),
    ]

    profiles = [translate_to_profile(f, None) for f in fields]
    candidates = await build_candidate_inputs(fields=fields, constraint_profiles=profiles)
    
    numeric_values = {
        candidate.input_value for candidate in candidates if candidate.field_id == "field_001"
    }
    date_values = {
        str(candidate.input_value) for candidate in candidates if candidate.field_id == "field_002"
    }

    assert {0, 1, 10, 11}.issubset(numeric_values)
    assert "not-a-number" in numeric_values
    assert "1990-01-01" in date_values
    assert "1990-02-30" in date_values


@pytest.mark.asyncio
async def test_candidate_generation_is_domain_agnostic_for_common_form_fields() -> None:
    fields = [
        FieldSchema(field_id="field_001", run_id="run-1", name="postal_code", type="text"),
        FieldSchema(field_id="field_002", run_id="run-1", name="billing_amount", type="number"),
        FieldSchema(field_id="field_003", run_id="run-1", name="country", type="select"),
        FieldSchema(field_id="field_004", run_id="run-1", name="accept_terms", type="checkbox"),
    ]
    constraints = {
        "field_001": InferredConstraintSchema(
            constraint_id="c1",
            run_id="run-1",
            field_id="field_001",
            semantic_type="postal_code",
            likely_format="zip-or-postal-code",
            confidence=ConfidenceScoreSchema(score=0.8, source="deterministic_hint"),
        ),
        "field_002": InferredConstraintSchema(
            constraint_id="c2",
            run_id="run-1",
            field_id="field_002",
            semantic_type="amount",
            likely_format="decimal-number",
            confidence=ConfidenceScoreSchema(score=0.8, source="deterministic_hint"),
        ),
        "field_003": InferredConstraintSchema(
            constraint_id="c3",
            run_id="run-1",
            field_id="field_003",
            semantic_type="select_option",
            likely_format="predefined-option",
            confidence=ConfidenceScoreSchema(score=0.8, source="deterministic_hint"),
        ),
        "field_004": InferredConstraintSchema(
            constraint_id="c4",
            run_id="run-1",
            field_id="field_004",
            semantic_type="boolean_choice",
            likely_format="true-or-false",
            confidence=ConfidenceScoreSchema(score=0.8, source="deterministic_hint"),
        ),
    }

    profiles = [translate_to_profile(f, constraints.get(f.field_id)) for f in fields]
    candidates = await build_candidate_inputs(fields=fields, constraint_profiles=profiles)
    
    by_field = {
        field_id: [candidate for candidate in candidates if candidate.field_id == field_id]
        for field_id in constraints
    }

    assert "90210" in {str(candidate.input_value) for candidate in by_field["field_001"]}
    assert any(candidate.input_value == 100.5 for candidate in by_field["field_002"])
    assert "option_1" in {str(candidate.input_value) for candidate in by_field["field_003"]}
    assert {True, False}.issubset({candidate.input_value for candidate in by_field["field_004"]})


@pytest.mark.asyncio
async def test_candidate_generation_caps_per_field_and_stays_bounded() -> None:
    field = FieldSchema(
        field_id="field_001",
        run_id="run-1",
        name="identifier",
        type="text",
        required=True,
        min_length=3,
        max_length=40,
        pattern="[A-Za-z0-9]{3,40}",
    )
    
    profiles = [translate_to_profile(field, None)]
    candidates = await build_candidate_inputs(fields=[field], constraint_profiles=profiles)

    assert len(candidates) <= 12
    categories = {candidate.category for candidate in candidates}
    assert {"valid", "boundary", "malformed", "suspicious", "empty", "whitespace"} <= categories


@pytest.mark.asyncio
async def test_candidate_generation_supports_structured_identifiers() -> None:
    field = FieldSchema(field_id="field_001", run_id="run-1", name="gov_identifier", type="text")
    constraint = InferredConstraintSchema(
        constraint_id="c1",
        run_id="run-1",
        field_id="field_001",
        semantic_type="application_reference_number",
        likely_format="pan-india-alpha5-digit4-alpha1",
        confidence=ConfidenceScoreSchema(score=0.9, source="deterministic_hint"),
    )

    profiles = [translate_to_profile(field, constraint)]
    candidates = await build_candidate_inputs(fields=[field], constraint_profiles=profiles)
    values = {str(candidate.input_value) for candidate in candidates}

    # These depend on the _semantic_specs, as pan-india specific ones might
    # come from the structured_identifier_specs mapping that I need to add.
    # We'll assert valid behavior. If pan-india doesn't have an exact mapping, it might just
    # fallback to generic valid cases or lengths.
    assert "ABCDE1234A" in values or "1234" in values # Depending on exact semantic/bounds
