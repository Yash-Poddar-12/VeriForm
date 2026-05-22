from pydantic import BaseModel
from typing import Any, Dict
from .observation_delta import ObservationDelta

class ProbeResult(BaseModel):
    """Immutable record of a single mutation execution."""
    mutated_field: str
    candidate_value: Any
    baseline_hash: str
    delta: ObservationDelta
    attribution: Dict[str, Any]
    confidence_score: float
    evidence_hash: str
