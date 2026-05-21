"""Tests for Reporter workflow integration."""

import json
from pathlib import Path
from datetime import datetime, timezone
from veriform.reporter.reporter import generate
from veriform.models.schemas import RunSummarySchema, RunMetrics, ResultSchema
from veriform.models.workflow import WorkflowSession, ActionSchema

def test_reporter_generates_workflow_artifacts(tmp_path: Path) -> None:
    summary = RunSummarySchema(
        run_id="r1",
        timestamp=datetime.now(tz=timezone.utc),
        target_url="http://test.com",
        metrics=RunMetrics(
            total_fields_detected=1,
            total_tests_executed=1,
            total_passed=1,
            total_failed=0,
            pass_rate_percentage=100.0,
        )
    )
    
    results = [
        ResultSchema(
            test_case_id="tc1",
            run_id="r1",
            observed_outcome="accepted",
            status="pass",
            execution_duration_ms=100
        )
    ]
    
    session = WorkflowSession(
        session_id="s1",
        run_id="r1",
        start_time=datetime.now(tz=timezone.utc),
        action_timeline=[
            ActionSchema(action_id="a1", type="navigate", value="http://test.com")
        ]
    )
    
    generate(
        summary=summary,
        results=results,
        output_dir=tmp_path,
        workflow_session=session
    )
    
    assert (tmp_path / "workflow.json").exists()
    assert (tmp_path / "trace.jsonl").exists()
    
    with open(tmp_path / "trace.jsonl", "r") as f:
        lines = f.readlines()
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["type"] == "action"
        assert data["data"]["action_id"] == "a1"
