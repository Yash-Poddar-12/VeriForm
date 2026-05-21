"""
veriform.detector.semantic_state
================================
Models for semantic state representation.
"""

from __future__ import annotations

from typing import List, Dict, Optional
from pydantic import BaseModel, Field

class SemanticState(BaseModel):
    """A compressed, semantically clustered representation of a DOM state."""
    classification: str  # e.g., 'auth_flow', 'payment_flow', 'otp_screen', 'generic_form', 'confirmation'
    confidence: float
    field_roles: List[str] = Field(default_factory=list)
    has_errors: bool = False
    is_terminal: bool = False
    raw_hash: str
