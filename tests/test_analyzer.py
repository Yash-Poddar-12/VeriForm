from __future__ import annotations

from veriform.analyzer.analyzer import analyze
from veriform.models.schemas import ResultSchema, TestCaseSchema


def test_analyze_sets_pass_fail_with_normalized_outcomes() -> None:
    test_cases = [
        TestCaseSchema(
            test_case_id="tc_accepted",
            field_id="field_001",
            run_id="run-1",
            input_value="ok",
            category="valid",
            expected_outcome="accept",
        ),
        TestCaseSchema(
            test_case_id="tc_validation",
            field_id="field_001",
            run_id="run-1",
            input_value="bad",
            category="invalid",
            expected_outcome="reject",
        ),
        TestCaseSchema(
            test_case_id="tc_timeout",
            field_id="field_001",
            run_id="run-1",
            input_value="bad",
            category="invalid",
            expected_outcome="reject",
        ),
    ]

    raw_results = [
        ResultSchema(
            test_case_id="tc_accepted",
            run_id="run-1",
            observed_outcome="accepted",
            status="fail",
            execution_duration_ms=10,
        ),
        ResultSchema(
            test_case_id="tc_validation",
            run_id="run-1",
            observed_outcome="validation_error",
            status="fail",
            execution_duration_ms=10,
        ),
        ResultSchema(
            test_case_id="tc_timeout",
            run_id="run-1",
            observed_outcome="timeout",
            status="pass",
            execution_duration_ms=10,
        ),
    ]

    analyzed = analyze(raw_results=raw_results, test_cases=test_cases)

    assert analyzed[0].status == "pass"
    assert analyzed[1].status == "pass"
    assert analyzed[2].status == "fail"
