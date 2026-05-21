"""Tests for constraint_ir.models.profile – ConstraintProfile."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from veriform.constraint_ir.enums import CharsetCategory
from veriform.constraint_ir.models.atomic import CharsetConstraint, LengthConstraint
from veriform.constraint_ir.models.profile import ConstraintProfile
from veriform.constraint_ir.models.segments import Segment, SegmentModel


def _simple_model(min_len: int = 5, max_len: int = 10) -> SegmentModel:
    return SegmentModel(
        segments=(
            Segment(
                segment_id="seg_main",
                constraints=(LengthConstraint(min_length=min_len, max_length=max_len),),
            ),
        )
    )


class TestConstraintProfile:
    def test_basic_creation(self) -> None:
        profile = ConstraintProfile(
            profile_id="profile_field_001",
            field_name="mobile_number",
            semantic_type="mobile_number",
            segment_model=_simple_model(10, 10),
        )
        assert profile.profile_id == "profile_field_001"
        assert profile.field_name == "mobile_number"
        assert profile.semantic_type == "mobile_number"
        assert profile.source == "deterministic"  # default
        assert profile.confidence == 1.0  # default

    def test_custom_source_and_confidence(self) -> None:
        profile = ConstraintProfile(
            profile_id="p",
            field_name="pan",
            semantic_type="pan",
            segment_model=_simple_model(),
            source="ai_inferred",
            confidence=0.82,
        )
        assert profile.source == "ai_inferred"
        assert profile.confidence == pytest.approx(0.82)

    def test_all_valid_sources(self) -> None:
        for src in (
            "html_attribute",
            "ai_inferred",
            "structured_registry",
            "deterministic",
            "user_override",
        ):
            p = ConstraintProfile(
                profile_id="p",
                field_name="f",
                semantic_type="t",
                segment_model=_simple_model(),
                source=src,
            )
            assert p.source == src

    def test_invalid_source_raises(self) -> None:
        with pytest.raises(ValidationError, match="source must be one of"):
            ConstraintProfile(
                profile_id="p",
                field_name="f",
                semantic_type="t",
                segment_model=_simple_model(),
                source="unknown_source",
            )

    def test_confidence_out_of_bounds_raises(self) -> None:
        with pytest.raises(ValidationError):
            ConstraintProfile(
                profile_id="p",
                field_name="f",
                semantic_type="t",
                segment_model=_simple_model(),
                confidence=1.5,
            )

    def test_is_frozen(self) -> None:
        profile = ConstraintProfile(
            profile_id="p",
            field_name="f",
            semantic_type="t",
            segment_model=_simple_model(),
        )
        with pytest.raises(ValidationError):
            profile.field_name = "mutated"  # type: ignore[misc]

    def test_total_min_length_delegate(self) -> None:
        profile = ConstraintProfile(
            profile_id="p",
            field_name="f",
            semantic_type="t",
            segment_model=_simple_model(3, 20),
        )
        assert profile.total_min_length() == 3

    def test_total_max_length_delegate(self) -> None:
        profile = ConstraintProfile(
            profile_id="p",
            field_name="f",
            semantic_type="t",
            segment_model=_simple_model(3, 20),
        )
        assert profile.total_max_length() == 20

    def test_is_single_segment(self) -> None:
        profile = ConstraintProfile(
            profile_id="p",
            field_name="f",
            semantic_type="t",
            segment_model=_simple_model(),
        )
        assert profile.is_single_segment() is True

    def test_multi_segment_not_single(self) -> None:
        model = SegmentModel(
            segments=(
                Segment(segment_id="a"),
                Segment(segment_id="b"),
            )
        )
        profile = ConstraintProfile(
            profile_id="p",
            field_name="f",
            semantic_type="t",
            segment_model=model,
        )
        assert profile.is_single_segment() is False
        assert profile.segment_count() == 2

    def test_extra_fields_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ConstraintProfile(  # type: ignore[call-arg]
                profile_id="p",
                field_name="f",
                semantic_type="t",
                segment_model=_simple_model(),
                unexpected_field="oops",
            )
