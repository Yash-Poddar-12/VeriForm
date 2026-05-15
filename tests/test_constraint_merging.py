"""Placeholder tests for deterministic constraint merging."""

from __future__ import annotations

from veriform.constraints.inferred_constraints import merge_inferred_constraints
from veriform.models.schemas import ConfidenceScoreSchema, FieldSchema, InferredConstraintSchema


def test_merge_inferred_constraints_groups_by_field() -> None:
    fields = [
        FieldSchema(field_id="field_001", run_id="run-1", name="email", type="text"),
        FieldSchema(field_id="field_002", run_id="run-1", name="phone", type="text"),
    ]
    constraints = [
        InferredConstraintSchema(
            constraint_id="c1",
            run_id="run-1",
            field_id="field_001",
            semantic_type="email",
            likely_format="local@domain.tld",
            confidence=ConfidenceScoreSchema(score=0.9, source="deterministic_hint"),
        ),
        InferredConstraintSchema(
            constraint_id="c2",
            run_id="run-1",
            field_id="field_003",
            semantic_type="ignore",
            likely_format="none",
            confidence=ConfidenceScoreSchema(score=0.1, source="deterministic_hint"),
        ),
    ]

    merged = merge_inferred_constraints(fields=fields, inferred_constraints=constraints)

    assert list(merged.keys()) == ["field_001", "field_002"]
    assert len(merged["field_001"]) == 1
    assert merged["field_002"] == []
