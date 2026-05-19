"""Schema validation tests for newly added AI-assisted models."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veriform.models.schemas import (
    CandidateInputSchema,
    CombinationPlanSchema,
    ConfidenceScoreSchema,
    InferredConstraintSchema,
)


def test_confidence_score_bounds() -> None:
    score = ConfidenceScoreSchema(score=0.5, source="deterministic_hint")
    assert score.score == 0.5

    with pytest.raises(ValidationError):
        ConfidenceScoreSchema(score=1.5, source="deterministic_hint")


def test_inferred_constraint_schema_contract() -> None:
    constraint = InferredConstraintSchema(
        constraint_id="constraint_001",
        run_id="run-1",
        field_id="field_001",
        semantic_type="email",
        likely_format="local@domain.tld",
        confidence=ConfidenceScoreSchema(score=0.7, source="deterministic_hint"),
    )
    assert constraint.field_id == "field_001"


def test_candidate_input_expected_outcome_validation() -> None:
    with pytest.raises(ValidationError):
        CandidateInputSchema(
            candidate_id="candidate_001",
            run_id="run-1",
            field_id="field_001",
            input_value="value",
            category="valid",
            expected_outcome="unknown",
        )


def test_combination_plan_schema_contract() -> None:
    candidate = CandidateInputSchema(
        candidate_id="candidate_001",
        run_id="run-1",
        field_id="field_001",
        input_value="value",
        category="valid",
        expected_outcome="accept",
        priority_score=0.3,
    )
    plan = CombinationPlanSchema(
        plan_id="plan_run-1",
        run_id="run-1",
        strategy="single-page-deterministic-priority",
        max_combinations=10,
        selected_candidates=[candidate],
    )
    assert plan.max_combinations == 10
    