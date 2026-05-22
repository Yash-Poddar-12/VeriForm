import asyncio
import time

from playwright.async_api import Page

from veriform_sync_engine.dom_stability import DOMStabilityDetector
from veriform_core.exceptions import SyncTimeoutError


class SyncManager:
    """
    Deterministic orchestrator handling:
    - DOM stability
    - network idle detection
    - failed response tracking
    - listener lifecycle cleanup
    """

    def __init__(self, page: Page):
        self.page = page

        self.dom_detector = DOMStabilityDetector(page)

        self.active_requests = set()
        self.failed_responses = []

        self._request_handler = None
        self._request_finished_handler = None
        self._request_failed_handler = None
        self._response_handler = None

    async def setup(self):
        """
        Inject DOM observer and attach deterministic network lifecycle listeners.
        Calls cleanup() first to remove any previously-registered listeners,
        preventing duplicate event accumulation across probe iterations.
        """
        self.cleanup()
        await self.dom_detector.inject_observer()

        self.active_requests.clear()
        # NOTE: failed_responses is NOT cleared here.
        # Call reset_probe_state() explicitly just before submitting a mutation.

        # Store handler references so cleanup() can remove them on the next setup() call
        _req_handler = lambda req: self.active_requests.add(req)
        _fin_handler = lambda req: self.active_requests.discard(req)
        _fail_handler = lambda req: self.active_requests.discard(req)
        _res_handler = lambda res: (
            self.failed_responses.append({"url": res.url, "status": res.status})
            if res.status >= 400 and {"url": res.url, "status": res.status} not in self.failed_responses
            else None
        )

        self._request_handler = _req_handler
        self._request_finished_handler = _fin_handler
        self._request_failed_handler = _fail_handler
        self._response_handler = _res_handler

        self.page.on("request", _req_handler)
        self.page.on("requestfinished", _fin_handler)
        self.page.on("requestfailed", _fail_handler)
        self.page.on("response", _res_handler)

    def reset_probe_state(self):
        """Clear collected network failures for a new probe observation window.
        Call this immediately before triggering a form submission, never during rollback."""
        self.failed_responses.clear()

    def cleanup(self):
        """
        Prevent listener leaks across:
        - reloads
        - rollback execution
        - mutation probes
        """

        if self._request_handler:
            self.page.remove_listener("request", self._request_handler)

        if self._request_finished_handler:
            self.page.remove_listener(
                "requestfinished",
                self._request_finished_handler,
            )

        if self._request_failed_handler:
            self.page.remove_listener(
                "requestfailed",
                self._request_failed_handler,
            )

        if self._response_handler:
            self.page.remove_listener(
                "response",
                self._response_handler,
            )

    async def wait_for_idle(self, timeout_ms: int = 10000):
        """Blocks until both network is quiet AND DOM is stable.

        Uses Playwright's built-in networkidle state which waits for ≥500ms of
        zero in-flight connections — this correctly captures JS-deferred fetches
        (e.g. setTimeout → fetch()) that fire after the triggering click returns.
        """
        import logging
        try:
            await self.page.wait_for_load_state("networkidle", timeout=timeout_ms)
            logging.debug("[SyncManager] networkidle reached.")
            await self.dom_detector.wait_for_stability(timeout_ms)
        except Exception as e:
            # Timeout here is non-fatal for observation; log and continue.
            logging.warning(f"[SyncManager] wait_for_idle timed out: {e}")