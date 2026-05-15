"""
veriform.reporter.reporter
===========================
Report generation module.

Writes machine-readable JSON plus HTML output using the shared Jinja2 template.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping, Sequence

from jinja2 import Environment, FileSystemLoader, select_autoescape

from veriform.models.schemas import InferredConstraintSchema, ResultSchema, RunSummarySchema
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


def generate(
    summary: RunSummarySchema,
    results: list[ResultSchema],
    output_dir: Path,
    inferred_constraints: Sequence[InferredConstraintSchema] | None = None,
    feedback_by_field: Mapping[str, Sequence[str]] | None = None,
) -> None:
    """Write JSON and HTML reports to *output_dir*."""
    output_dir.mkdir(parents=True, exist_ok=True)

    payload = {
        "summary": summary.model_dump(mode="json"),
        "results": [result.model_dump(mode="json") for result in results],
        "inferred_constraints": [
            item.model_dump(mode="json") for item in (inferred_constraints or [])
        ],
        "feedback_by_field": {
            field_id: list(outcomes)
            for field_id, outcomes in (feedback_by_field or {}).items()
        },
    }

    report_json_path = output_dir / "report.json"
    report_json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    templates_dir = Path(__file__).resolve().parents[3] / "templates"
    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    template = env.get_template("report.html.j2")
    report_html = template.render(summary=summary, results=results)
    (output_dir / "report.html").write_text(report_html, encoding="utf-8")

    logger.info("reporter.generate: wrote report to %s", output_dir)
