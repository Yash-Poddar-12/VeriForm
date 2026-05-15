"""Placeholder tests for AI inference modules."""

from __future__ import annotations

from veriform.ai_inference.confidence_ranker import rank_constraints_by_confidence
from veriform.ai_inference.field_classifier import classify_fields
from veriform.ai_inference.provider_interface import InferenceContext
from veriform.ai_inference.semantic_parser import parse_semantic_hints
from veriform.models.schemas import ConfidenceScoreSchema, FieldSchema, InferredConstraintSchema


def test_parse_semantic_hints_normalizes_tokens() -> None:
    hints = parse_semantic_hints("User_Name", "email-address")
    assert hints.tokens == ("user", "name", "email", "address")


def test_classify_fields_returns_deterministic_constraints() -> None:
    fields = [
        FieldSchema(
            field_id="field_001",
            run_id="run-1",
            name="email",
            type="text",
        )
    ]
    context = InferenceContext(run_id="run-1", target_url="https://example.com")

    constraints = classify_fields(fields=fields, context=context)

    assert len(constraints) == 1
    assert constraints[0].semantic_type == "email"
    assert constraints[0].confidence.score == 0.74


def test_rank_constraints_by_confidence_orders_descending() -> None:
    constraints = [
        InferredConstraintSchema(
            constraint_id="c1",
            run_id="run-1",
            field_id="field_001",
            semantic_type="generic_text",
            likely_format="free-text",
            confidence=ConfidenceScoreSchema(score=0.4, source="x"),
        ),
        InferredConstraintSchema(
            constraint_id="c2",
            run_id="run-1",
            field_id="field_001",
            semantic_type="email",
            likely_format="local@domain.tld",
            confidence=ConfidenceScoreSchema(score=0.8, source="x"),
        ),
    ]

    ranked = rank_constraints_by_confidence(constraints)
    assert [item.constraint_id for item in ranked] == ["c2", "c1"]
