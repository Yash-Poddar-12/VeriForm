"""Tests for veriform.reporter.reporter – report generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from veriform.models.schemas import (
    ConfidenceScoreSchema,
    InferredConstraintSchema,
    ResultSchema,
    RunMetrics,
    RunSummarySchema,
)
from veriform.reporter.reporter import generate


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _summary(run_id: str = "run-1", passed: int = 1, failed: int = 0) -> RunSummarySchema:
    total = passed + failed
    rate = (passed / total * 100.0) if total else 0.0
    return RunSummarySchema(
        run_id=run_id,
        timestamp=datetime.now(tz=timezone.utc),
        target_url="https://example.com/form",
        metrics=RunMetrics(
            total_fields_detected=2,
            total_tests_executed=total,
            total_passed=passed,
            total_failed=failed,
            pass_rate_percentage=round(rate, 2),
        ),
    )


def _result(
    tc_id: str = "tc1",
    run_id: str = "run-1",
    observed: str = "accepted",
    status: str = "pass",
    duration_ms: int = 10,
) -> ResultSchema:
    return ResultSchema(
        test_case_id=tc_id,
        run_id=run_id,
        observed_outcome=observed,
        status=status,
        execution_duration_ms=duration_ms,
    )


def _constraint(
    field_id: str = "field_001",
    semantic: str = "mobile_number",
    fmt: str = "phone-local-or-international",
    score: float = 0.85,
) -> InferredConstraintSchema:
    return InferredConstraintSchema(
        constraint_id=f"{field_id}_ic_001",
        run_id="run-1",
        field_id=field_id,
        semantic_type=semantic,
        likely_format=fmt,
        confidence=ConfidenceScoreSchema(score=score, source="deterministic_hint"),
    )


# ---------------------------------------------------------------------------
# File creation
# ---------------------------------------------------------------------------


class TestReporterFileCreation:
    def test_creates_json_file(self, workspace_tmp_path: Path) -> None:
        output_dir = workspace_tmp_path / "out"
        generate(summary=_summary(), results=[_result()], output_dir=output_dir)
        assert (output_dir / "report.json").exists()

    def test_creates_html_file(self, workspace_tmp_path: Path) -> None:
        output_dir = workspace_tmp_path / "out"
        generate(summary=_summary(), results=[_result()], output_dir=output_dir)
        assert (output_dir / "report.html").exists()

    def test_creates_output_dir_if_absent(self, workspace_tmp_path: Path) -> None:
        output_dir = workspace_tmp_path / "nested" / "run-xyz"
        assert not output_dir.exists()
        generate(summary=_summary(), results=[], output_dir=output_dir)
        assert output_dir.exists()


# ---------------------------------------------------------------------------
# JSON payload structure
# ---------------------------------------------------------------------------


class TestJsonPayload:
    def _load(self, tmp: Path, **kwargs) -> dict:
        out = tmp / "out"
        generate(output_dir=out, **kwargs)
        return json.loads((out / "report.json").read_text("utf-8"))

    def test_summary_run_id(self, workspace_tmp_path: Path) -> None:
        payload = self._load(workspace_tmp_path, summary=_summary("run-42"), results=[])
        assert payload["summary"]["run_id"] == "run-42"

    def test_results_list_present(self, workspace_tmp_path: Path) -> None:
        payload = self._load(
            workspace_tmp_path,
            summary=_summary(),
            results=[_result("tc1"), _result("tc2")],
        )
        assert len(payload["results"]) == 2

    def test_stats_block(self, workspace_tmp_path: Path) -> None:
        payload = self._load(
            workspace_tmp_path,
            summary=_summary(passed=3, failed=1),
            results=[
                _result("a", status="pass"),
                _result("b", status="pass"),
                _result("c", status="pass"),
                _result("d", observed="rejected", status="fail"),
            ],
        )
        assert payload["stats"]["total"] == 4
        assert payload["stats"]["passed"] == 3
        assert payload["stats"]["failed"] == 1
        assert payload["stats"]["pass_rate_pct"] == pytest.approx(75.0)

    def test_grouped_results_pass(self, workspace_tmp_path: Path) -> None:
        payload = self._load(
            workspace_tmp_path,
            summary=_summary(),
            results=[_result("tc1", status="pass")],
        )
        assert "pass" in payload["grouped_results"]
        assert payload["grouped_results"]["pass"][0]["test_case_id"] == "tc1"

    def test_grouped_results_fail(self, workspace_tmp_path: Path) -> None:
        payload = self._load(
            workspace_tmp_path,
            summary=_summary(passed=0, failed=1),
            results=[_result("tc-fail", observed="rejected", status="fail")],
        )
        assert "fail" in payload["grouped_results"]
        assert payload["grouped_results"]["fail"][0]["test_case_id"] == "tc-fail"

    def test_by_outcome_block(self, workspace_tmp_path: Path) -> None:
        payload = self._load(
            workspace_tmp_path,
            summary=_summary(),
            results=[
                _result("t1", observed="accepted", status="pass"),
                _result("t2", observed="validation_error", status="fail"),
            ],
        )
        assert "accepted" in payload["by_outcome"]
        assert "validation_error" in payload["by_outcome"]

    def test_constraint_summary_included(self, workspace_tmp_path: Path) -> None:
        payload = self._load(
            workspace_tmp_path,
            summary=_summary(),
            results=[],
            inferred_constraints=[_constraint("field_001", "mobile_number")],
        )
        assert "field_001" in payload["constraint_summary"]
        cs = payload["constraint_summary"]["field_001"]
        assert cs["semantic_type"] == "mobile_number"
        assert cs["confidence_score"] == pytest.approx(0.85)

    def test_empty_constraint_summary_when_none(self, workspace_tmp_path: Path) -> None:
        payload = self._load(
            workspace_tmp_path,
            summary=_summary(),
            results=[],
        )
        assert payload["constraint_summary"] == {}

    def test_feedback_by_field_included(self, workspace_tmp_path: Path) -> None:
        payload = self._load(
            workspace_tmp_path,
            summary=_summary(),
            results=[],
            feedback_by_field={"field_001": ["accepted", "rejected"]},
        )
        assert payload["feedback_by_field"]["field_001"] == ["accepted", "rejected"]

    def test_zero_results_safe(self, workspace_tmp_path: Path) -> None:
        payload = self._load(
            workspace_tmp_path,
            summary=_summary(passed=0, failed=0),
            results=[],
        )
        assert payload["stats"]["total"] == 0
        assert payload["stats"]["pass_rate_pct"] == 0.0


# ---------------------------------------------------------------------------
# HTML content
# ---------------------------------------------------------------------------


class TestHtmlOutput:
    def _html(self, tmp: Path, **kwargs) -> str:
        out = tmp / "out"
        generate(output_dir=out, **kwargs)
        return (out / "report.html").read_text("utf-8")

    def test_html_contains_run_id(self, workspace_tmp_path: Path) -> None:
        html = self._html(
            workspace_tmp_path,
            summary=_summary("run-sentinel"),
            results=[],
        )
        assert "run-sentinel" in html

    def test_html_contains_target_url(self, workspace_tmp_path: Path) -> None:
        html = self._html(workspace_tmp_path, summary=_summary(), results=[])
        assert "example.com" in html

    def test_html_contains_pass_verdict_class(self, workspace_tmp_path: Path) -> None:
        html = self._html(
            workspace_tmp_path,
            summary=_summary(),
            results=[_result("t1", status="pass")],
        )
        assert "verdict-pass" in html

    def test_html_contains_fail_verdict_class(self, workspace_tmp_path: Path) -> None:
        html = self._html(
            workspace_tmp_path,
            summary=_summary(passed=0, failed=1),
            results=[_result("t1", observed="rejected", status="fail")],
        )
        assert "verdict-fail" in html

    def test_html_contains_constraint_semantic_type(self, workspace_tmp_path: Path) -> None:
        html = self._html(
            workspace_tmp_path,
            summary=_summary(),
            results=[],
            inferred_constraints=[_constraint("field_001", "mobile_number")],
        )
        assert "mobile_number" in html

    def test_html_is_valid_utf8(self, workspace_tmp_path: Path) -> None:
        html = self._html(workspace_tmp_path, summary=_summary(), results=[])
        # If read succeeds with no exception the file is valid UTF-8
        assert len(html) > 100
