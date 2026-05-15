# 1. Recommended Python Package Structure

```text
veriform/constraint_ir/
├── __init__.py
├── contracts.py           # Protocol definitions (cardinality, generation, plugins)
├── enums.py               # Enums (Charsets, LogicalOperators)
├── models/
│   ├── __init__.py
│   ├── atomic.py          # LengthConstraint, CharsetConstraint, etc.
│   ├── checksums.py       # LuhnChecksum, Mod97Checksum, etc.
│   ├── graph.py           # Dependency models and cross-segment definitions
│   ├── segments.py        # Segment and SegmentModel
│   └── profile.py         # ConstraintProfile (Root schema)
├── regex/
│   └── structures.py      # Regex decompilation output structures
└── serialization/
    └── registry.py        # Pydantic discriminators and JSON codec aliases
```

# 2. Model Ownership Boundaries

- **Classification Layer:** Owns the _creation_ and _compilation_ of `ConstraintProfile` objects based on raw form data, semantics, and regexes.
- **IR Layer (This Design):** Owns the _schema definition_, _validation invariants_, _type relationships_, and _serialization contracts_. It is purely a data representation layer.
- **Execution/Generation Layer:** Owns the _interpretation_ of the IR. It implements the algorithms that satisfy the `DeterministicGenerator` protocols and resolves the dependency graphs.

# 3. Compilation Pipeline Stages

1.  **Semantic Inference / Regex Parsing:** Raw data is analyzed.
2.  **Decompilation:** Regex is converted to abstract segment structures.
3.  **IR Instantiation:** Pydantic models (`ConstraintProfile`) are initialized. Validation invariants run instantly.
4.  **Graph Verification:** The DAG (Directed Acyclic Graph) of segment dependencies is validated for cycles.
5.  **State Space Calculation:** The `.cardinality()` protocol is invoked. If the combinatorial space exceeds bounds, a `StateSpaceExplosionError` is raised.
6.  **Serialization:** The bounded IR is serialized to JSON for the Generation Layer.

# 4. Immutable Model Strategy

To guarantee deterministic execution and safe cross-process boundaries, all models enforce strict immutability using Pydantic v2's `ConfigDict`:

```python
from pydantic import BaseModel, ConfigDict

class ImmutableIRModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,               # Prevents attribute mutation post-initialization
        strict=True,               # Disallows type coercion (e.g., int to str)
        extra="forbid",            # Rejects unknown fields
        validate_default=True      # Ensures defaults pass validation
    )
```

# 5. API Contracts & Interfaces

### Cardinality and Deterministic Generation (Protocols)

```python
from typing import Protocol, Dict, Optional

class CardinalityContract(Protocol):
    def cardinality(self) -> int:
        """Returns the exact number of valid combinatorial states."""
        ...

class GenerationContract(Protocol):
    def generate(self, index: int, context: Optional[Dict[str, str]] = None) -> str:
        """
        Deterministically yields the valid value at the given state index.
        `context` provides upstream segment values for dependent generation (e.g., checksums).
        """
        ...

class AbstractValidator(CardinalityContract, GenerationContract, Protocol):
    """Plugins and generators must satisfy this abstract interface."""
    ...
```

# 6. Class Hierarchy & Field Definitions (Pydantic v2)

### Enums

```python
from enum import Enum

class CharsetCategory(str, Enum):
    NUMERIC = "numeric"
    ALPHA_UPPER = "alpha_upper"
    ALPHA_LOWER = "alpha_lower"
    ALPHANUMERIC = "alphanumeric"
    HEX_UPPER = "hex_upper"
```

### Extensibility Interfaces (Checksums)

```python
from typing import Annotated, Literal, Union
from pydantic import Field

class BaseChecksum(ImmutableIRModel):
    type: str

class LuhnChecksum(BaseChecksum):
    type: Literal["luhn"] = "luhn"

class Mod97Checksum(BaseChecksum):
    type: Literal["mod97"] = "mod97"

class VerhoeffChecksum(BaseChecksum):
    type: Literal["verhoeff"] = "verhoeff"

class WeightedModuloChecksum(BaseChecksum):
    type: Literal["weighted_modulo"] = "weighted_modulo"
    weights: list[int]
    modulo: int

ChecksumStrategyType = Annotated[
    Union[LuhnChecksum, Mod97Checksum, VerhoeffChecksum, WeightedModuloChecksum],
    Field(discriminator="type")
]
```

### Atomic Constraints & Discriminated Union

```python
class BaseConstraint(ImmutableIRModel):
    type: str

class LengthConstraint(BaseConstraint):
    type: Literal["length"] = "length"
    min_length: int
    max_length: int

class CharsetConstraint(BaseConstraint):
    type: Literal["charset"] = "charset"
    category: CharsetCategory

class LiteralConstraint(BaseConstraint):
    type: Literal["literal"] = "literal"
    exact_value: str

class RangeConstraint(BaseConstraint):
    type: Literal["range"] = "range"
    min_value: int
    max_value: int

AtomicConstraintType = Annotated[
    Union[LengthConstraint, CharsetConstraint, LiteralConstraint, RangeConstraint],
    Field(discriminator="type")
]
```

### Graph & Dependency Modeling

```python
class SegmentDependency(ImmutableIRModel):
    depends_on_segment_id: str
    purpose: Literal["checksum_input", "range_boundary", "conditional_logic"]
```

### Segments and Root Profile

```python
class Segment(ImmutableIRModel):
    segment_id: str
    constraints: list[AtomicConstraintType]
    dependencies: list[SegmentDependency] = Field(default_factory=list)
    checksum_strategy: Optional[ChecksumStrategyType] = None

class SegmentModel(ImmutableIRModel):
    segments: list[Segment]
    separator: Optional[str] = None

class ConstraintProfile(ImmutableIRModel):
    profile_id: str
    field_name: str
    segment_model: SegmentModel
```

# 7. Validation Invariants

Implemented via Pydantic `@model_validator` to catch mathematical impossibilities at instantiation.

```python
from pydantic import model_validator

# Example attached to LengthConstraint
@model_validator(mode='after')
def validate_length_bounds(self) -> 'LengthConstraint':
    if self.min_length > self.max_length:
        raise ValueError(f"min_length ({self.min_length}) cannot be > max_length ({self.max_length})")
    if self.max_length > 1000:
        raise ValueError("max_length exceeds deterministic execution safety threshold")
    return self

# Example attached to SegmentModel
@model_validator(mode='after')
def validate_dependency_graph(self) -> 'SegmentModel':
    segment_ids = {seg.segment_id for seg in self.segments}
    for seg in self.segments:
        for dep in seg.dependencies:
            if dep.depends_on_segment_id not in segment_ids:
                raise ValueError(f"Dangling dependency: {dep.depends_on_segment_id}")
            if dep.depends_on_segment_id == seg.segment_id:
                raise ValueError(f"Cyclic dependency on self in segment: {seg.segment_id}")
    return self
```

# 8. Examples & JSON Payloads

### Example 1: PAN IR Object (Primary Account Number)

A standard Credit Card features a BIN, an Account Number, and a Luhn checksum digit dependent on the prior segments.

```json
{
  "profile_id": "prf_pan_001",
  "field_name": "credit_card_number",
  "segment_model": {
    "separator": null,
    "segments": [
      {
        "segment_id": "bin",
        "constraints": [
          { "type": "charset", "category": "numeric" },
          { "type": "length", "min_length": 6, "max_length": 6 }
        ],
        "dependencies": [],
        "checksum_strategy": null
      },
      {
        "segment_id": "account_id",
        "constraints": [
          { "type": "charset", "category": "numeric" },
          { "type": "length", "min_length": 9, "max_length": 9 }
        ],
        "dependencies": [],
        "checksum_strategy": null
      },
      {
        "segment_id": "checksum_digit",
        "constraints": [{ "type": "length", "min_length": 1, "max_length": 1 }],
        "dependencies": [
          { "depends_on_segment_id": "bin", "purpose": "checksum_input" },
          { "depends_on_segment_id": "account_id", "purpose": "checksum_input" }
        ],
        "checksum_strategy": { "type": "luhn" }
      }
    ]
  }
}
```

### Example 2: IBAN IR Object (International Bank Account Number)

Features a Country Code, Mod97 Checksum (dependent on BBAN), and the Basic Bank Account Number (BBAN).

```json
{
  "profile_id": "prf_iban_001",
  "field_name": "iban",
  "segment_model": {
    "separator": null,
    "segments": [
      {
        "segment_id": "country_code",
        "constraints": [{ "type": "literal", "exact_value": "DE" }],
        "dependencies": [],
        "checksum_strategy": null
      },
      {
        "segment_id": "checksum",
        "constraints": [
          { "type": "charset", "category": "numeric" },
          { "type": "length", "min_length": 2, "max_length": 2 }
        ],
        "dependencies": [
          {
            "depends_on_segment_id": "country_code",
            "purpose": "checksum_input"
          },
          { "depends_on_segment_id": "bban", "purpose": "checksum_input" }
        ],
        "checksum_strategy": { "type": "mod97" }
      },
      {
        "segment_id": "bban",
        "constraints": [
          { "type": "charset", "category": "numeric" },
          { "type": "length", "min_length": 18, "max_length": 18 }
        ],
        "dependencies": [],
        "checksum_strategy": null
      }
    ]
  }
}
```

### Example 3: VIN IR Object (Vehicle Identification Number)

Requires specific characters, excludes I, O, Q, and has a weighted modulo 11 checksum.

```json
{
  "profile_id": "prf_vin_001",
  "field_name": "vehicle_id",
  "segment_model": {
    "separator": null,
    "segments": [
      {
        "segment_id": "wmi",
        "constraints": [
          { "type": "charset", "category": "alphanumeric" },
          { "type": "length", "min_length": 3, "max_length": 3 }
        ],
        "dependencies": [],
        "checksum_strategy": null
      },
      {
        "segment_id": "vds",
        "constraints": [
          { "type": "charset", "category": "alphanumeric" },
          { "type": "length", "min_length": 5, "max_length": 5 }
        ],
        "dependencies": [],
        "checksum_strategy": null
      },
      {
        "segment_id": "check_digit",
        "constraints": [
          { "type": "charset", "category": "alphanumeric" },
          { "type": "length", "min_length": 1, "max_length": 1 }
        ],
        "dependencies": [
          { "depends_on_segment_id": "wmi", "purpose": "checksum_input" },
          { "depends_on_segment_id": "vds", "purpose": "checksum_input" },
          { "depends_on_segment_id": "vis", "purpose": "checksum_input" }
        ],
        "checksum_strategy": {
          "type": "weighted_modulo",
          "weights": [8, 7, 6, 5, 4, 3, 2, 10, 0, 9, 8, 7, 6, 5, 4, 3, 2],
          "modulo": 11
        }
      },
      {
        "segment_id": "vis",
        "constraints": [
          { "type": "charset", "category": "alphanumeric" },
          { "type": "length", "min_length": 8, "max_length": 8 }
        ],
        "dependencies": [],
        "checksum_strategy": null
      }
    ]
  }
}
```

# 9. Regex Decomposition Output Structures

When the Regex Decompiler parses an expression like `\d{3}-\d{2}-\d{4}` (SSN), it produces the following pure IR schema. Note the translation of the `-` into the `separator` field and `\d` into `charset/numeric`.

```json
{
  "profile_id": "prf_decompiled_ssn",
  "field_name": "social_security",
  "segment_model": {
    "separator": "-",
    "segments": [
      {
        "segment_id": "seg_0",
        "constraints": [
          { "type": "charset", "category": "numeric" },
          { "type": "length", "min_length": 3, "max_length": 3 }
        ]
      },
      {
        "segment_id": "seg_1",
        "constraints": [
          { "type": "charset", "category": "numeric" },
          { "type": "length", "min_length": 2, "max_length": 2 }
        ]
      },
      {
        "segment_id": "seg_2",
        "constraints": [
          { "type": "charset", "category": "numeric" },
          { "type": "length", "min_length": 4, "max_length": 4 }
        ]
      }
    ]
  }
}
```
