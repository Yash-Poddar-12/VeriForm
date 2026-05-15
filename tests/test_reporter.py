from __future__ import annotations

import json
from datetime import datetime, timezone

from veriform.models.schemas import ResultSchema, RunMetrics, RunSummarySchema
from veriform.reporter.reporter import generate


def test_reporter_writes_json_and_html(workspace_tmp_path) -> None:
    summary = RunSummarySchema(
        run_id="run-1",
        timestamp=datetime.now(tz=timezone.utc),
        target_url="https://example.com/form",
        metrics=RunMetrics(
            total_fields_detected=1,
            total_tests_executed=1,
            total_passed=1,
            total_failed=0,
            pass_rate_percentage=100.0,
        ),
    )
    results = [
        ResultSchema(
            test_case_id="tc1",
            run_id="run-1",
            observed_outcome="accepted",
            status="pass",
            execution_duration_ms=5,
        )
    ]

    output_dir = workspace_tmp_path / "report-output"
    generate(summary=summary, results=results, output_dir=output_dir)

    assert (output_dir / "report.json").exists()
    assert (output_dir / "report.html").exists()

    payload = json.loads((output_dir / "report.json").read_text(encoding="utf-8"))
    assert payload["summary"]["run_id"] == "run-1"
    assert payload["results"][0]["status"] == "pass"
