"""veriform.generator.generator
=============================
Deterministic test generation facade.

This module keeps backward-compatible ``generate(fields)`` behavior while
routing through candidate generation and combination planning placeholders.
"""

from __future__ import annotations

from typing import Mapping, Sequence

from veriform.constraint_ir.models.profile import ConstraintProfile
from veriform.generator.candidate_generator import build_candidate_inputs
from veriform.generator.combination_planner import create_combination_plan
from veriform.models.schemas import FieldSchema, InferredConstraintSchema, TestCaseSchema
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


async def generate(
    fields: list[FieldSchema],
    constraint_profiles: Sequence[ConstraintProfile] | None = None,
    max_combinations: int = 25,
) -> list[TestCaseSchema]:
    """Generate deterministic test cases for each detected field.

    TODO:
    - Expand category coverage to full Phase 1 matrix.
    """
    if not fields:
        logger.warning("generate: no fields provided - returning empty list")
        return []

    profiles = constraint_profiles or []
    candidates = await build_candidate_inputs(fields=fields, constraint_profiles=profiles)
    plan = create_combination_plan(
        run_id=fields[0].run_id,
        candidates=candidates,
        max_combinations=max_combinations,
    )
    field_lookup = {field.field_id: field for field in fields}

    test_cases: list[TestCaseSchema] = []
    for index, candidate in enumerate(plan.selected_candidates, start=1):
        field = field_lookup.get(candidate.field_id)
        test_cases.append(
            TestCaseSchema(
                test_case_id=f"{candidate.field_id}_tc_{index:03d}",
                field_id=candidate.field_id,
                run_id=candidate.run_id,
                field_name=field.name if field else None,
                dom_id=field.dom_id if field else None,
                input_value=candidate.input_value,
                category=candidate.category,
                expected_outcome=candidate.expected_outcome,
            )
        )
    return test_cases


def _cases_for_field(field: FieldSchema) -> list[TestCaseSchema]:
    """Reserved helper for future per-field matrix expansion."""
    # TODO: restore rich category generation once field strategies land.
    return []
