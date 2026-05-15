"""
veriform.executor.executor
===========================
Playwright browser interaction module.

Phase 1 behavior:
- Deterministically navigates to the target URL for each test case.
- Fills a single target field value.
- Submits the form.
- Captures raw execution outcomes for analyzer classification.
"""

from __future__ import annotations

from time import perf_counter

from veriform.config import settings
from veriform.models.schemas import ResultSchema, TestCaseSchema
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


async def execute(
    page: object,
    test_cases: list[TestCaseSchema],
    target_url: str,
) -> list[ResultSchema]:
    """Fill and submit the form for each test case, returning raw outcomes."""
    results: list[ResultSchema] = []
    for test_case in test_cases:
        started = perf_counter()
        validation_message: str | None = None
        screenshot_path: str | None = None
        observed_outcome = "crash"
        try:
            await page.goto(target_url, timeout=settings.timeout_ms)
            pre_submit_url = str(getattr(page, "url", target_url))

            field_selector = _selector_for_test_case(test_case)
            await page.locator(field_selector).fill(str(test_case.input_value))
            await _submit_form(page, field_selector)

            try:
                await page.wait_for_load_state("networkidle", timeout=1500)
            except Exception:
                # Some forms stay on-page without navigation; that's valid Phase 1 behavior.
                pass

            validation_message = await _extract_validation_message(page)
            post_submit_url = str(getattr(page, "url", target_url))
            observed_outcome = _classify_raw_outcome(
                pre_submit_url=pre_submit_url,
                post_submit_url=post_submit_url,
                validation_message=validation_message,
            )
        except TimeoutError:
            observed_outcome = "timeout"
        except Exception as exc:
            observed_outcome = "crash"
            validation_message = str(exc)
            try:
                screenshot_path = await _capture_failure_screenshot(page, test_case.test_case_id)
            except Exception:
                screenshot_path = None

        duration_ms = int((perf_counter() - started) * 1000)
        results.append(
            ResultSchema(
                test_case_id=test_case.test_case_id,
                run_id=test_case.run_id,
                observed_outcome=observed_outcome,
                status="fail",
                validation_message=validation_message,
                screenshot_path=screenshot_path,
                execution_duration_ms=max(duration_ms, 0),
            )
        )
    logger.info("execute: completed %d test cases", len(results))
    return results


def _selector_for_test_case(test_case: TestCaseSchema) -> str:
    if test_case.dom_id:
        return f"#{test_case.dom_id}"
    if test_case.field_name:
        return f"[name='{test_case.field_name}']"
    return f"[name='{test_case.field_id}']"


async def _submit_form(page: object, field_selector: str) -> None:
    submit_selectors = [
        "form button[type='submit']",
        "form input[type='submit']",
        "button[type='submit']",
        "input[type='submit']",
    ]
    for selector in submit_selectors:
        try:
            await page.locator(selector).first.click(timeout=600)
            return
        except Exception:
            continue

    # Fallback: press Enter on current field when no explicit submit control is found.
    await page.locator(field_selector).press("Enter")


async def _extract_validation_message(page: object) -> str | None:
    selectors = [
        "[role='alert']",
        ".error",
        ".invalid",
        ".validation-error",
        "[aria-invalid='true']",
    ]
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            text = (await locator.inner_text(timeout=400)).strip()
            if text:
                return text
        except Exception:
            continue
    return None


def _classify_raw_outcome(
    pre_submit_url: str,
    post_submit_url: str,
    validation_message: str | None,
) -> str:
    if validation_message:
        return "validation_error"
    if post_submit_url != pre_submit_url:
        return "accepted"
    return "rejected"


async def _capture_failure_screenshot(page: object, test_case_id: str) -> str | None:
    path = settings.reports_dir / f"{test_case_id}_crash.png"
    await page.screenshot(path=str(path), full_page=True)
    return str(path)
