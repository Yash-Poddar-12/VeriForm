"""
veriform.executor.action_engine
===============================
Execution engine for discrete DOM actions.
Supports fill, click, select, wait, navigate, and submit.
"""

from __future__ import annotations

import asyncio
from typing import Any

from veriform.models.workflow import ActionSchema
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


class ActionEngine:
    """Executes ActionSchema payloads against a Playwright Page."""
    
    def __init__(self, page: Any):
        self.page = page

    async def execute_action(self, action: ActionSchema) -> None:
        """Execute a single deterministic action."""
        logger.debug("Executing action: %s", action.action_id)
        
        if action.type == "fill":
            await self._fill(action)
        elif action.type == "click":
            await self._click(action)
        elif action.type == "select":
            await self._select(action)
        elif action.type == "wait":
            await self._wait(action)
        elif action.type == "navigate":
            await self._navigate(action)
        elif action.type == "submit":
            await self._submit(action)
        else:
            raise ValueError(f"Unknown action type: {action.type}")

    async def _fill(self, action: ActionSchema) -> None:
        if not action.selector:
            raise ValueError("Fill action requires a selector")
        val = str(action.value) if action.value is not None else ""
        locator = self.page.locator(action.selector).first
        await locator.fill(val, timeout=action.timeout_ms or 5000)

    async def _click(self, action: ActionSchema) -> None:
        if not action.selector:
            raise ValueError("Click action requires a selector")
        locator = self.page.locator(action.selector).first
        await locator.click(timeout=action.timeout_ms or 5000)

    async def _select(self, action: ActionSchema) -> None:
        if not action.selector:
            raise ValueError("Select action requires a selector")
        val = str(action.value) if action.value is not None else ""
        locator = self.page.locator(action.selector).first
        await locator.select_option(val, timeout=action.timeout_ms or 5000)

    async def _wait(self, action: ActionSchema) -> None:
        # If selector provided, wait for it to be visible
        if action.selector:
            locator = self.page.locator(action.selector).first
            await locator.wait_for(state="visible", timeout=action.timeout_ms or 5000)
        elif action.timeout_ms:
            # Just wait for duration
            await asyncio.sleep(action.timeout_ms / 1000.0)
        else:
            # Wait for network idle
            try:
                await self.page.wait_for_load_state("networkidle", timeout=5000)
            except Exception:
                pass

    async def _navigate(self, action: ActionSchema) -> None:
        if not action.value:
            raise ValueError("Navigate action requires a URL in value")
        await self.page.goto(str(action.value), timeout=action.timeout_ms or 30000)

    async def _submit(self, action: ActionSchema) -> None:
        from veriform.executor.executor import _SUBMIT_SELECTORS
        
        # Try finding and clicking submit
        for sel in _SUBMIT_SELECTORS:
            try:
                locator = self.page.locator(sel).first
                if await locator.is_visible(timeout=500):
                    await locator.click(timeout=action.timeout_ms or 2000)
                    return
            except Exception:
                continue
                
        # Fallback to pressing Enter if a selector was given
        if action.selector:
            try:
                await self.page.locator(action.selector).first.press("Enter", timeout=1000)
            except Exception:
                pass
