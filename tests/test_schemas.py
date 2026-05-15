"""
tests/test_schemas.py
=====================
Unit tests for Pydantic schema validation.

These tests verify:
    - Valid models are accepted.
    - Invalid enum values raise ValidationError.
    - Required fields are enforced.
    - run_id propagation fields exist on child schemas.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from veriform.models.schemas import (
    FieldSchema,
    ResultSchema,
    RunMetrics,
    RunSummarySchema,
    TestCaseSchema,
)


RUN_ID = "run-test-abc123"


class TestFieldSchema:
    def test_valid_text_field(self):
        field = FieldSchema(
            field_id="field_001",
            run_id=RUN_ID,
            name="username",
            type="text",
            required=True,
            max_length=50,
        )
        assert field.field_id == "field_001"
        assert field.run_id == RUN_ID
        assert field.max_length == 50
        assert field.label is None

    def test_optional_fields_default_to_none(self):
        field = FieldSchema(field_id="f1", run_id=RUN_ID, name="q", type="text")
        assert field.label is None
        assert field.dom_id is None
        assert field.pattern is None

    def test_max_length_must_be_positive(self):
        with pytest.raises(ValidationError):
            FieldSchema(
                field_id="f1",
                run_id=RUN_ID,
                name="q",
                type="text",
                max_length=0,  # ge=1 constraint
            )


class TestTestCaseSchema:
    def test_valid_accept_case(self):
        tc = TestCaseSchema(
            test_case_id="tc_001",
            field_id="field_001",
            run_id=RUN_ID,
            input_value="hello",
            category="valid",
            expected_outcome="accept",
        )
        assert tc.expected_outcome == "accept"

    def test_valid_reject_case(self):
        tc = TestCaseSchema(
            test_case_id="tc_002",
            field_id="field_001",
            run_id=RUN_ID,
            input_value="",
            category="empty",
            expected_outcome="reject",
        )
        assert tc.expected_outcome == "reject"

    def test_invalid_expected_outcome_raises(self):
        with pytest.raises(ValidationError):
            TestCaseSchema(
                test_case_id="tc_003",
                field_id="field_001",
                run_id=RUN_ID,
                input_value="x",
                category="valid",
                expected_outcome="maybe",  # invalid
            )


class TestResultSchema:
    def test_valid_pass_result(self):
        result = ResultSchema(
            test_case_id="tc_001",
            run_id=RUN_ID,
            observed_outcome="accept",
            status="pass",
            execution_duration_ms=120,
        )
        assert result.status == "pass"
        assert result.screenshot_path is None

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            ResultSchema(
                test_case_id="tc_001",
                run_id=RUN_ID,
                observed_outcome="accept",
                status="unknown",  # invalid
                execution_duration_ms=100,
            )

    def test_invalid_observed_outcome_raises(self):
        with pytest.raises(ValidationError):
            ResultSchema(
                test_case_id="tc_001",
                run_id=RUN_ID,
                observed_outcome="maybe",  # invalid
                status="pass",
                execution_duration_ms=100,
            )


class TestRunSummarySchema:
    def test_valid_empty_run_summary(self):
        summary = RunSummarySchema(
            run_id=RUN_ID,
            timestamp=datetime.now(tz=timezone.utc),
            target_url="https://example.com/form",
            metrics=RunMetrics(
                total_fields_detected=0,
                total_tests_executed=0,
                total_passed=0,
                total_failed=0,
                pass_rate_percentage=0.0,
            ),
        )
        assert summary.run_id == RUN_ID
        assert summary.metrics.pass_rate_percentage == 0.0

    def test_pass_rate_out_of_bounds_raises(self):
        with pytest.raises(ValidationError):
            RunSummarySchema(
                run_id=RUN_ID,
                timestamp=datetime.now(tz=timezone.utc),
                target_url="https://example.com/form",
                metrics=RunMetrics(
                    total_fields_detected=1,
                    total_tests_executed=1,
                    total_passed=1,
                    total_failed=0,
                    pass_rate_percentage=101.0,  # le=100.0 violated
                ),
            )
