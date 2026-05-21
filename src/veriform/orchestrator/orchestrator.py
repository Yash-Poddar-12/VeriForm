"""veriform.orchestrator.orchestrator
===================================
Central controller for a single VeriForm test run.

Deterministic execution remains the source of truth.
AI artifacts are assistive and feed prioritization only.

Pipeline stages
---------------
1. detect          – DOM inspection → list[FieldSchema]
2. classify        – heuristic inference → list[InferredConstraintSchema]
2b. build_profiles – translate → list[ConstraintProfile]  (IR layer)
3. merge           – group/rank constraints by field
4. generate        – candidates + combination plan → list[TestCaseSchema]
5. execute         – browser automation → list[ResultSchema]
6. analyze         – compare expected vs observed → updated ResultSchema list
7. feedback        – propagate outcomes back to constraint confidence
8. report          – write JSON + HTML artifacts
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from veriform.ai_inference.field_classifier import classify_fields
from veriform.ai_inference.provider_interface import InferenceContext
from veriform.analyzer.analyzer import analyze
from veriform.config import settings
from veriform.constraint_ir.adapters.translator import translate_to_profile
from veriform.constraint_ir.models.profile import ConstraintProfile
from veriform.constraints.inferred_constraints import (
    apply_feedback_to_constraints,
    merge_inferred_constraints,
)
from veriform.detector.detector import detect_fields
from veriform.executor.executor import execute
from veriform.generator.generator import generate
from veriform.models.schemas import (
    CandidateInputSchema,
    FieldSchema,
    InferredConstraintSchema,
    ResultSchema,
    RunMetrics,
    RunSummarySchema,
    TestCaseSchema,
)
from veriform.reporter.reporter import generate as generate_report
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


class OrchestratorError(Exception):
    """Raised when the run lifecycle encounters an unrecoverable error."""


class InferenceInterface(Protocol):
    """Interface for field inference stage (deterministic + optional AI)."""

    def infer(
        self,
        fields: Sequence[FieldSchema],
        run_id: str,
        target_url: str,
        feedback_by_field: Mapping[str, Sequence[str]],
    ) -> Sequence[InferredConstraintSchema]:
        """Return inferred constraints for detected fields."""


class CandidatePlanningInterface(Protocol):
    """Interface for candidate generation/ranking/planning stage."""

    def build_ranked_candidates(
        self,
        fields: Sequence[FieldSchema],
        merged_constraints: Mapping[str, Sequence[InferredConstraintSchema]],
    ) -> Sequence[CandidateInputSchema]:
        """Return candidates ordered by deterministic-first priority."""


@dataclass
class OrchestrationArtifacts:
    """Shared state object for the orchestrator run lifecycle."""

    detected_fields: list[FieldSchema] = field(default_factory=list)
    inferred_constraints: list[InferredConstraintSchema] = field(default_factory=list)
    constraint_profiles: list[ConstraintProfile] = field(default_factory=list)
    merged_constraints: dict[str, list[InferredConstraintSchema]] = field(default_factory=dict)
    ranked_candidates: list[CandidateInputSchema] = field(default_factory=list)
    planned_test_cases: list[TestCaseSchema] = field(default_factory=list)
    raw_results: list[ResultSchema] = field(default_factory=list)
    enriched_results: list[ResultSchema] = field(default_factory=list)
    execution_feedback: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class _ManagedPageSession:
    playwright: Any
    browser: Any
    context: Any
    page: Any

    async def close(self) -> None:
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()


async def run(target_url: str) -> RunSummarySchema:
    """Execute a full test run against *target_url*."""
    return await run_single_page(target_url=target_url)


async def run_single_page(
    target_url: str,
    page: object | None = None,
    reports_root: Path | None = None,
) -> RunSummarySchema:
    """Run the Phase 1 single-page deterministic + AI-assisted flow."""
    run_id = str(uuid.uuid4())
    started_at = datetime.now(tz=timezone.utc)
    logger.info("Starting run %s for URL: %s", run_id, target_url)

    artifacts = OrchestrationArtifacts()
    managed_session: _ManagedPageSession | None = None

    try:
        if page is None:
            page, managed_session = await _try_create_managed_page()

        if page is None:
            logger.warning(
                "No Playwright page available; returning empty summary for run %s", run_id
            )
        else:
            await page.goto(target_url, timeout=settings.timeout_ms, wait_until="networkidle")
            await page.wait_for_timeout(3000)

            artifacts.detected_fields = await detect_fields(page=page, run_id=run_id)
            logger.debug("Step 1 - detected %d fields", len(artifacts.detected_fields))

            inference_context = InferenceContext(run_id=run_id, target_url=target_url)
            artifacts.inferred_constraints = classify_fields(
                fields=artifacts.detected_fields,
                context=inference_context,
            )
            artifacts.merged_constraints = merge_inferred_constraints(
                fields=artifacts.detected_fields,
                inferred_constraints=artifacts.inferred_constraints,
                feedback_by_field=artifacts.execution_feedback,
            )
            logger.debug(
                "Step 2 - inferred %d constraints", len(artifacts.inferred_constraints)
            )

            # Step 2b – translate to constraint IR profiles (ConstraintProfile).
            # The primary constraint per field (highest confidence) drives the IR.
            artifacts.constraint_profiles = _build_constraint_profiles(
                fields=artifacts.detected_fields,
                merged_constraints=artifacts.merged_constraints,
            )
            logger.debug(
                "Step 2b - built %d constraint profiles", len(artifacts.constraint_profiles)
            )

            artifacts.planned_test_cases = await generate(
                fields=artifacts.detected_fields,
                constraint_profiles=artifacts.constraint_profiles,
            )
            logger.debug(
                "Step 3 - planned %d test cases", len(artifacts.planned_test_cases)
            )

            artifacts.raw_results = await execute(
                page=page,
                test_cases=artifacts.planned_test_cases,
                target_url=target_url,
            )
            logger.debug("Step 4 - executed %d cases", len(artifacts.raw_results))

            artifacts.enriched_results = analyze(
                raw_results=artifacts.raw_results,
                test_cases=artifacts.planned_test_cases,
            )
            artifacts.execution_feedback = _build_execution_feedback(
                artifacts.enriched_results,
                artifacts.planned_test_cases,
            )
            artifacts.merged_constraints = apply_feedback_to_constraints(
                merged_constraints=artifacts.merged_constraints,
                feedback_by_field=artifacts.execution_feedback,
            )
            artifacts.inferred_constraints = [
                constraint
                for constraints in artifacts.merged_constraints.values()
                for constraint in constraints
            ]
            logger.debug("Step 5 - feedback fields=%d", len(artifacts.execution_feedback))

        summary = _build_run_summary(
            run_id=run_id,
            started_at=started_at,
            target_url=target_url,
            detected_fields=artifacts.detected_fields,
            results=artifacts.enriched_results,
        )

        reports_dir = (reports_root or settings.reports_dir) / run_id
        generate_report(
            summary=summary,
            results=artifacts.enriched_results,
            output_dir=reports_dir,
            inferred_constraints=artifacts.inferred_constraints,
            feedback_by_field=artifacts.execution_feedback,
        )

        logger.info(
            "Run %s complete - %d/%d passed (%.1f%%)",
            summary.run_id,
            summary.metrics.total_passed,
            summary.metrics.total_tests_executed,
            summary.metrics.pass_rate_percentage,
        )
        return summary
    except Exception as exc:
        logger.exception("Run %s failed: %s", run_id, exc)
        raise OrchestratorError(str(exc)) from exc
    finally:
        if managed_session is not None:
            await managed_session.close()


async def _try_create_managed_page() -> tuple[object | None, _ManagedPageSession | None]:
    try:
        from playwright.async_api import async_playwright

        playwright = await async_playwright().start()
        browser_type = getattr(playwright, settings.browser, playwright.chromium)
        browser = await browser_type.launch(headless=settings.headless)
        context = await browser.new_context()
        page = await context.new_page()
        return page, _ManagedPageSession(
            playwright=playwright,
            browser=browser,
            context=context,
            page=page,
        )
    except Exception as exc:
        logger.warning("Playwright startup unavailable: %s", exc)
        return None, None


def _build_run_summary(
    run_id: str,
    started_at: datetime,
    target_url: str,
    detected_fields: Sequence[FieldSchema],
    results: Sequence[ResultSchema],
) -> RunSummarySchema:
    total_passed = sum(1 for result in results if result.status == "pass")
    total_failed = sum(1 for result in results if result.status == "fail")
    total_executed = total_passed + total_failed
    pass_rate = (total_passed / total_executed * 100.0) if total_executed else 0.0

    return RunSummarySchema(
        run_id=run_id,
        timestamp=started_at,
        target_url=target_url,
        metrics=RunMetrics(
            total_fields_detected=len(detected_fields),
            total_tests_executed=total_executed,
            total_passed=total_passed,
            total_failed=total_failed,
            pass_rate_percentage=round(pass_rate, 2),
        ),
    )


def _build_execution_feedback(
    results: Sequence[ResultSchema],
    test_cases: Sequence[TestCaseSchema],
) -> dict[str, list[str]]:
    """Build field-level deterministic feedback from observed outcomes."""
    field_by_case_id = {tc.test_case_id: tc.field_id for tc in test_cases}
    feedback: dict[str, list[str]] = {}
    for result in results:
        field_id = field_by_case_id.get(result.test_case_id)
        if field_id is None:
            continue
        feedback.setdefault(field_id, []).append(result.observed_outcome)
    return feedback


def _build_constraint_profiles(
    fields: Sequence[FieldSchema],
    merged_constraints: Mapping[str, Sequence[InferredConstraintSchema]],
) -> list[ConstraintProfile]:
    """Translate each field into a ``ConstraintProfile`` via the IR adapter.

    Picks the highest-confidence inferred constraint per field as the primary
    driver; falls back to HTML-attribute-only translation when no constraint
    is available.
    """
    profiles: list[ConstraintProfile] = []
    for f in fields:
        field_constraints = list(merged_constraints.get(f.field_id, []))
        primary = (
            max(field_constraints, key=lambda c: c.confidence.score)
            if field_constraints
            else None
        )
        try:
            profiles.append(translate_to_profile(f, primary))
        except Exception as exc:  # never let IR translation break the run
            logger.warning(
                "IR translation failed for field %s: %s", f.field_id, exc
            )
    return profiles
