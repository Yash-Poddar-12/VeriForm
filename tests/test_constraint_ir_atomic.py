import pytest
from pydantic import TypeAdapter, ValidationError

from veriform.constraint_ir.enums import CharsetCategory
from veriform.constraint_ir.models.atomic import (
    AtomicConstraintType,
    CharsetConstraint,
    LengthConstraint,
)


def test_length_constraint_valid():
    constraint = LengthConstraint(min_length=5, max_length=10)

    assert constraint.min_length == 5
    assert constraint.max_length == 10
    assert constraint.type == "length"


def test_length_constraint_min_less_than_zero():
    with pytest.raises(ValidationError, match="min_length must be >= 0"):
        LengthConstraint(min_length=-1, max_length=10)


def test_length_constraint_max_less_than_min():
    with pytest.raises(
        ValidationError,
        match="max_length must be >= min_length",
    ):
        LengthConstraint(min_length=10, max_length=5)


def test_length_constraint_max_exceeds_bounds():
    with pytest.raises(
        ValidationError,
        match="max_length exceeds deterministic safety bound of 500",
    ):
        LengthConstraint(min_length=1, max_length=501)


def test_charset_constraint_valid():
    constraint = CharsetConstraint(
        category=CharsetCategory.NUMERIC
    )

    assert constraint.category == CharsetCategory.NUMERIC
    assert constraint.type == "charset"


def test_discriminated_union_resolution():
    adapter = TypeAdapter(AtomicConstraintType)

    length_json = (
        '{"type":"length","min_length":1,"max_length":5}'
    )

    length_obj = adapter.validate_json(length_json)

    assert isinstance(length_obj, LengthConstraint)
    assert length_obj.min_length == 1
    assert length_obj.max_length == 5

    charset_json = (
        '{"type":"charset","category":"numeric"}'
    )

    charset_obj = adapter.validate_json(charset_json)

    assert isinstance(charset_obj, CharsetConstraint)
    assert charset_obj.category == CharsetCategory.NUMERIC