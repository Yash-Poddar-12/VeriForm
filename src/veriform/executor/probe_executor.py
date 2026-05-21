"""
veriform.executor.probe_executor
================================
Safe Playwright execution wrapper for behavioral mutations.
"""

from __future__ import annotations

import asyncio
from typing import List

from veriform.models.schemas import FieldSchema
from veriform.schemas.mutations import MutationProbe, ProbeResult
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


class ProbeExecutor:
    """Executes MutationProbes against a live Playwright page safely."""

    def __init__(self, page: object):
        self.page = page  # playwright.async_api.Page

    async def _safe_reset(self, selector: str):
        """Safely reset the field without triggering submits."""
        try:
            element = await self.page.query_selector(selector)
            if not element:
                return
            
            # Focus, clear, and blur
            await element.focus()
            await element.fill("")
            await element.evaluate("el => el.blur()")
            
            # Wait for microtasks
            await self.page.wait_for_timeout(50)
        except Exception as e:
            logger.debug(f"Reset failed for {selector}: {e}")

    async def execute_probes(self, field: FieldSchema, probes: List[MutationProbe]) -> List[ProbeResult]:
        """Execute a list of probes sequentially and collect results."""
        results = []
        
        # Build deterministic selector
        if field.dom_id:
            selector = f"id={field.dom_id}"
        else:
            selector = f"input[name='{field.name}']" if field.name else "input"

        for probe in probes:
            await self._safe_reset(selector)
            
            # Inject payload
            try:
                element = await self.page.wait_for_selector(selector, state="visible", timeout=2000)
                if not element:
                    logger.warning(f"Field {selector} not visible")
                    continue
                
                payload = str(probe.value)
                await element.focus()
                await element.fill(payload)
                
                # Natural trigger
                await element.evaluate("el => el.blur()")
                await self.page.wait_for_timeout(200)  # Debounce wait
                
                # Observe DOM state
                accepted = await self._is_accepted(element, field)
                errors = await self._capture_errors(element, field)
                submit_enabled = await self._check_submit_state()
                
                results.append(ProbeResult(
                    mutation_id=probe.mutation_id,
                    field_id=field.field_id,
                    probe_value=payload,
                    accepted=accepted,
                    observed_errors=errors,
                    submit_enabled=submit_enabled
                ))
                
            except Exception as e:
                logger.error(f"Error executing probe {probe.mutation_id}: {e}")
                results.append(ProbeResult(
                    mutation_id=probe.mutation_id,
                    field_id=field.field_id,
                    probe_value=str(probe.value),
                    accepted=False,
                    observed_errors=[f"Execution Error: {str(e)}"],
                    submit_enabled=False
                ))
                
        return results

    async def _is_accepted(self, element, field: FieldSchema) -> bool:
        """Determine if input is semantically accepted."""
        # 1. Check HTML5 validity
        is_valid = await element.evaluate("el => el.checkValidity ? el.checkValidity() : true")
        if not is_valid:
            return False
            
        # 2. Check aria-invalid
        aria_invalid = await element.get_attribute("aria-invalid")
        if aria_invalid in ["true", "spelling", "grammar"]:
            return False
            
        # 3. Check error classes (heuristic)
        class_name = await element.get_attribute("class") or ""
        if "error" in class_name.lower() or "invalid" in class_name.lower():
            return False
            
        return True

    async def _capture_errors(self, element, field: FieldSchema) -> List[str]:
        """Extract adjacent error messages."""
        errors = []
        
        # HTML5 validation message
        validation_message = await element.evaluate("el => el.validationMessage")
        if validation_message:
            errors.append(validation_message)
            
        # aria-errormessage
        err_id = await element.get_attribute("aria-errormessage")
        if err_id:
            try:
                err_node = await self.page.query_selector(f"id={err_id}")
                if err_node:
                    txt = await err_node.inner_text()
                    if txt:
                        errors.append(txt.strip())
            except Exception:
                pass
                
        return errors

    async def _check_submit_state(self) -> bool:
        """Determine if a generic submit button is enabled."""
        try:
            submit_btn = await self.page.query_selector("button[type='submit'], input[type='submit']")
            if submit_btn:
                is_disabled = await submit_btn.is_disabled()
                return not is_disabled
        except Exception:
            pass
        return True
