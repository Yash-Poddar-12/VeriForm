"""Typed provider interfaces for future AI inference integrations.

This module intentionally contains interfaces only.
No external LLM calls should be implemented here in Phase 1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence

from veriform.models.schemas import (
    CandidateInputSchema,
    FieldSchema,
    InferredConstraintSchema,
)


@dataclass(frozen=True)
class InferenceContext:
    """Execution context for inference and ranking providers."""

    run_id: str
    target_url: str
    # TODO: include locale/session metadata when adaptive learning is introduced.
    feedback_by_field: Mapping[str, Sequence[str]] = field(default_factory=dict)


class SemanticInferenceProvider(Protocol):
    """Contract for providers that infer semantic constraints from detected fields."""

    provider_name: str

    def infer_constraints(
        self,
        fields: Sequence[FieldSchema],
        context: InferenceContext,
    ) -> Sequence[InferredConstraintSchema]:
        """Return inferred constraints for the given fields."""


class CandidateRankingProvider(Protocol):
    """Contract for providers that rank generated candidate inputs."""

    provider_name: str

    def rank_candidates(
        self,
        candidates: Sequence[CandidateInputSchema],
        context: InferenceContext,
    ) -> Sequence[CandidateInputSchema]:
        """Return candidates with updated priority_score values."""
