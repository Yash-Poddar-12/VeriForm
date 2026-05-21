"""
veriform.reporter.reporter
===========================
Report generation module.

Writes:
- ``report.json``  – full machine-readable payload (summary, results,
                     inferred constraints, execution feedback)
- ``report.html``  – rich Jinja2-rendered HTML for QA review

Phase 1 improvements
---------------------
* JSON payload now includes ``grouped_results`` (by pass/fail) and
  ``constraint_summary`` (inferred semantic types + confidence scores).
* HTML template receives all payload sections for a rich report.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Mapping, Optional, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape

from veriform.models.schemas import (
    InferredConstraintSchema,
    ResultSchema,
    RunSummarySchema,
)
from veriform.utils.logging import get_logger

logger = get_logger(__name__)

# Resolve template directory relative to this file:
# reporter.py  →  reporter/  →  veriform/  →  src/  →  project root  →  templates/
_TEMPLATES_DIR = Path(__file__).resolve().parents[3] / "templates"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


from veriform.models.workflow import WorkflowSession

def generate(
    summary: RunSummarySchema,
    results: list[ResultSchema],
    output_dir: Path,
    inferred_constraints: Optional[Sequence[InferredConstraintSchema]] = None,
    feedback_by_field: Optional[Mapping[str, Sequence[str]]] = None,
    workflow_session: Optional[WorkflowSession] = None,
) -> None:
    """Write ``report.json`` and ``report.html`` to *output_dir*."""
    output_dir.mkdir(parents=True, exist_ok=True)

    _inferred = list(inferred_constraints or [])
    _feedback = {k: list(v) for k, v in (feedback_by_field or {}).items()}

    payload = _build_payload(summary, results, _inferred, _feedback)
    if workflow_session:
        payload["workflow"] = workflow_session.model_dump(mode="json")
        
        # Write append-only replay trace in JSONL
        trace_path = output_dir / "trace.jsonl"
        with trace_path.open("w", encoding="utf-8") as f:
            for action in workflow_session.action_timeline:
                f.write(json.dumps({"type": "action", "data": action.model_dump(mode="json")}) + "\n")
            for h, snap in workflow_session.snapshots.items():
                f.write(json.dumps({"type": "snapshot", "data": snap.model_dump(mode="json")}) + "\n")
                
        # Write workflow graph JSON
        _write_json(output_dir / "workflow.json", payload["workflow"])

    _write_json(output_dir / "report.json", payload)
    _write_html(output_dir / "report.html", payload)

    logger.info(
        "Reports written -> %s  (pass=%d fail=%d)",
        output_dir,
        payload["stats"]["passed"],
        payload["stats"]["failed"],
    )


# ---------------------------------------------------------------------------
# Payload construction
# ---------------------------------------------------------------------------


def _build_payload(
    summary: RunSummarySchema,
    results: list[ResultSchema],
    inferred_constraints: list[InferredConstraintSchema],
    feedback_by_field: dict[str, list[str]],
) -> dict:
    """Assemble the full JSON-serialisable payload dict."""
    results_dicts = [r.model_dump(mode="json") for r in results]

    # Aggregate stats
    passed = sum(1 for r in results if r.status == "pass")
    failed = sum(1 for r in results if r.status == "fail")
    total = len(results)
    pass_rate = round((passed / total * 100.0) if total else 0.0, 1)

    # Group results by status
    grouped: dict[str, list[dict]] = defaultdict(list)
    for r in results_dicts:
        grouped[r["status"]].append(r)

    # Group results by observed outcome
    by_outcome: dict[str, list[dict]] = defaultdict(list)
    for r in results_dicts:
        by_outcome[r["observed_outcome"]].append(r)

    # Constraint summary keyed by field_id
    constraint_summary: dict[str, dict] = {}
    for c in inferred_constraints:
        constraint_summary[c.field_id] = {
            "constraint_id": c.constraint_id,
            "semantic_type": c.semantic_type,
            "likely_format": c.likely_format,
            "confidence_score": c.confidence.score,
            "confidence_source": c.confidence.source,
            "confidence_rationale": c.confidence.rationale,
        }

    return {
        "summary": summary.model_dump(mode="json"),
        "stats": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate_pct": pass_rate,
        },
        "results": results_dicts,
        "grouped_results": {k: list(v) for k, v in grouped.items()},
        "by_outcome": {k: list(v) for k, v in by_outcome.items()},
        "constraint_summary": constraint_summary,
        "feedback_by_field": feedback_by_field,
        "inferred_constraints": [c.model_dump(mode="json") for c in inferred_constraints],
    }


# ---------------------------------------------------------------------------
# Writers
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    logger.debug("JSON report → %s", path)


def _write_html(path: Path, payload: dict) -> None:
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "j2"]),
    )
    template = env.get_template("report.html.j2")
    html = template.render(**payload)
    path.write_text(html, encoding="utf-8")
    logger.debug("HTML report → %s", path)
