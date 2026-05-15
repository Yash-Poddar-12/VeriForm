from typing import Annotated, Literal, Union

from pydantic import Field, model_validator

from veriform.constraint_ir.enums import CharsetCategory
from veriform.constraint_ir.models.base import ImmutableIRModel


class BaseConstraint(ImmutableIRModel):
    """Abstract base class for all constraint primitives."""

    type: str


class LengthConstraint(BaseConstraint):
    """Defines deterministic boundaries for string length."""

    type: Literal["length"] = "length"
    min_length: int
    max_length: int

    @model_validator(mode="after")
    def validate_length_bounds(self) -> "LengthConstraint":
        if self.min_length < 0:
            raise ValueError("min_length must be >= 0")

        if self.max_length < self.min_length:
            raise ValueError("max_length must be >= min_length")

        if self.max_length > 500:
            raise ValueError(
                "max_length exceeds deterministic safety bound of 500"
            )

        return self


class CharsetConstraint(BaseConstraint):
    """Restricts allowed character set."""

    type: Literal["charset"] = "charset"
    category: CharsetCategory


AtomicConstraintType = Annotated[
    Union[LengthConstraint, CharsetConstraint],
    Field(discriminator="type"),
]