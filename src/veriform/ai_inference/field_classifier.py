"""Deterministic-first field classification helpers.

AI providers can be layered on top of these helpers in later phases,
but deterministic heuristics remain the baseline source of truth.
"""

from __future__ import annotations

from typing import Sequence

from veriform.ai_inference.provider_interface import InferenceContext, SemanticInferenceProvider
from veriform.ai_inference.semantic_parser import parse_semantic_hints
from veriform.models.schemas import ConfidenceScoreSchema, FieldSchema, InferredConstraintSchema


def classify_fields(
    fields: Sequence[FieldSchema],
    context: InferenceContext,
    provider: SemanticInferenceProvider | None = None,
) -> list[InferredConstraintSchema]:
    """Classify fields into semantic hypotheses using deterministic hints first.

    TODO:
    - Resolve provider/deterministic conflicts using richer feedback loops.
    """
    constraints: list[InferredConstraintSchema] = []
    for index, field in enumerate(fields, start=1):
        semantic_type = _infer_semantic_type(field)
        confidence = _base_confidence_for(semantic_type)
        constraints.append(
            InferredConstraintSchema(
                constraint_id=f"{field.field_id}_ic_{index:03d}",
                run_id=context.run_id,
                field_id=field.field_id,
                semantic_type=semantic_type,
                likely_format=_default_format_for(semantic_type),
                confidence=ConfidenceScoreSchema(
                    score=confidence,
                    source="deterministic_hint",
                    rationale="Derived from deterministic field label/name tokens",
                ),
            )
        )

    if provider is None:
        return constraints

    provider_constraints = list(provider.infer_constraints(fields=fields, context=context))
    return _merge_provider_constraints(constraints, provider_constraints)


def _infer_semantic_type(field: FieldSchema) -> str:
    hints = parse_semantic_hints(field.name, field.label, field.dom_id)
    tokens = set(hints.tokens)
    if {"mobile", "phone", "contact"} & tokens:
        return "mobile_number"
    if {"loan", "lan", "account"} <= tokens or {"loan", "account"} <= tokens:
        return "loan_account_number"
    if {"dob"} & tokens or {"date", "birth"} <= tokens:
        return "date_of_birth"
    if {"application", "reference"} & tokens:
        return "application_reference_number"
    if "email" in tokens:
        return "email"
    if "name" in tokens:
        return "name"
    return "generic_text"


def _default_format_for(semantic_type: str) -> str:
    format_map = {
        "mobile_number": "10-digit-number",
        "loan_account_number": "8-16-digit-number",
        "date_of_birth": "YYYY-MM-DD",
        "application_reference_number": "alphanumeric-6-20",
        "email": "local@domain.tld",
        "phone": "10-digit-number",
        "name": "alphabetic-with-spaces",
        "generic_text": "free-text",
    }
    return format_map.get(semantic_type, "free-text")


def _base_confidence_for(semantic_type: str) -> float:
    confidence_map = {
        "mobile_number": 0.85,
        "loan_account_number": 0.82,
        "date_of_birth": 0.8,
        "application_reference_number": 0.78,
        "email": 0.74,
        "name": 0.62,
        "generic_text": 0.45,
    }
    return confidence_map.get(semantic_type, 0.45)


def _merge_provider_constraints(
    deterministic_constraints: Sequence[InferredConstraintSchema],
    provider_constraints: Sequence[InferredConstraintSchema],
) -> list[InferredConstraintSchema]:
    merged_by_field = {item.field_id: item for item in deterministic_constraints}
    for provider_item in provider_constraints:
        current = merged_by_field.get(provider_item.field_id)
        if current is None or provider_item.confidence.score > current.confidence.score:
            merged_by_field[provider_item.field_id] = provider_item
    return list(merged_by_field.values())
