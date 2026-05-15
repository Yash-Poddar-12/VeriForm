"""Confidence-based ranking utilities for inferred constraints and candidates."""

from __future__ import annotations

from typing import Sequence

from veriform.models.schemas import CandidateInputSchema, InferredConstraintSchema


def rank_constraints_by_confidence(
    constraints: Sequence[InferredConstraintSchema],
) -> list[InferredConstraintSchema]:
    """Return constraints sorted by descending confidence score."""
    return sorted(
        constraints,
        key=lambda item: (-item.confidence.score, item.constraint_id),
    )


def rank_candidates_by_priority(
    candidates: Sequence[CandidateInputSchema],
) -> list[CandidateInputSchema]:
    """Return candidates sorted by descending deterministic priority."""
    return sorted(candidates, key=lambda item: (-item.priority_score, item.candidate_id))
