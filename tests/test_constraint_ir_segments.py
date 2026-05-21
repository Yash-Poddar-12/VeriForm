"""Tests for constraint_ir.models.segments – Segment, SegmentModel, checksum types."""

from __future__ import annotations

import pytest
from pydantic import TypeAdapter, ValidationError

from veriform.constraint_ir.enums import CharsetCategory
from veriform.constraint_ir.models.atomic import CharsetConstraint, LengthConstraint
from veriform.constraint_ir.models.segments import (
    ChecksumStrategyType,
    LuhnChecksum,
    Mod97Checksum,
    Segment,
    SegmentDependency,
    SegmentModel,
    WeightedModuloChecksum,
)


# ---------------------------------------------------------------------------
# Checksum strategy tests
# ---------------------------------------------------------------------------


class TestChecksumStrategies:
    def test_luhn_type_literal(self) -> None:
        cs = LuhnChecksum()
        assert cs.type == "luhn"

    def test_mod97_type_literal(self) -> None:
        cs = Mod97Checksum()
        assert cs.type == "mod97"

    def test_weighted_modulo_fields(self) -> None:
        cs = WeightedModuloChecksum(weights=(2, 1, 2, 1), modulo=10)
        assert cs.weights == (2, 1, 2, 1)
        assert cs.modulo == 10
        assert cs.type == "weighted_modulo"

    def test_weighted_modulo_is_frozen(self) -> None:
        cs = WeightedModuloChecksum(weights=(3,), modulo=7)
        with pytest.raises(ValidationError):
            cs.modulo = 11  # type: ignore[misc]

    def test_discriminated_union_luhn(self) -> None:
        adapter: TypeAdapter[ChecksumStrategyType] = TypeAdapter(ChecksumStrategyType)
        obj = adapter.validate_python({"type": "luhn"})
        assert isinstance(obj, LuhnChecksum)

    def test_discriminated_union_mod97(self) -> None:
        adapter: TypeAdapter[ChecksumStrategyType] = TypeAdapter(ChecksumStrategyType)
        obj = adapter.validate_python({"type": "mod97"})
        assert isinstance(obj, Mod97Checksum)

    def test_discriminated_union_weighted_modulo(self) -> None:
        # ImmutableIRModel has strict=True so list is not coerced to tuple;
        # build from a real WeightedModuloChecksum instance instead.
        original = WeightedModuloChecksum(weights=(2, 3), modulo=11)
        adapter: TypeAdapter[ChecksumStrategyType] = TypeAdapter(ChecksumStrategyType)
        obj = adapter.validate_python(original)
        assert isinstance(obj, WeightedModuloChecksum)
        assert obj.modulo == 11
        assert obj.weights == (2, 3)


# ---------------------------------------------------------------------------
# SegmentDependency tests
# ---------------------------------------------------------------------------


class TestSegmentDependency:
    def test_valid_dependency(self) -> None:
        dep = SegmentDependency(
            depends_on_segment_id="seg_a",
            purpose="checksum_input",
        )
        assert dep.depends_on_segment_id == "seg_a"
        assert dep.purpose == "checksum_input"

    def test_all_purposes_accepted(self) -> None:
        for purpose in ("checksum_input", "range_boundary", "conditional_logic"):
            dep = SegmentDependency(
                depends_on_segment_id="x", purpose=purpose  # type: ignore[arg-type]
            )
            assert dep.purpose == purpose

    def test_invalid_purpose_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SegmentDependency(depends_on_segment_id="x", purpose="nonexistent")  # type: ignore[arg-type]

    def test_is_frozen(self) -> None:
        dep = SegmentDependency(depends_on_segment_id="x", purpose="checksum_input")
        with pytest.raises(ValidationError):
            dep.depends_on_segment_id = "y"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Segment tests
# ---------------------------------------------------------------------------


class TestSegment:
    def test_empty_segment(self) -> None:
        seg = Segment(segment_id="seg_empty")
        assert seg.segment_id == "seg_empty"
        assert seg.constraints == ()
        assert seg.dependencies == ()
        assert seg.checksum_strategy is None

    def test_segment_with_length_and_charset(self) -> None:
        seg = Segment(
            segment_id="seg_pan_alpha5",
            constraints=(
                LengthConstraint(min_length=5, max_length=5),
                CharsetConstraint(category=CharsetCategory.ALPHA_UPPER),
            ),
        )
        assert len(seg.constraints) == 2
        assert seg.constraints[0].type == "length"
        assert seg.constraints[1].type == "charset"

    def test_segment_with_checksum(self) -> None:
        seg = Segment(
            segment_id="seg_luhn",
            constraints=(LengthConstraint(min_length=1, max_length=1),),
            checksum_strategy=LuhnChecksum(),
        )
        assert isinstance(seg.checksum_strategy, LuhnChecksum)

    def test_segment_with_dependency(self) -> None:
        seg = Segment(
            segment_id="seg_b",
            dependencies=(
                SegmentDependency(
                    depends_on_segment_id="seg_a",
                    purpose="checksum_input",
                ),
            ),
        )
        assert len(seg.dependencies) == 1
        assert seg.dependencies[0].depends_on_segment_id == "seg_a"

    def test_segment_is_frozen(self) -> None:
        seg = Segment(segment_id="s")
        with pytest.raises(ValidationError):
            seg.segment_id = "t"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SegmentModel tests
# ---------------------------------------------------------------------------


class TestSegmentModel:
    def _pan_model(self) -> SegmentModel:
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

    def _aadhaar_model(self) -> SegmentModel:
        return SegmentModel(
            segments=(
                Segment(
                    segment_id="g1",
                    constraints=(LengthConstraint(min_length=4, max_length=4),),
                ),
                Segment(
                    segment_id="g2",
                    constraints=(LengthConstraint(min_length=4, max_length=4),),
                ),
                Segment(
                    segment_id="g3",
                    constraints=(LengthConstraint(min_length=4, max_length=4),),
                ),
            ),
            separator=" ",
        )

    def test_pan_total_min_length(self) -> None:
        model = self._pan_model()
        # 5 + 4 + 1 = 10, no separator
        assert model.total_min_length() == 10

    def test_pan_total_max_length(self) -> None:
        model = self._pan_model()
        assert model.total_max_length() == 10

    def test_aadhaar_total_length_includes_separators(self) -> None:
        model = self._aadhaar_model()
        # segments: 4+4+4 = 12, separators: 2 * " " = 2 → total 14
        assert model.total_min_length() == 14
        assert model.total_max_length() == 14

    def test_segment_count(self) -> None:
        assert self._pan_model().segment_count() == 3
        assert self._aadhaar_model().segment_count() == 3

    def test_single_segment(self) -> None:
        model = SegmentModel(
            segments=(
                Segment(
                    segment_id="s1",
                    constraints=(LengthConstraint(min_length=6, max_length=12),),
                ),
            ),
        )
        assert model.total_min_length() == 6
        assert model.total_max_length() == 12

    def test_empty_segments_length(self) -> None:
        # SegmentModel with segment that has no length constraint contributes 0.
        model = SegmentModel(
            segments=(Segment(segment_id="bare"),),
        )
        assert model.total_min_length() == 0

    def test_is_frozen(self) -> None:
        model = SegmentModel(segments=(Segment(segment_id="x"),))
        with pytest.raises(ValidationError):
            model.separator = "-"  # type: ignore[misc]

    def test_separator_none_vs_string(self) -> None:
        m_none = SegmentModel(segments=(Segment(segment_id="a"),), separator=None)
        m_dash = SegmentModel(segments=(Segment(segment_id="b"),), separator="-")
        assert m_none.separator is None
        assert m_dash.separator == "-"
