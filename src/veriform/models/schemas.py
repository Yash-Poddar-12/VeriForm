"""
veriform.models.schemas
=======================
Pydantic data contracts for the VeriForm pipeline.

Design notes
------------
- Deterministic execution remains the source of truth.
- AI structures are assistive metadata only and must be validated by execution.
- Child schemas include run_id for future normalized analytics exports.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Union

from pydantic import BaseModel, Field, field_validator


class FieldSchema(BaseModel):
    """Metadata for a single form input element, extracted from the DOM."""

    field_id: str = Field(..., description="Unique internal ID, e.g. 'field_001'")
    run_id: str = Field(..., description="Parent run session ID")
    label: Optional[str] = Field(None, description="Associated <label> text")
    placeholder: Optional[str] = Field(None, description="Placeholder hint text")
    context_text: Optional[str] = Field(
        None, description="Nearby descriptive/helper text around the field"
    )
    name: str = Field(..., description="HTML name attribute")
    dom_id: Optional[str] = Field(None, description="HTML id attribute")
    type: str = Field(..., description="Input type: text, email, number, textarea")
    required: bool = Field(False, description="Whether the field is marked required")
    min_length: Optional[int] = Field(None, ge=0)
    max_length: Optional[int] = Field(None, ge=1)
    pattern: Optional[str] = Field(None, description="HTML pattern attribute (regex)")
    min_val: Optional[float] = Field(None, description="Min value for numeric/date")
    max_val: Optional[float] = Field(None, description="Max value for numeric/date")


class ConfidenceScoreSchema(BaseModel):
    """Confidence metadata used for AI-assisted ranking decisions."""

    score: float = Field(..., ge=0.0, le=1.0)
    source: str = Field(..., description="Inference source, e.g. label_inference")
    rationale: Optional[str] = Field(None, description="Short explanation for score")


class InferredConstraintSchema(BaseModel):
    """AI-assisted hypothesis for a field constraint that needs deterministic validation."""

    constraint_id: str = Field(..., description="Unique internal ID")
    run_id: str = Field(..., description="Parent run session ID")
    field_id: str = Field(..., description="Reference to FieldSchema.field_id")
    semantic_type: str = Field(..., description="Inferred semantic label, e.g. phone")
    likely_format: str = Field(..., description="Likely input format or regex string")
    confidence: ConfidenceScoreSchema


class CandidateInputSchema(BaseModel):
    """Candidate value proposal generated before final combination planning."""

    candidate_id: str = Field(..., description="Unique candidate identifier")
    run_id: str = Field(..., description="Parent run session ID")
    field_id: str = Field(..., description="Reference to FieldSchema.field_id")
    input_value: Union[str, int, float, bool] = Field(..., description="Candidate payload")
    category: str = Field(..., description="Candidate category, e.g. valid, boundary-max")
    expected_outcome: str = Field(..., description="accept or reject")
    priority_score: float = Field(0.0, ge=0.0, le=1.0)

    @field_validator("expected_outcome")
    @classmethod
    def _validate_expected_outcome(cls, v: str) -> str:
        allowed = {"accept", "reject"}
        if v not in allowed:
            raise ValueError(f"expected_outcome must be one of {allowed}, got '{v}'")
        return v


class CombinationPlanSchema(BaseModel):
    """Deterministic selection plan for candidate execution order."""

    plan_id: str = Field(..., description="Unique combination plan ID")
    run_id: str = Field(..., description="Parent run session ID")
    strategy: str = Field(..., description="Planning strategy identifier")
    max_combinations: int = Field(..., ge=1)
    selected_candidates: list[CandidateInputSchema] = Field(default_factory=list)


class TestCaseSchema(BaseModel):
    """A single executable test scenario targeting one form field."""

    __test__ = False
    test_case_id: str = Field(..., description="Unique identifier, e.g. 'tc_102'")
    field_id: str = Field(..., description="Reference to FieldSchema.field_id")
    run_id: str = Field(..., description="Parent run session ID")
    field_name: Optional[str] = Field(
        None, description="HTML name used to resolve a deterministic selector"
    )
    dom_id: Optional[str] = Field(
        None, description="HTML id used to resolve a deterministic selector"
    )
    input_value: Union[str, int, float, bool] = Field(
        ..., description="Payload to inject into the field"
    )
    category: str = Field(..., description="Test category label")
    expected_outcome: str = Field(..., description="accept or reject")

    @field_validator("expected_outcome")
    @classmethod
    def _validate_expected_outcome(cls, v: str) -> str:
        allowed = {"accept", "reject"}
        if v not in allowed:
            raise ValueError(f"expected_outcome must be one of {allowed}, got '{v}'")
        return v


class ResultSchema(BaseModel):
    """Observed outcome of a single executed test case."""

    test_case_id: str = Field(..., description="Reference to TestCaseSchema")
    run_id: str = Field(..., description="Parent run session ID")
    observed_outcome: str = Field(
        ...,
        description=(
            "accepted | rejected | validation_error | timeout | crash "
            "(legacy: accept | reject | error)"
        ),
    )
    status: str = Field(..., description="pass or fail")
    validation_message: Optional[str] = Field(
        None, description="DOM error message text extracted from the page"
    )
    screenshot_path: Optional[str] = Field(
        None, description="Relative path to a failure screenshot"
    )
    execution_duration_ms: int = Field(
        ..., ge=0, description="Wall-clock time for the test case in milliseconds"
    )

    @field_validator("observed_outcome")
    @classmethod
    def _validate_observed_outcome(cls, v: str) -> str:
        allowed = {
            "accepted",
            "rejected",
            "validation_error",
            "timeout",
            "crash",
            "accept",
            "reject",
            "error",
        }
        if v not in allowed:
            raise ValueError(f"observed_outcome must be one of {allowed}, got '{v}'")
        return v

    @field_validator("status")
    @classmethod
    def _validate_status(cls, v: str) -> str:
        allowed = {"pass", "fail"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got '{v}'")
        return v


class RunMetrics(BaseModel):
    """Aggregate counters for a single test run."""

    total_fields_detected: int = Field(..., ge=0)
    total_tests_executed: int = Field(..., ge=0)
    total_passed: int = Field(..., ge=0)
    total_failed: int = Field(..., ge=0)
    pass_rate_percentage: float = Field(..., ge=0.0, le=100.0)


class RunSummarySchema(BaseModel):
    """Aggregated results for one complete form evaluation session."""

    run_id: str = Field(..., description="Unique session identifier (UUID)")
    timestamp: datetime = Field(..., description="ISO-8601 execution start time")
    target_url: str = Field(..., description="The URL under test")
    metrics: RunMetrics
