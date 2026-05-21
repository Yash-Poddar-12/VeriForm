"""
veriform.orchestrator.replay_repair
===================================
Self-healing deterministic replay system.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from veriform.config import settings
from veriform.detector.selector_resilience import SelectorResilienceEngine
from veriform.models.healing import DecisionLog, SelectorFingerprint
from veriform.models.workflow import ActionSchema
from veriform.executor.action_engine import ActionEngine
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


class ReplayRepairEngine:
    def __init__(self, page: Page, run_id: str):
        self.page = page
        self.run_id = run_id
        self.action_engine = ActionEngine(page)
        self.resilience_engine = SelectorResilienceEngine(page)
        self.decision_logs: List[DecisionLog] = []

    async def execute_repair_trace(self, trace_file: Path) -> bool:
        """Read a trace JSONL and execute it with self-healing boundaries."""
        if not trace_file.exists():
            logger.error("Trace file not found: %s", trace_file)
            return False
            
        with trace_file.open("r", encoding="utf-8") as f:
            lines = f.readlines()
            
        for line in lines:
            event = json.loads(line)
            if event["type"] == "action":
                action = ActionSchema(**event["data"])
                success = await self._execute_action_with_healing(action)
                if not success:
                    logger.error("Unrecoverable failure at action: %s", action.action_id)
                    return False
                    
        return True

    async def _execute_action_with_healing(self, action: ActionSchema) -> bool:
        """Attempt action, and invoke resilience engine on timeout."""
        try:
            # We override timeout to strict bounds to prevent stalling.
            # Normal action engine usually waits 30s. We cap it earlier during repair to fail-fast and heal.
            # Unless it's a wait action.
            if action.type == "wait":
                await self.action_engine.execute(action)
                return True
                
            await asyncio.wait_for(
                self.action_engine.execute(action), 
                timeout=settings.heal_timeout_seconds
            )
            return True
            
        except (PlaywrightTimeoutError, asyncio.TimeoutError) as e:
            if not settings.enable_self_healing:
                logger.error("Action failed and healing is disabled: %s", e)
                return False
                
            logger.warning("Action timeout. Triggering Self-Healing for selector: %s", action.selector)
            
            # 1. Recover historical fingerprint (In a real system, this would be loaded from DB/Trace. For now, we mock it based on the action data to simulate recovery).
            # For demonstration, we construct a fake historical fingerprint. The true Phase 1 implementation would load the actual `SelectorFingerprint` saved during the original run.
            historical_fp = SelectorFingerprint(
                tag="input", # Guessing
                text_content=None,
                placeholder=action.selector.replace("#", "") if action.selector else None, # Rough heuristic mock
                hierarchy_depth=0
            )
            
            # 2. Attempt repair
            try:
                candidate = await asyncio.wait_for(
                    self.resilience_engine.attempt_repair(action.selector or "", historical_fp),
                    timeout=settings.heal_timeout_seconds
                )
            except asyncio.TimeoutError:
                logger.error("Self-healing timed out.")
                return False
                
            if candidate:
                # Log Decision
                log = DecisionLog(
                    run_id=self.run_id,
                    action_type="selector_repair",
                    original_target=action.selector,
                    repaired_target=candidate.selector,
                    confidence_score=candidate.confidence_score,
                    reasoning_trace=[f"Heuristic matched with {candidate.confidence_score:.2f} score"],
                    timestamp=datetime.now(tz=timezone.utc).isoformat()
                )
                self.decision_logs.append(log)
                
                # Retry with new selector
                action.selector = candidate.selector
                try:
                    await asyncio.wait_for(
                        self.action_engine.execute(action),
                        timeout=settings.heal_timeout_seconds
                    )
                    logger.info("Successfully healed and executed action.")
                    return True
                except Exception as e:
                    logger.error("Failed executing healed selector: %s", e)
                    return False
                    
            return False
