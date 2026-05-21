"""
veriform.constraint_ir.models.segments
=======================================
Segment-level IR for multi-part structured identifiers.

A *segment* is a positional slice of a field value (e.g. the BIN prefix of a
card number, the area code of an SSN).  A *SegmentModel* groups segments into
an ordered collection and optionally records the separator character.

Checksum strategies are kept intentionally minimal for Phase 1; the
discriminated-union makes it straightforward to add new algorithms later.
"""

from __future__ import annotations

from typing import Annotated, Literal, Optional, Union

from pydantic import Field

from veriform.constraint_ir.models.atomic import AtomicConstraintType
from veriform.constraint_ir.models.base import ImmutableIRModel


# ---------------------------------------------------------------------------
# Checksum strategies
# ---------------------------------------------------------------------------


class LuhnChecksum(ImmutableIRModel):
    """Luhn algorithm – credit cards, IMEI numbers."""

    type: Literal["luhn"] = "luhn"


class Mod97Checksum(ImmutableIRModel):
    """ISO 7064 Mod-97 – IBAN validation."""

    type: Literal["mod97"] = "mod97"


class WeightedModuloChecksum(ImmutableIRModel):
    """Configurable weighted-modulo – VIN check digit, Verhoeff-style."""

    type: Literal["weighted_modulo"] = "weighted_modulo"
    weights: tuple[int, ...]
    modulo: int


ChecksumStrategyType = Annotated[
    Union[LuhnChecksum, Mod97Checksum, WeightedModuloChecksum],
    Field(discriminator="type"),
]


# ---------------------------------------------------------------------------
# Segment primitives
# ---------------------------------------------------------------------------


class SegmentDependency(ImmutableIRModel):
    """Directed dependency from this segment to another segment.

    *purpose* describes *why* the dependency exists:
    - ``checksum_input``    – this segment provides input to a checksum algorithm
    - ``range_boundary``    – this segment defines a numeric boundary
    - ``conditional_logic`` – this segment controls whether another is required
    """

    depends_on_segment_id: str
    purpose: Literal["checksum_input", "range_boundary", "conditional_logic"]


class Segment(ImmutableIRModel):
    """A single positional slice within a structured identifier.

    *constraints* are ordered; generators apply them left-to-right.
    *dependencies* capture inter-segment relationships.
    *checksum_strategy* is present only on checksum/parity segments.
    """

    segment_id: str
    constraints: tuple[AtomicConstraintType, ...] = ()
    dependencies: tuple[SegmentDependency, ...] = ()
    checksum_strategy: Optional[ChecksumStrategyType] = None


class SegmentModel(ImmutableIRModel):
    """Ordered collection of segments that compose a complete field value.

    *separator* is the literal string placed between adjacent segments when
    rendering/parsing (e.g. ``"-"`` for SSN, ``" "`` for Aadhaar).  ``None``
    means segments are concatenated directly.
    """

    segments: tuple[Segment, ...]
    separator: Optional[str] = None

    # ------------------------------------------------------------------
    # Derived properties (computed, not stored – safe on frozen model)
    # ------------------------------------------------------------------

    def total_min_length(self) -> int:
        """Sum of each segment's minimum length, plus separators."""
        total = sum(
            c.min_length
            for seg in self.segments
            for c in seg.constraints
            if c.type == "length"
        )
        sep_count = max(len(self.segments) - 1, 0)
        sep_contribution = (len(self.separator) * sep_count) if self.separator else 0
        return total + sep_contribution

    def total_max_length(self) -> int:
        """Sum of each segment's maximum length, plus separators."""
        total = sum(
            c.max_length
            for seg in self.segments
            for c in seg.constraints
            if c.type == "length"
        )
        sep_count = max(len(self.segments) - 1, 0)
        sep_contribution = (len(self.separator) * sep_count) if self.separator else 0
        return total + sep_contribution

    def segment_count(self) -> int:
        """Number of segments."""
        return len(self.segments)
