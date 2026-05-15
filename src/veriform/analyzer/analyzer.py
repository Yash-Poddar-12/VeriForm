"""
veriform.analyzer.analyzer
===========================
Result classification module.

Phase 1 behavior:
- Normalizes raw execution outcomes.
- Compares observed vs expected to compute pass/fail.
"""

from __future__ import annotations

from veriform.models.schemas import ResultSchema, TestCaseSchema
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


def analyze(
    raw_results: list[ResultSchema],
    test_cases: list[TestCaseSchema],
) -> list[ResultSchema]:
    """Enrich *raw_results* with pass/fail status."""
    expected_by_test_case = {
        test_case.test_case_id: test_case.expected_outcome for test_case in test_cases
    }

    enriched: list[ResultSchema] = []
    for raw in raw_results:
        expected = expected_by_test_case.get(raw.test_case_id, "reject")
        normalized = _normalize_outcome(raw.observed_outcome)
        status = "pass" if normalized == expected else "fail"

        if raw.observed_outcome in {"timeout", "crash", "error"}:
            status = "fail"

        enriched.append(raw.model_copy(update={"status": status}))

    logger.info("analyze: processed %d results", len(enriched))
    return enriched


def _normalize_outcome(observed_outcome: str) -> str:
    if observed_outcome in {"accepted", "accept"}:
        return "accept"
    if observed_outcome in {"rejected", "reject", "validation_error"}:
        return "reject"
    return "error"
