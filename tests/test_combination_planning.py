from __future__ import annotations
import pytest
"""Tests for candidate generation and deterministic combination planning."""


from veriform.constraint_ir.adapters.translator import translate_to_profile
from veriform.generator.candidate_generator import build_candidate_inputs
from veriform.generator.combination_planner import create_combination_plan
from veriform.models.schemas import CandidateInputSchema, FieldSchema


@pytest.mark.asyncio
async def test_build_candidate_inputs_creates_required_empty_case() -> None:
    fields = [
        FieldSchema(
            field_id="field_001",
            run_id="run-1",
            name="email",
            type="email",
            required=True,
        )
    ]
    from veriform.models.schemas import InferredConstraintSchema, ConfidenceScoreSchema
    constraint = InferredConstraintSchema(
        constraint_id="c1",
        run_id="run-1",
        field_id="field_001",
        semantic_type="email",
        likely_format="",
        confidence=ConfidenceScoreSchema(score=0.9, source="deterministic_hint")
    )
    profiles = [translate_to_profile(fields[0], constraint)]
    candidates = await build_candidate_inputs(fields=fields, constraint_profiles=profiles)

    categories = {candidate.category for candidate in candidates}
    assert {"valid", "malformed", "invalid", "empty", "whitespace", "suspicious"} <= categories


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_create_combination_plan_dedupes_and_caps() -> None:
    fields = [
        FieldSchema(field_id="field_001", run_id="run-1", name="email", type="email")
    ]
    profiles = [translate_to_profile(fields[0])]
    candidates = await build_candidate_inputs(fields=fields, constraint_profiles=profiles)
    duplicated = candidates + candidates

    plan = create_combination_plan(run_id="run-1", candidates=duplicated, max_combinations=1)

    assert len(plan.selected_candidates) == 1
    assert plan.strategy == "single-page-deterministic-priority"


@pytest.mark.asyncio
async def test_create_combination_plan_keeps_highest_priority_duplicate() -> None:
    candidates = [
        CandidateInputSchema(
            candidate_id="cand-low",
            run_id="run-1",
            field_id="field_001",
            input_value="same",
            category="valid",
            expected_outcome="accept",
            priority_score=0.2,
        ),
        CandidateInputSchema(
            candidate_id="cand-high",
            run_id="run-1",
            field_id="field_001",
            input_value="same",
            category="valid",
            expected_outcome="accept",
            priority_score=0.9,
        ),
    ]

    plan = create_combination_plan(run_id="run-1", candidates=candidates, max_combinations=5)

    assert [candidate.candidate_id for candidate in plan.selected_candidates] == ["cand-high"]


@pytest.mark.asyncio
async def test_create_combination_plan_prefers_field_coverage_under_cap() -> None:
    candidates = [
        CandidateInputSchema(
            candidate_id="field-1-best",
            run_id="run-1",
            field_id="field_001",
            input_value="a",
            category="valid",
            expected_outcome="accept",
            priority_score=0.99,
        ),
        CandidateInputSchema(
            candidate_id="field-1-next",
            run_id="run-1",
            field_id="field_001",
            input_value="b",
            category="boundary",
            expected_outcome="reject",
            priority_score=0.98,
        ),
        CandidateInputSchema(
            candidate_id="field-2-best",
            run_id="run-1",
            field_id="field_002",
            input_value="c",
            category="valid",
            expected_outcome="accept",
            priority_score=0.7,
        ),
    ]

    plan = create_combination_plan(run_id="run-1", candidates=candidates, max_combinations=2)

    assert [candidate.candidate_id for candidate in plan.selected_candidates] == [
        "field-1-best",
        "field-2-best",
    ]


@pytest.mark.asyncio
async def test_create_combination_plan_enforces_global_hard_cap() -> None:
    candidates = [
        CandidateInputSchema(
            candidate_id=f"cand-{index:03d}",
            run_id="run-1",
            field_id=f"field_{index:03d}",
            input_value=f"value-{index}",
            category="valid",
            expected_outcome="accept",
            priority_score=0.9,
        )
        for index in range(1, 80)
    ]

    plan = create_combination_plan(run_id="run-1", candidates=candidates, max_combinations=999)

    assert plan.max_combinations == 40
    assert len(plan.selected_candidates) == 40
