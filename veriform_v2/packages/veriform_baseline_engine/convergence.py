from typing import List, Dict
import hashlib
import json
from veriform_core.budget import ProbeBudget

class ConvergenceTracker:
    """Bounded convergence logic to prevent infinite fuzzing loops."""
    def __init__(self, budget: ProbeBudget):
        self.budget = budget
        self.history: List[Dict] = []
        
    def record_delta(self, delta: Dict):
        self.history.append(delta)
        
    def check_stagnation(self) -> bool:
        if len(self.history) >= self.budget.max_identical_failures:
            recent = self.history[-self.budget.max_identical_failures:]
            def hash_delta(d):
                return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
            hashes = [hash_delta(d) for d in recent]
            if len(set(hashes)) == 1:
                return True
        return False
