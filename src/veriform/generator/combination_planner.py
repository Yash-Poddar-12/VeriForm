"""Deterministic combination planner for candidate execution."""

from __future__ import annotations

from typing import Sequence

from veriform.ai_inference.confidence_ranker import rank_candidates_by_priority
from veriform.models.schemas import CandidateInputSchema, CombinationPlanSchema


def create_combination_plan(
    run_id: str,
    candidates: Sequence[CandidateInputSchema],
    max_combinations: int = 25,
) -> CombinationPlanSchema:
    """Create a deterministic, bounded execution plan from unique candidates."""
    deduped = _dedupe_candidates(candidates)
    ranked = rank_candidates_by_priority(deduped)
    selected = _select_with_field_coverage(ranked, max_combinations=max_combinations)
    return CombinationPlanSchema(
        plan_id=f"plan_{run_id}",
        run_id=run_id,
        strategy="single-page-deterministic-priority",
        max_combinations=max_combinations,
        selected_candidates=selected,
    )


def _dedupe_candidates(
    candidates: Sequence[CandidateInputSchema],
) -> list[CandidateInputSchema]:
    unique: dict[tuple[str, str, str], CandidateInputSchema] = {}
    for candidate in candidates:
        key = (candidate.field_id, str(candidate.input_value), candidate.category)
        current = unique.get(key)
        if current is None or candidate.priority_score > current.priority_score:
            unique[key] = candidate
    return list(unique.values())


def _select_with_field_coverage(
    ranked: Sequence[CandidateInputSchema],
    max_combinations: int,
) -> list[CandidateInputSchema]:
    """Seed one high-priority candidate per field, then fill by global priority."""
    if max_combinations <= 0:
        return []

    selected: list[CandidateInputSchema] = []
    selected_ids: set[str] = set()
    seen_fields: set[str] = set()

    for candidate in ranked:
        if len(selected) >= max_combinations:
            return selected
        if candidate.field_id in seen_fields:
            continue
        selected.append(candidate)
        selected_ids.add(candidate.candidate_id)
        seen_fields.add(candidate.field_id)

    for candidate in ranked:
        if len(selected) >= max_combinations:
            break
        if candidate.candidate_id in selected_ids:
            continue
        selected.append(candidate)
        selected_ids.add(candidate.candidate_id)

    return selected
