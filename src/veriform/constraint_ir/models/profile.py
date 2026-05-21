"""
veriform.constraint_ir.models.profile
=======================================
Root IR schema for a single form field.

``ConstraintProfile`` is the compiled, field-level representation that the
generation layer consumes.  It bundles:

- semantic classification (e.g. ``"mobile_number"``)
- structural layout via a ``SegmentModel``
- provenance metadata (source + confidence)

Profiles are produced by ``constraint_ir.adapters.translator`` and consumed
by ``generator.candidate_generator`` to synthesise boundary-aware test values.
"""

from __future__ import annotations

from pydantic import Field, field_validator

from veriform.constraint_ir.models.base import ImmutableIRModel
from veriform.constraint_ir.models.segments import SegmentModel


class ConstraintProfile(ImmutableIRModel):
    """Root IR for a single detected form field.

    Fields
    ------
    profile_id
        Globally unique ID derived from the field's ``field_id``
        (pattern: ``"profile_<field_id>"``).
    field_name
        HTML ``name`` attribute of the source element.
    semantic_type
        Inferred or declared semantic label (e.g. ``"mobile_number"``).
    segment_model
        Structural decomposition into typed segments.
    source
        Provenance tag; one of ``"html_attribute"``, ``"ai_inferred"``,
        ``"structured_registry"``, or ``"deterministic"``.
    confidence
        Aggregate confidence in the profile (0.0 – 1.0).
    """

    profile_id: str
    field_name: str
    semantic_type: str
    segment_model: SegmentModel
    source: str = "deterministic"
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)

    @field_validator("source")
    @classmethod
    def _validate_source(cls, v: str) -> str:
        allowed = {
            "html_attribute",
            "ai_inferred",
            "structured_registry",
            "deterministic",
            "user_override",
        }
        if v not in allowed:
            raise ValueError(f"source must be one of {sorted(allowed)}, got {v!r}")
        return v

    # ------------------------------------------------------------------
    # Convenience accessors
    # ------------------------------------------------------------------

    def total_min_length(self) -> int:
        """Delegate to ``segment_model.total_min_length()``."""
        return self.segment_model.total_min_length()

    def total_max_length(self) -> int:
        """Delegate to ``segment_model.total_max_length()``."""
        return self.segment_model.total_max_length()

    def is_single_segment(self) -> bool:
        """Return ``True`` when the profile has exactly one segment."""
        return self.segment_model.segment_count() == 1

    def segment_count(self) -> int:
        """Number of segments in the underlying model."""
        return self.segment_model.segment_count()
