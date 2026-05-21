from __future__ import annotations

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field

class MutationCategory(str, Enum):
    BOUNDARY_UNDERFLOW = "boundary_underflow"
    BOUNDARY_EXACT = "boundary_exact"
    BOUNDARY_OVERFLOW = "boundary_overflow"
    CHARSET_DIGITS = "charset_digits"
    CHARSET_ALPHA = "charset_alpha"
    CHARSET_ALPHANUMERIC = "charset_alphanumeric"
    CHARSET_SPECIAL = "charset_special"
    UNICODE_PROBE = "unicode_probe"
    WHITESPACE_PROBE = "whitespace_probe"
    HOMOGLYPH_PROBE = "homoglyph_probe"
    NULL_LIKE_PROBE = "null_like_probe"
    PREFIX_PROBE = "prefix_probe"
    SUFFIX_PROBE = "suffix_probe"
    STRUCTURE_PROBE = "structure_probe"

class MutationProfile(str, Enum):
    LIGHTWEIGHT = "lightweight"
    BALANCED = "balanced"
    EXHAUSTIVE = "exhaustive"

class MutationProbe(BaseModel):
    """A deterministically generated payload for behavioral probing."""
    mutation_id: str = Field(..., description="Unique ID for this mutation instance")
    field_id: str = Field(..., description="Target field ID")
    category: MutationCategory = Field(..., description="Taxonomy classification")
    purpose: str = Field(..., description="Documented inference purpose")
    value: Any = Field(..., description="The payload to inject")

class ProbeResult(BaseModel):
    """The observed outcome of executing a MutationProbe in the browser."""
    mutation_id: str = Field(..., description="Reference to MutationProbe")
    field_id: str = Field(..., description="Target field ID")
    probe_value: Any = Field(..., description="The payload that was executed")
    accepted: bool = Field(..., description="Whether the payload passed client-side validation")
    observed_errors: List[str] = Field(default_factory=list, description="Raw error texts captured from the DOM")
    submit_enabled: bool = Field(..., description="State of the submit button after input")
