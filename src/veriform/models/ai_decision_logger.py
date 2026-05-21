"""
veriform.models.ai_decision_logger
==================================
Schema for AI decision tracking.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

class AIDecisionLog(BaseModel):
    """Artifact schema for any AI invocation."""
    run_id: str
    action_context: str
    prompt: str
    model: str
    latency_ms: float
    confidence: float
    reasoning_summary: Optional[str] = None
    output_mutation: Any = None
    timestamp: str
