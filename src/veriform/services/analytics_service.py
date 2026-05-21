"""
veriform.services.analytics_service
===================================
Historical analytics and drift detection.
"""

from __future__ import annotations

from typing import Dict, List, Set, Any

from sqlalchemy import select
from veriform.persistence.database import get_session
from veriform.persistence.models import WorkflowRun, WorkflowState, WorkflowTransition
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


class AnalyticsService:
    async def get_regression_report(self, target_url: str, run_id_a: str, run_id_b: str) -> Dict[str, Any]:
        """Compare two runs of the same URL to detect state/transition regressions."""
        async with get_session() as db:
            run_a = await db.get(WorkflowRun, run_id_a)
            run_b = await db.get(WorkflowRun, run_id_b)
            
            if not run_a or not run_b:
                raise ValueError("Runs not found")
                
            # Fetch states
            states_a_res = await db.execute(select(WorkflowState.state_hash).where(WorkflowState.run_id == run_id_a))
            states_b_res = await db.execute(select(WorkflowState.state_hash).where(WorkflowState.run_id == run_id_b))
            
            states_a: Set[str] = set(states_a_res.scalars().all())
            states_b: Set[str] = set(states_b_res.scalars().all())
            
            missing_states = states_a - states_b
            new_states = states_b - states_a
            
            # Fetch transitions
            trans_a_res = await db.execute(
                select(WorkflowTransition).where(WorkflowTransition.run_id == run_id_a)
            )
            trans_b_res = await db.execute(
                select(WorkflowTransition).where(WorkflowTransition.run_id == run_id_b)
            )
            
            trans_a = {(t.from_state_hash, t.to_state_hash) for t in trans_a_res.scalars().all()}
            trans_b = {(t.from_state_hash, t.to_state_hash) for t in trans_b_res.scalars().all()}
            
            missing_transitions = trans_a - trans_b
            new_transitions = trans_b - trans_a
            
            # Calculate Healing Metrics (Mocked from DecisionLog tables that would exist in production)
            # In MVP, we deduce stability from missing transitions.
            stability_score = 1.0 - (len(missing_transitions) / max(len(trans_a), 1))
            
            return {
                "run_a": run_id_a,
                "run_b": run_id_b,
                "states_discovered_a": len(states_a),
                "states_discovered_b": len(states_b),
                "missing_states": list(missing_states),
                "new_states": list(new_states),
                "missing_transitions": list(missing_transitions),
                "new_transitions": list(new_transitions),
                "has_regression": len(missing_states) > 0 or len(missing_transitions) > 0,
                "metrics": {
                    "stability_score": round(max(0.0, stability_score), 2),
                    "recovery_success_rate": 0.85, # Placeholder for Phase 8 metrics
                    "workflow_complexity": len(states_b) + len(trans_b) * 1.5
                }
            }
