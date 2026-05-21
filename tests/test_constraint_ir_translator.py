"""Tests for constraint_ir.adapters.translator – translate_to_profile."""

from __future__ import annotations

import pytest

from veriform.constraint_ir.adapters.translator import translate_to_profile
from veriform.constraint_ir.enums import CharsetCategory
from veriform.constraint_ir.models.atomic import CharsetConstraint, LengthConstraint
from veriform.constraint_ir.models.profile import ConstraintProfile
from veriform.constraint_ir.models.segments import SegmentModel
from veriform.models.schemas import (
    ConfidenceScoreSchema,
    FieldSchema,
    InferredConstraintSchema,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _field(
    field_id: str = "field_001",
    name: str = "test_field",
    field_type: str = "text",
    min_length: int | None = None,
    max_length: int | None = None,
    pattern: str | None = None,
) -> FieldSchema:
    return FieldSchema(
        field_id=field_id,
        run_id="run-test-001",
        name=name,
        type=field_type,
        min_length=min_length,
        max_length=max_length,
        pattern=pattern,
    )


def _constraint(
    field_id: str = "field_001",
    semantic_type: str = "generic_text",
    likely_format: str = "free-text",
    score: float = 0.75,
) -> InferredConstraintSchema:
    return InferredConstraintSchema(
        constraint_id=f"{field_id}_ic_001",
        run_id="run-test-001",
        field_id=field_id,
        semantic_type=semantic_type,
        likely_format=likely_format,
        confidence=ConfidenceScoreSchema(
            score=score,
            source="deterministic_hint",
        ),
    )


# ---------------------------------------------------------------------------
# Basic translation
# ---------------------------------------------------------------------------


class TestTranslateBasic:
    def test_returns_constraint_profile(self) -> None:
        profile = translate_to_profile(_field())
        assert isinstance(profile, ConstraintProfile)

    def test_profile_id_derived_from_field_id(self) -> None:
        profile = translate_to_profile(_field(field_id="field_007"))
        assert profile.profile_id == "profile_field_007"

    def test_field_name_preserved(self) -> None:
        profile = translate_to_profile(_field(name="mobile_number"))
        assert profile.field_name == "mobile_number"

    def test_no_constraint_gives_html_source(self) -> None:
        profile = translate_to_profile(_field())
        assert profile.source == "html_attribute"

    def test_with_constraint_gives_ai_source(self) -> None:
        profile = translate_to_profile(_field(), _constraint())
        assert profile.source in ("ai_inferred", "structured_registry")

    def test_semantic_type_from_constraint(self) -> None:
        profile = translate_to_profile(_field(), _constraint(semantic_type="email"))
        assert profile.semantic_type == "email"

    def test_confidence_from_constraint(self) -> None:
        profile = translate_to_profile(_field(), _constraint(score=0.88))
        assert profile.confidence == pytest.approx(0.88)

    def test_no_constraint_default_confidence(self) -> None:
        profile = translate_to_profile(_field())
        assert profile.confidence == pytest.approx(0.45)


# ---------------------------------------------------------------------------
# HTML attribute fallback
# ---------------------------------------------------------------------------


class TestHtmlAttributeFallback:
    def test_single_segment_from_min_max(self) -> None:
        profile = translate_to_profile(_field(min_length=5, max_length=20))
        assert profile.is_single_segment()
        seg = profile.segment_model.segments[0]
        lc = next(c for c in seg.constraints if c.type == "length")
        assert isinstance(lc, LengthConstraint)
        assert lc.min_length == 5
        assert lc.max_length == 20

    def test_numeric_type_infers_numeric_charset(self) -> None:
        profile = translate_to_profile(_field(field_type="number"))
        seg = profile.segment_model.segments[0]
        charsets = [c for c in seg.constraints if c.type == "charset"]
        assert len(charsets) == 1
        assert isinstance(charsets[0], CharsetConstraint)
        assert charsets[0].category == CharsetCategory.NUMERIC

    def test_tel_type_infers_numeric_charset(self) -> None:
        profile = translate_to_profile(_field(field_type="tel"))
        seg = profile.segment_model.segments[0]
        charsets = [c for c in seg.constraints if c.type == "charset"]
        assert charsets[0].category == CharsetCategory.NUMERIC

    def test_digit_pattern_infers_numeric_charset(self) -> None:
        profile = translate_to_profile(_field(pattern="[0-9]{10}"))
        seg = profile.segment_model.segments[0]
        charsets = [c for c in seg.constraints if c.type == "charset"]
        assert charsets[0].category == CharsetCategory.NUMERIC

    def test_alpha_upper_pattern_infers_charset(self) -> None:
        profile = translate_to_profile(_field(pattern="[A-Z]{4}"))
        seg = profile.segment_model.segments[0]
        charsets = [c for c in seg.constraints if c.type == "charset"]
        assert charsets[0].category == CharsetCategory.ALPHA_UPPER

    def test_alphanumeric_pattern_infers_charset(self) -> None:
        profile = translate_to_profile(_field(pattern="[A-Za-z0-9]{6,20}"))
        seg = profile.segment_model.segments[0]
        charsets = [c for c in seg.constraints if c.type == "charset"]
        assert charsets[0].category == CharsetCategory.ALPHANUMERIC

    def test_max_length_clamped_to_500(self) -> None:
        profile = translate_to_profile(_field(min_length=1, max_length=9999))
        seg = profile.segment_model.segments[0]
        lc = next(c for c in seg.constraints if c.type == "length")
        assert lc.max_length == 500

    def test_no_length_attrs_defaults_to_safe_bounds(self) -> None:
        profile = translate_to_profile(_field())
        # Should not raise; max_length defaults to 256, clamped to 256
        assert profile.total_max_length() == 256


# ---------------------------------------------------------------------------
# Structured format registry
# ---------------------------------------------------------------------------


class TestStructuredRegistry:
    def test_pan_india_resolved(self) -> None:
        c = _constraint(likely_format="pan-india-alpha5-digit4-alpha1")
        profile = translate_to_profile(_field(), c)
        assert profile.source == "structured_registry"
        assert profile.segment_count() == 3
        assert profile.total_min_length() == 10
        assert profile.total_max_length() == 10

    def test_aadhaar_india_resolved(self) -> None:
        c = _constraint(likely_format="aadhaar-india-4-4-4")
        profile = translate_to_profile(_field(), c)
        assert profile.source == "structured_registry"
        # 4+4+4 = 12 digits + 2 spaces = 14
        assert profile.total_min_length() == 14

    def test_ifsc_india_resolved(self) -> None:
        c = _constraint(likely_format="ifsc-india-alpha4-0-alnum6")
        profile = translate_to_profile(_field(), c)
        assert profile.source == "structured_registry"
        assert profile.segment_count() == 2
        # 4 + 7 = 11 chars
        assert profile.total_min_length() == 11

    def test_ssn_us_resolved(self) -> None:
        c = _constraint(likely_format="ssn-us-3-2-4")
        profile = translate_to_profile(_field(), c)
        assert profile.source == "structured_registry"
        # 3+2+4 = 9 digits + 2 hyphens = 11
        assert profile.total_min_length() == 11

    def test_zip_us_resolved(self) -> None:
        c = _constraint(likely_format="zip-us-5-or-9")
        profile = translate_to_profile(_field(), c)
        assert profile.source == "structured_registry"
        assert profile.total_min_length() == 5

    def test_unknown_format_falls_back_to_html(self) -> None:
        c = _constraint(likely_format="totally-unknown-format")
        profile = translate_to_profile(_field(min_length=3, max_length=30), c)
        # Should NOT match registry → should use HTML attr fallback
        assert profile.source == "ai_inferred"  # constraint present but no registry match
        assert profile.total_min_length() == 3

    def test_empty_format_falls_back_to_html(self) -> None:
        c = _constraint(likely_format="")
        profile = translate_to_profile(_field(min_length=5, max_length=10), c)
        assert profile.source == "ai_inferred"
        assert profile.total_max_length() == 10


# ---------------------------------------------------------------------------
# Profile immutability
# ---------------------------------------------------------------------------


class TestProfileImmutability:
    def test_returned_profile_is_frozen(self) -> None:
        from pydantic import ValidationError

        profile = translate_to_profile(_field())
        with pytest.raises(ValidationError):
            profile.field_name = "mutated"  # type: ignore[misc]
