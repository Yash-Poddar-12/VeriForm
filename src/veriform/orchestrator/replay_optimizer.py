"""
veriform.orchestrator.replay_optimizer
======================================
Replay graph reduction based on semantic states.
"""

from __future__ import annotations

from typing import List, Dict, Any
from veriform.models.workflow import ActionSchema
from veriform.detector.semantic_state import SemanticState
from veriform.utils.logging import get_logger

logger = get_logger(__name__)

class ReplayOptimizer:
    def __init__(self):
        pass

    def optimize_trace(self, trace_events: List[Dict[str, Any]], semantic_states: Dict[str, SemanticState]) -> List[Dict[str, Any]]:
        """Skip redundant transitions if states are semantically equivalent."""
        optimized_trace = []
        seen_classifications = set()
        
        for event in trace_events:
            if event["type"] == "state":
                state_hash = event["data"].get("state_hash")
                semantic = semantic_states.get(state_hash)
                
                if semantic:
                    cls = semantic.classification
                    if cls in seen_classifications and cls not in ["generic_form"]:
                        logger.info(f"Optimization: Skipping redundant state transition into {cls}")
                        continue
                    seen_classifications.add(cls)
            
            optimized_trace.append(event)
            
        return optimized_trace
