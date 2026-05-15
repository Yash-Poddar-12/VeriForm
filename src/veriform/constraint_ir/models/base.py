from pydantic import BaseModel, ConfigDict


class ImmutableIRModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        strict=True,
        extra="forbid",
    )