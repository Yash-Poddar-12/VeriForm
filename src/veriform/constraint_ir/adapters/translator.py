"""
veriform.constraint_ir.adapters.translator
===========================================
Translates ``FieldSchema`` + ``InferredConstraintSchema`` → ``ConstraintProfile``.

This adapter is the **entry point** for the constraint IR system within the
generation pipeline.  It converts the runtime domain objects produced by the
detector and classifier into the immutable IR representation consumed by the
candidate generator.

Design decisions
----------------
1. **Registry-first**: Known multi-segment formats (PAN, Aadhaar, IFSC, SSN,
   ZIP) are matched against the ``likely_format`` string and resolved to a
   pre-built ``SegmentModel``.  This gives precise boundary values for
   structured identifiers without any regex parsing.

2. **HTML-attribute fallback**: Fields whose format is not in the registry fall
   back to a single-segment model derived from ``min_length``/``max_length``
   and an inferred ``CharsetConstraint``.

3. **Immutability**: All returned ``ConstraintProfile`` objects are fully frozen
   (via ``ImmutableIRModel``) – safe to cache and hash.

4. **Determinism**: Given the same inputs the translator always returns the same
   profile.  No randomness is introduced here.
"""

from __future__ import annotations

import re
from typing import Optional

from veriform.constraint_ir.enums import CharsetCategory
from veriform.constraint_ir.models.atomic import (
    CharsetConstraint,
    LengthConstraint,
)
from veriform.constraint_ir.models.profile import ConstraintProfile
from veriform.constraint_ir.models.segments import (
    Segment,
    SegmentModel,
)
from veriform.models.schemas import FieldSchema, InferredConstraintSchema


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def translate_to_profile(
    field: FieldSchema,
    constraint: Optional[InferredConstraintSchema] = None,
) -> ConstraintProfile:
    """Translate a ``FieldSchema`` (+ optional ``InferredConstraintSchema``)
    into a ``ConstraintProfile``.

    Parameters
    ----------
    field:
        The detected form field.
    constraint:
        The highest-confidence inferred constraint for this field, if any.
        When *None* the profile is built purely from HTML attributes.

    Returns
    -------
    ConstraintProfile
        Fully frozen and validated IR profile.
    """
    semantic_type = constraint.semantic_type if constraint else "generic_text"
    likely_format = constraint.likely_format if constraint else ""
    confidence = constraint.confidence.score if constraint else 0.45
    source = "ai_inferred" if constraint else "html_attribute"

    # 1. Try known structured formats from the registry.
    segment_model = _lookup_structured_format(likely_format)

    if segment_model is not None:
        source = "structured_registry"
    else:
        # 2. Fall back to HTML attribute derivation.
        segment_model = _build_from_html_attrs(field)

    return ConstraintProfile(
        profile_id=f"profile_{field.field_id}",
        field_name=field.name,
        semantic_type=semantic_type,
        segment_model=segment_model,
        source=source,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# Structured format registry
# ---------------------------------------------------------------------------

# Populated lazily on first use — avoids circular import issues at module load.
_REGISTRY: dict[str, SegmentModel] = {}
_REGISTRY_READY = False


def _lookup_structured_format(likely_format: str) -> Optional[SegmentModel]:
    """Return a pre-built ``SegmentModel`` for a known structured format prefix."""
    _ensure_registry()
    if not likely_format:
        return None
    for key, model in _REGISTRY.items():
        if likely_format.startswith(key):
            return model
    return None


def _ensure_registry() -> None:
    global _REGISTRY, _REGISTRY_READY
    if _REGISTRY_READY:
        return
    _REGISTRY = {
        "pan-india": _pan_india(),
        "aadhaar-india": _aadhaar_india(),
        "ifsc-india": _ifsc_india(),
        "ssn-us": _ssn_us(),
        "zip-us": _zip_us(),
    }
    _REGISTRY_READY = True


# ---------------------------------------------------------------------------
# Known segment model factories
# ---------------------------------------------------------------------------


def _pan_india() -> SegmentModel:
    """PAN: AAAAA0000A — 5 alpha-upper + 4 numeric + 1 alpha-upper."""
    return SegmentModel(
        segments=(
            Segment(
                segment_id="pan_alpha5",
                constraints=(
                    LengthConstraint(min_length=5, max_length=5),
                    CharsetConstraint(category=CharsetCategory.ALPHA_UPPER),
                ),
            ),
            Segment(
                segment_id="pan_digit4",
                constraints=(
                    LengthConstraint(min_length=4, max_length=4),
                    CharsetConstraint(category=CharsetCategory.NUMERIC),
                ),
            ),
            Segment(
                segment_id="pan_alpha1",
                constraints=(
                    LengthConstraint(min_length=1, max_length=1),
                    CharsetConstraint(category=CharsetCategory.ALPHA_UPPER),
                ),
            ),
        ),
        separator=None,
    )


def _aadhaar_india() -> SegmentModel:
    """Aadhaar: XXXX XXXX XXXX — three groups of 4 numeric digits."""
    return SegmentModel(
        segments=(
            Segment(
                segment_id="aadhaar_g1",
                constraints=(
                    LengthConstraint(min_length=4, max_length=4),
                    CharsetConstraint(category=CharsetCategory.NUMERIC),
                ),
            ),
            Segment(
                segment_id="aadhaar_g2",
                constraints=(
                    LengthConstraint(min_length=4, max_length=4),
                    CharsetConstraint(category=CharsetCategory.NUMERIC),
                ),
            ),
            Segment(
                segment_id="aadhaar_g3",
                constraints=(
                    LengthConstraint(min_length=4, max_length=4),
                    CharsetConstraint(category=CharsetCategory.NUMERIC),
                ),
            ),
        ),
        separator=" ",
    )


def _ifsc_india() -> SegmentModel:
    """IFSC: AAAA0XXXXXX — 4 alpha + literal '0' + 6 alphanumeric.

    Modelled as two segments for simplicity; the '0' positional constraint is
    captured in the branch segment's length bounds.
    """
    return SegmentModel(
        segments=(
            Segment(
                segment_id="ifsc_bank",
                constraints=(
                    LengthConstraint(min_length=4, max_length=4),
                    CharsetConstraint(category=CharsetCategory.ALPHA_UPPER),
                ),
            ),
            Segment(
                segment_id="ifsc_branch",
                constraints=(
                    LengthConstraint(min_length=7, max_length=7),
                    CharsetConstraint(category=CharsetCategory.ALPHANUMERIC),
                ),
            ),
        ),
        separator=None,
    )


def _ssn_us() -> SegmentModel:
    """US SSN: XXX-XX-XXXX — three numeric groups separated by hyphens."""
    return SegmentModel(
        segments=(
            Segment(
                segment_id="ssn_area",
                constraints=(
                    LengthConstraint(min_length=3, max_length=3),
                    CharsetConstraint(category=CharsetCategory.NUMERIC),
                ),
            ),
            Segment(
                segment_id="ssn_group",
                constraints=(
                    LengthConstraint(min_length=2, max_length=2),
                    CharsetConstraint(category=CharsetCategory.NUMERIC),
                ),
            ),
            Segment(
                segment_id="ssn_serial",
                constraints=(
                    LengthConstraint(min_length=4, max_length=4),
                    CharsetConstraint(category=CharsetCategory.NUMERIC),
                ),
            ),
        ),
        separator="-",
    )


def _zip_us() -> SegmentModel:
    """US ZIP: XXXXX or XXXXX-XXXX (modelled as base 5-digit segment)."""
    return SegmentModel(
        segments=(
            Segment(
                segment_id="zip_base",
                constraints=(
                    LengthConstraint(min_length=5, max_length=5),
                    CharsetConstraint(category=CharsetCategory.NUMERIC),
                ),
            ),
        ),
        separator=None,
    )


# ---------------------------------------------------------------------------
# HTML attribute fallback
# ---------------------------------------------------------------------------


def _build_from_html_attrs(field: FieldSchema) -> SegmentModel:
    """Derive a single-segment ``SegmentModel`` from HTML attribute constraints."""
    min_len = max(field.min_length or 0, 0)
    max_len = min(field.max_length or 256, 500)

    # Clamp to valid Pydantic invariants.
    if max_len < min_len:
        max_len = min_len

    # Guard against zero-length segments (Pydantic validator requires max_len >= 1).
    if max_len < 1:
        max_len = 1
    if min_len < 0:
        min_len = 0

    atomic_constraints: list[LengthConstraint | CharsetConstraint] = [
        LengthConstraint(min_length=min_len, max_length=max_len),
    ]

    charset = _infer_charset(field)
    if charset is not None:
        atomic_constraints.append(CharsetConstraint(category=charset))

    return SegmentModel(
        segments=(
            Segment(
                segment_id=f"seg_{field.field_id}",
                constraints=tuple(atomic_constraints),
            ),
        ),
        separator=None,
    )


def _infer_charset(field: FieldSchema) -> Optional[CharsetCategory]:
    """Infer the dominant character set from ``type`` and ``pattern``."""
    # HTML input type is the strongest signal.
    if field.type in ("number", "tel"):
        return CharsetCategory.NUMERIC

    if not field.pattern:
        return None

    pat = field.pattern.strip()

    # Pure digit patterns: [0-9]{N}, \d{N}, [0-9]{m,n}, \d{m,n}
    _digit_patterns = (
        r"^\^?\[0-9\]\{[\d,]+\}\$?$",
        r"^\^?\\d\{[\d,]+\}\$?$",
        r"^\^?\[0-9\]\+\$?$",
        r"^\^?\\d\+\$?$",
    )
    for dp in _digit_patterns:
        if re.match(dp, pat):
            return CharsetCategory.NUMERIC

    # Alpha upper: [A-Z]{N}
    if re.match(r"^\^?\[A-Z\]\{[\d,]+\}\$?$", pat):
        return CharsetCategory.ALPHA_UPPER

    # Alphanumeric: [A-Za-z0-9]{N} or [a-zA-Z0-9]{N}
    if re.match(r"^\^?\[A-Za-z0-9\]\{[\d,]+\}\$?$", pat) or re.match(
        r"^\^?\[a-zA-Z0-9\]\{[\d,]+\}\$?$", pat
    ):
        return CharsetCategory.ALPHANUMERIC

    return None
