"""Deterministic-first merge utilities for inferred constraints.

The output from this module is used by generation/planning layers. AI hints
are assistive and can be overruled by deterministic execution feedback.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Mapping, Sequence

from veriform.ai_inference.confidence_ranker import rank_constraints_by_confidence
from veriform.models.schemas import ConfidenceScoreSchema, FieldSchema, InferredConstraintSchema


def merge_inferred_constraints(
    fields: Sequence[FieldSchema],
    inferred_constraints: Sequence[InferredConstraintSchema],
    feedback_by_field: Mapping[str, Sequence[str]] | None = None,
) -> dict[str, list[InferredConstraintSchema]]:
    """Merge deterministic field set with inferred constraint hypotheses.

    TODO:
    - Add explicit conflict resolution between HTML attributes and inferred formats.
    - Incorporate accepted/rejected loop signals for adaptive confidence updates.
    """
    feedback_map = feedback_by_field or {}
    field_ids = {field.field_id for field in fields}
    grouped: dict[str, list[InferredConstraintSchema]] = defaultdict(list)

    for constraint in inferred_constraints:
        if constraint.field_id not in field_ids:
            continue
        grouped[constraint.field_id].append(constraint)

    merged: dict[str, list[InferredConstraintSchema]] = {}
    for field in fields:
        ranked = rank_constraints_by_confidence(grouped.get(field.field_id, []))
        # Deterministic-first: feedback does not mutate data yet; reserved for Phase 2.
        if field.field_id in feedback_map:
            _ = feedback_map[field.field_id]
        merged[field.field_id] = ranked

    return merged


def apply_feedback_to_constraints(
    merged_constraints: Mapping[str, Sequence[InferredConstraintSchema]],
    feedback_by_field: Mapping[str, Sequence[str]],
) -> dict[str, list[InferredConstraintSchema]]:
    """Return constraints with lightweight confidence updates from outcomes.

    Phase 1 keeps this deterministic and bounded. Outcomes are interpreted as:
    - accepted -> confidence +0.05
    - rejected/validation_error/timeout/crash -> confidence -0.05
    """
    updated: dict[str, list[InferredConstraintSchema]] = {}
    for field_id, constraints in merged_constraints.items():
        outcomes = feedback_by_field.get(field_id, ())
        delta = _confidence_delta(outcomes)
        updated[field_id] = [
            constraint.model_copy(
                update={
                    "confidence": ConfidenceScoreSchema(
                        score=_clamp_score(constraint.confidence.score + delta),
                        source=constraint.confidence.source,
                        rationale=_updated_rationale(
                            constraint.confidence.rationale,
                            outcomes,
                        ),
                    )
                }
            )
            for constraint in constraints
        ]
    return updated


def _confidence_delta(outcomes: Sequence[str]) -> float:
    delta = 0.0
    for outcome in outcomes:
        if outcome == "accepted":
            delta += 0.05
        elif outcome in {"rejected", "validation_error", "timeout", "crash"}:
            delta -= 0.05
    return delta


def _clamp_score(score: float) -> float:
    if score < 0.0:
        return 0.0
    if score > 1.0:
        return 1.0
    return round(score, 4)


def _updated_rationale(existing: str | None, outcomes: Sequence[str]) -> str:
    history = ",".join(outcomes) if outcomes else "none"
    base = existing or "deterministic_hint"
    return f"{base}; feedback={history}"
