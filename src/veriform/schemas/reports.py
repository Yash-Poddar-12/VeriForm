from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

from veriform.schemas.discovery import ValidationContract

class ExecutiveSummaryMetrics(BaseModel):
    """Core metrics for the validation run."""
    total_fields: int = Field(..., ge=0)
    fully_specified_fields: int = Field(..., ge=0, description="Fields that reached a definitive validation contract")
    total_mutations_tested: int = Field(..., ge=0)
    run_duration_ms: int = Field(..., ge=0)

class ExecutiveSummary(BaseModel):
    """High-level summary of the validation discovery run."""
    run_id: str = Field(..., description="Unique run identifier")
    target_url: str = Field(..., description="Target URL")
    timestamp: datetime = Field(..., description="Run start time")
    mode: str = Field(..., description="'fast_mode' or 'discovery_mode'")
    metrics: ExecutiveSummaryMetrics
    
class FieldAnalysisReport(BaseModel):
    """Detailed breakdown of a single field's analysis."""
    field_id: str = Field(...)
    semantic_type: Optional[str] = Field(None)
    confidence_score: float = Field(0.0)
    inferred_regex_pattern: Optional[str] = Field(None)
    accepted_examples: List[str] = Field(default_factory=list)
    rejected_examples: List[str] = Field(default_factory=list)
    mutation_timeline: List[dict] = Field(default_factory=list, description="Timeline of behavioral probes and responses")

class FinalDiscoveryReport(BaseModel):
    """The complete aggregated report data."""
    summary: ExecutiveSummary
    contract: ValidationContract
    field_analyses: List[FieldAnalysisReport]
