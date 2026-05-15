from __future__ import annotations

from veriform.executor.executor import execute
from veriform.models.schemas import TestCaseSchema

from fake_playwright import FakePage


async def test_execute_returns_raw_outcomes_for_each_test_case() -> None:
    page = FakePage(controls=[])
    test_cases = [
        TestCaseSchema(
            test_case_id="tc1",
            field_id="field_001",
            run_id="run-1",
            field_name="mobile_number",
            input_value="9876543210",
            category="mobile-valid",
            expected_outcome="accept",
        ),
        TestCaseSchema(
            test_case_id="tc2",
            field_id="field_001",
            run_id="run-1",
            field_name="mobile_number",
            input_value="1234",
            category="mobile-too-short",
            expected_outcome="reject",
        ),
    ]

    results = await execute(page=page, test_cases=test_cases, target_url="https://example.com/form")

    assert len(results) == 2
    assert results[0].observed_outcome == "accepted"
    assert results[1].observed_outcome == "validation_error"
    assert all(result.execution_duration_ms >= 0 for result in results)
