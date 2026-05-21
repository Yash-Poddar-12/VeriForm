"""
veriform.constraint_ir
=======================
Immutable Intermediate Representation (IR) for field-level constraints.

Public surface
--------------
Enums:
    CharsetCategory

Base model:
    ImmutableIRModel

Atomic constraints (discriminated union):
    LengthConstraint
    CharsetConstraint
    AtomicConstraintType         ← use this as the union type annotation

Segment / profile IR:
    SegmentDependency
    Segment
    SegmentModel
    ChecksumStrategyType         ← checksum discriminated union
    LuhnChecksum
    Mod97Checksum
    WeightedModuloChecksum
    ConstraintProfile            ← root IR for a single field
"""

from veriform.constraint_ir.enums import CharsetCategory
from veriform.constraint_ir.models.atomic import (
    AtomicConstraintType,
    BaseConstraint,
    CharsetConstraint,
    LengthConstraint,
)
from veriform.constraint_ir.models.base import ImmutableIRModel
from veriform.constraint_ir.models.profile import ConstraintProfile
from veriform.constraint_ir.models.segments import (
    ChecksumStrategyType,
    LuhnChecksum,
    Mod97Checksum,
    Segment,
    SegmentDependency,
    SegmentModel,
    WeightedModuloChecksum,
)

__all__ = [
    # enums
    "CharsetCategory",
    # base
    "ImmutableIRModel",
    # atomic
    "AtomicConstraintType",
    "BaseConstraint",
    "CharsetConstraint",
    "LengthConstraint",
    # segments
    "ChecksumStrategyType",
    "LuhnChecksum",
    "Mod97Checksum",
    "Segment",
    "SegmentDependency",
    "SegmentModel",
    "WeightedModuloChecksum",
    # profile
    "ConstraintProfile",
]
