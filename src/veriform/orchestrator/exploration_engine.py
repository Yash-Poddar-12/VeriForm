"""
veriform.orchestrator.exploration_engine
========================================
Risk-based queue prioritization and novelty scoring.
"""

from __future__ import annotations

from typing import Dict, List, Any
import re
from veriform.models.workflow import ActionSchema
from veriform.config import settings
from veriform.utils.logging import get_logger

logger = get_logger(__name__)

class ExplorationEngine:
    def __init__(self):
        self.enable_exploration = settings.enable_autonomous_exploration
        self.visited_state_counts: Dict[str, int] = {}
        
    def _score_action_risk(self, action: ActionSchema) -> float:
        """Heuristic risk scoring based on keywords (Auth, Payment)."""
        score = 1.0
        
        target = str(action.selector or action.value or "").lower()
        
        # Auth flows
        if re.search(r'login|signin|password|auth|register|signup', target):
            score += 2.0
            
        # Payments
        if re.search(r'checkout|pay|credit|card|billing|cvv', target):
            score += 3.0
            
        return score

    def score_branch(self, to_state_hash: str, transition_action: ActionSchema) -> float:
        """Calculate the priority of a workflow branch."""
        if not self.enable_exploration:
            return 1.0
            
        # Novelty: Prefer unvisited or rarely visited states
        visit_count = self.visited_state_counts.get(to_state_hash, 0)
        novelty_score = 10.0 / (visit_count + 1)
        
        # Risk Priority
        risk_score = self._score_action_risk(transition_action)
        
        return novelty_score * risk_score

    def record_visit(self, state_hash: str) -> None:
        """Mark a state as visited for novelty scoring decay."""
        self.visited_state_counts[state_hash] = self.visited_state_counts.get(state_hash, 0) + 1

    def sort_queue(self, queue: List[Any], key_extractor) -> List[Any]:
        """Sort the exploration frontier based on the branch scores."""
        if not self.enable_exploration:
            return queue
            
        # Sort descending by score
        queue.sort(key=lambda item: self.score_branch(*key_extractor(item)), reverse=True)
        return queue
