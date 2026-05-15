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
            type="email",
            placeholder="name@example.com",
            required=True,
        )
    ]
    context = InferenceContext(run_id="run-1", target_url="https://example.com")

    constraints = classify_fields(fields=fields, context=context)

    assert len(constraints) == 1
    assert constraints[0].semantic_type == "email"
    assert constraints[0].confidence.score >= 0.8


def test_classify_fields_detects_general_form_semantics() -> None:
    fields = [
        FieldSchema(
            field_id="field_001",
            run_id="run-1",
            name="postal_code",
            label="ZIP / Postal Code",
            type="text",
            pattern="[0-9]{5}",
        ),
        FieldSchema(
            field_id="field_002",
            run_id="run-1",
            name="billing_amount",
            label="Amount (USD)",
            type="number",
            min_val=0,
        ),
        FieldSchema(
            field_id="field_003",
            run_id="run-1",
            name="terms_accepted",
            label="I agree to terms",
            type="checkbox",
            required=True,
        ),
        FieldSchema(
            field_id="field_004",
            run_id="run-1",
            name="country",
            label="Country",
            type="select",
        ),
    ]

    context = InferenceContext(run_id="run-1", target_url="https://example.com")
    constraints = classify_fields(fields=fields, context=context)
    semantic_by_field = {item.field_id: item.semantic_type for item in constraints}

    assert semantic_by_field["field_001"] == "postal_code"
    assert semantic_by_field["field_002"] == "amount"
    assert semantic_by_field["field_003"] == "boolean_choice"
    assert semantic_by_field["field_004"] == "select_option"


def test_classify_fields_synthesizes_structured_formats() -> None:
    fields = [
        FieldSchema(
            field_id="field_001",
            run_id="run-1",
            name="tax_identifier",
            label="PAN Number",
            type="text",
            pattern="^[A-Z]{5}[0-9]{4}[A-Z]{1}$",
        ),
        FieldSchema(
            field_id="field_002",
            run_id="run-1",
            name="ssn",
            label="Social Security Number",
            type="text",
            pattern="^[0-9]{3}-[0-9]{2}-[0-9]{4}$",
        ),
    ]

    context = InferenceContext(run_id="run-1", target_url="https://example.com")
    constraints = classify_fields(fields=fields, context=context)
    format_by_field = {item.field_id: item.likely_format for item in constraints}

    assert format_by_field["field_001"] == "pan-india-alpha5-digit4-alpha1"
    assert format_by_field["field_002"] == "ssn-us-3-2-4"


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
