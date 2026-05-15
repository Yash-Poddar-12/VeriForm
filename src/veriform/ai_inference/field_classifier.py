"""Deterministic-first field classification helpers.

AI providers can be layered on top of these helpers in later phases,
but deterministic heuristics remain the baseline source of truth.
"""

from __future__ import annotations

from typing import Sequence

from veriform.ai_inference.provider_interface import InferenceContext, SemanticInferenceProvider
from veriform.ai_inference.semantic_parser import parse_semantic_hints
from veriform.constraints.structured_synthesis import synthesize_likely_format
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
        confidence = _confidence_for(field, semantic_type)
        constraints.append(
            InferredConstraintSchema(
                constraint_id=f"{field.field_id}_ic_{index:03d}",
                run_id=context.run_id,
                field_id=field.field_id,
                semantic_type=semantic_type,
                likely_format=synthesize_likely_format(field, semantic_type),
                confidence=ConfidenceScoreSchema(
                    score=confidence,
                    source="deterministic_hint",
                    rationale="Derived from deterministic metadata tokens and constraints",
                ),
            )
        )

    if provider is None:
        return constraints

    provider_constraints = list(provider.infer_constraints(fields=fields, context=context))
    return _merge_provider_constraints(constraints, provider_constraints)


def _infer_semantic_type(field: FieldSchema) -> str:
    hints = parse_semantic_hints(
        field.name,
        field.label,
        field.dom_id,
        field.placeholder,
        field.context_text,
        field.pattern,
    )
    tokens = set(hints.tokens)
    field_type = field.type.lower()

    if field_type in {"checkbox", "radio"} or _contains_any(
        tokens, {"agree", "accept", "consent", "yes", "no", "terms"}
    ):
        return "boolean_choice"
    if field_type in {"select", "dropdown"}:
        return "select_option"
    if field_type == "email" or "email" in tokens:
        return "email"
    if field_type == "tel" or _contains_any(tokens, {"mobile", "phone", "contact", "telephone"}):
        return "mobile_number"
    if _contains_any(tokens, {"dob"}) or {"date", "birth"} <= tokens:
        return "date_of_birth"
    if field_type == "date" or _contains_any(tokens, {"date", "day", "month", "year"}):
        return "date"
    if _contains_any(tokens, {"address", "street", "line1", "line2"}):
        return "address"
    if "city" in tokens:
        return "city"
    if "state" in tokens or "province" in tokens:
        return "state"
    if _contains_any(tokens, {"zip", "postal", "postcode", "pincode"}):
        return "postal_code"
    if {"loan", "account"} <= tokens:
        return "loan_account_number"
    if _contains_any(tokens, {"account", "iban", "routing"}) and _contains_any(
        tokens, {"number", "no", "num", "id"}
    ):
        return "account_number"
    if _contains_any(tokens, {"reference", "identifier", "application", "ticket"}) and _contains_any(
        tokens, {"number", "no", "num", "id", "code", "ref"}
    ):
        return "application_reference_number"
    if _contains_any(tokens, {"amount", "price", "fee", "salary", "income", "currency"}):
        return "amount"
    if "name" in tokens:
        return "name"
    if field_type == "textarea" or _contains_any(tokens, {"message", "comments", "description"}):
        return "free_text"
    return "generic_text"


def _base_confidence_for(semantic_type: str) -> float:
    confidence_map = {
        "mobile_number": 0.85,
        "loan_account_number": 0.82,
        "account_number": 0.78,
        "date_of_birth": 0.8,
        "date": 0.74,
        "address": 0.72,
        "city": 0.72,
        "state": 0.7,
        "postal_code": 0.76,
        "amount": 0.78,
        "select_option": 0.72,
        "boolean_choice": 0.7,
        "free_text": 0.58,
        "application_reference_number": 0.78,
        "email": 0.74,
        "name": 0.62,
        "generic_text": 0.45,
    }
    return confidence_map.get(semantic_type, 0.45)


def _contains_any(tokens: set[str], values: set[str]) -> bool:
    return bool(tokens & values)


def _confidence_for(field: FieldSchema, semantic_type: str) -> float:
    score = _base_confidence_for(semantic_type)
    if field.pattern:
        score += 0.05
    if field.required:
        score += 0.03
    if field.min_length is not None or field.max_length is not None:
        score += 0.03
    if field.min_val is not None or field.max_val is not None:
        score += 0.03
    if field.type.lower() in {"email", "tel", "date", "number", "select", "checkbox", "radio"}:
        score += 0.04
    return round(min(max(score, 0.0), 1.0), 4)


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
