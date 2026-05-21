"""
veriform.models.healing
=======================
Schemas for autonomous self-healing and decision logging.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

class SelectorFingerprint(BaseModel):
    """Semantic signature of a DOM element for resilient recovery."""
    tag: str
    roles: List[str] = Field(default_factory=list)
    label: Optional[str] = None
    aria_label: Optional[str] = None
    placeholder: Optional[str] = None
    text_content: Optional[str] = None
    nearby_text: List[str] = Field(default_factory=list)
    hierarchy_depth: int = 0
    attributes: Dict[str, str] = Field(default_factory=dict)
    
class RepairCandidate(BaseModel):
    """A scored candidate during self-healing."""
    selector: str
    confidence_score: float
    matching_heuristics: List[str] = Field(default_factory=list)

class DecisionLog(BaseModel):
    """Explainable artifact for autonomous operations."""
    run_id: str
    action_type: str  # "selector_repair", "explore_branch", "ai_mutation"
    original_target: Optional[str] = None
    repaired_target: Optional[str] = None
    confidence_score: float
    reasoning_trace: List[str] = Field(default_factory=list)
    timestamp: str
