"""
veriform.executor.executor
===========================
Playwright browser interaction module.

Phase 1 behaviour
-----------------
* Navigates to the target URL for each test case (fresh state per case).
* Fills a single target field with the candidate value.
* Submits the form via button discovery or Enter-key fallback.
* Captures raw execution outcomes for the analyzer to classify.
* Takes screenshots on crash and on unexpected failures.

Phase 1 robustness improvements (current)
------------------------------------------
* Retry on ``TimeoutError`` – up to ``_MAX_RETRIES`` attempts per case.
* Broader submit-button detection (aria-label, value attribute, role=button).
* Post-submit navigation wait extended to ``_POST_SUBMIT_WAIT_MS``.
* Screenshot captured on any outcome other than ``accepted`` / ``rejected``
  when the test case expected ``accept`` (i.e. on genuine failures).
"""

from __future__ import annotations

from time import perf_counter
from typing import Optional

from veriform.config import settings
from veriform.models.schemas import ResultSchema, TestCaseSchema
from veriform.utils.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

_POST_SUBMIT_WAIT_MS: int = 5_000
"""Milliseconds to wait for ``networkidle`` after submit (generous for SPAs)."""

_MAX_RETRIES: int = 2
"""Maximum number of retry attempts on ``TimeoutError`` per test case."""

_VALIDATION_SELECTORS: tuple[str, ...] = (
    "[role='alert']",
    "[aria-live='polite']",
    "[aria-live='assertive']",
    ".error",
    ".invalid",
    ".validation-error",
    ".field-error",
    "[aria-invalid='true']",
    ".help-block",
    ".form-error",
)

_SUBMIT_SELECTORS: tuple[str, ...] = (
    "form button[type='submit']",
    "form input[type='submit']",
    "button[type='submit']",
    "input[type='submit']",
    "button[aria-label*='submit' i]",
    "button[value*='submit' i]",
    "[role='button'][type='submit']",
    "button:has-text('Submit')",
    "button:has-text('Login')",
    "button:has-text('Sign in')",
    "button:has-text('Continue')",
    "button:has-text('Next')",
    "button:has-text('Send')",
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def execute(
    page: object,
    test_cases: list[TestCaseSchema],
    target_url: str,
) -> list[ResultSchema]:
    """Execute *test_cases* sequentially against *target_url*.

    The caller is responsible for providing an already-open Playwright ``Page``
    (or compatible fake).  Navigation state is reset for each test case.

    Returns
    -------
    list[ResultSchema]
        One result per test case.  ``status`` is always ``"fail"`` at this
        stage; the :mod:`veriform.analyzer` upgrades it to ``"pass"``
        by comparing against expected outcomes.
    """
    results: list[ResultSchema] = []

    for test_case in test_cases:
        result = await _execute_with_retry(page, target_url, test_case)
        results.append(result)

    return results


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _execute_with_retry(
    page: object,
    target_url: str,
    test_case: TestCaseSchema,
) -> ResultSchema:
    """Attempt *test_case* execution up to ``_MAX_RETRIES`` times on timeout."""
    last_error: Optional[Exception] = None

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            return await _run_single(page, target_url, test_case)
        except TimeoutError as exc:
            last_error = exc
            logger.warning(
                "Timeout on %s (attempt %d/%d): %s",
                test_case.test_case_id,
                attempt,
                _MAX_RETRIES,
                exc,
            )
        except Exception as exc:
            # Non-timeout errors are not retried.
            last_error = exc
            logger.warning(
                "Crash on %s: %s",
                test_case.test_case_id,
                exc,
            )
            break

    # All retries exhausted – capture a crash screenshot and return error result.
    screenshot_path = await _capture_screenshot(page, test_case.test_case_id, "crash")
    return ResultSchema(
        test_case_id=test_case.test_case_id,
        run_id=test_case.run_id,
        observed_outcome="crash",
        status="fail",
        validation_message=str(last_error) if last_error else "unknown error",
        screenshot_path=screenshot_path,
        execution_duration_ms=0,
    )


async def _run_single(
    page: object,
    target_url: str,
    test_case: TestCaseSchema,
) -> ResultSchema:
    """Execute a single test case and return the raw ``ResultSchema``."""
    started = perf_counter()
    observed_outcome: str = "crash"  # safe default overwritten below

    # Fresh navigation for each test case ensures clean state.
    await page.goto(target_url, timeout=settings.timeout_ms)  # type: ignore[attr-defined]
    pre_submit_url: str = page.url  # type: ignore[attr-defined]

    field_selector = _selector_for_test_case(test_case)
    await page.locator(field_selector).fill(str(test_case.input_value))  # type: ignore[attr-defined]

    await _submit_form(page, field_selector)

    # Wait for navigation / dynamic validation to settle.
    try:
        await page.wait_for_load_state("networkidle", timeout=_POST_SUBMIT_WAIT_MS)  # type: ignore[attr-defined]
    except Exception:
        # Some forms stay on-page and never reach networkidle – that is fine.
        pass

    validation_message = await _extract_validation_message(page)
    post_submit_url: str = page.url  # type: ignore[attr-defined]

    observed_outcome = _classify_raw_outcome(
        pre_submit_url, post_submit_url, validation_message
    )

    duration_ms = int((perf_counter() - started) * 1_000)

    # Screenshot on unexpected failures (not on deliberate reject tests).
    screenshot_path: Optional[str] = None
    if observed_outcome in ("crash", "timeout"):
        screenshot_path = await _capture_screenshot(
            page, test_case.test_case_id, observed_outcome
        )

    return ResultSchema(
        test_case_id=test_case.test_case_id,
        run_id=test_case.run_id,
        observed_outcome=observed_outcome,
        status="fail",  # analyzer upgrades this
        validation_message=validation_message,
        screenshot_path=screenshot_path,
        execution_duration_ms=duration_ms,
    )


def _selector_for_test_case(test_case: TestCaseSchema) -> str:
    """Return the most specific CSS selector for the field under test."""
    if test_case.dom_id:
        return f"#{test_case.dom_id}"
    if test_case.field_name:
        return f"[name='{test_case.field_name}']"
    return f"[name='{test_case.field_id}']"


async def _submit_form(page: object, field_selector: str) -> None:
    """Attempt to submit the form using the broadest set of selector strategies."""
    for sel in _SUBMIT_SELECTORS:
        try:
            locator = page.locator(sel)  # type: ignore[attr-defined]
            await locator.first.click(timeout=600)
            return
        except Exception:
            continue

    # Final fallback: press Enter on the active field.
    try:
        await page.locator(field_selector).first.press("Enter")  # type: ignore[attr-defined]
    except Exception:
        pass


async def _extract_validation_message(page: object) -> Optional[str]:
    """Probe common validation-error selectors and return the first non-empty text."""
    for sel in _VALIDATION_SELECTORS:
        try:
            text: str = await page.locator(sel).first.inner_text(timeout=400)  # type: ignore[attr-defined]
            if text.strip():
                return text.strip()
        except Exception:
            continue
    return None


def _classify_raw_outcome(
    pre_submit_url: str,
    post_submit_url: str,
    validation_message: Optional[str],
) -> str:
    """Map post-submission state to a canonical outcome string.

    Priority:
    1. Validation message present  → ``"validation_error"``
    2. URL changed                 → ``"accepted"``
    3. No change                   → ``"rejected"``
    """
    if validation_message:
        return "validation_error"
    if post_submit_url != pre_submit_url:
        return "accepted"
    return "rejected"


async def _capture_screenshot(
    page: object,
    test_case_id: str,
    label: str,
) -> Optional[str]:
    """Capture a full-page screenshot and return the relative path."""
    try:
        from pathlib import Path

        path = Path(settings.reports_dir) / f"{test_case_id}_{label}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        await page.screenshot(path=str(path), full_page=True)  # type: ignore[attr-defined]
        return str(path)
    except Exception as exc:
        logger.debug("Screenshot failed for %s: %s", test_case_id, exc)
        return None
