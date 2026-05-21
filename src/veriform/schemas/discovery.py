from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class RegexInference(BaseModel):
    """Deterministic, human-readable synthesized regex contract (used by older schemas)."""
    pattern: str = Field(..., description="Synthesized anchored regex pattern")
    confidence: float = Field(..., ge=0.0, le=1.0)
    examples_accepted: List[str] = Field(default_factory=list)
    examples_rejected: List[str] = Field(default_factory=list)
    description: str = Field(..., description="Human-readable explanation of the constraint")


class RegexSynthesisResult(BaseModel):
    """Deterministic, human-readable synthesized regex contract (Phase 5)."""
    field_id: str
    semantic_type: Optional[str] = None
    required: bool = False
    regex: str = Field(..., description="Synthesized anchored regex pattern")
    confidence: float = Field(..., ge=0.0, le=1.0)
    description: str = Field(..., description="Human-readable explanation of the constraint")
    accepted_examples: List[str] = Field(default_factory=list)
    rejected_examples: List[str] = Field(default_factory=list)
    evidence: List[str] = Field(default_factory=list, description="Reasoning trace for why this regex was chosen")


class FieldSpecification(BaseModel):
    field_id: str
    name: str
    semantic_type: Optional[str] = None
    required: Optional[bool] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_charsets: Optional[List[str]] = None
    inferred_regex: Optional[RegexInference] = None
    synthesized_regex: Optional[RegexSynthesisResult] = None
    html_attributes: Dict[str, Any] = Field(default_factory=dict)
    validation_messages: List[str] = Field(default_factory=list)


class ValidationContract(BaseModel):
    run_id: str
    target_url: str
    fields: List[FieldSpecification] = Field(default_factory=list)
