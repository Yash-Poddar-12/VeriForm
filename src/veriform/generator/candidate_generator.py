"""Semantic-aware candidate input generation for deterministic form exploration."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence, Union

from veriform.models.schemas import CandidateInputSchema, FieldSchema, InferredConstraintSchema

CandidateValue = Union[str, int, float, bool]

SECURITY_PAYLOAD = "' OR '1'='1"
MAX_CANDIDATES_PER_FIELD = 12


@dataclass(frozen=True)
class _CandidateSpec:
    input_value: CandidateValue
    category: str
    expected_outcome: str
    weight: float


def build_candidate_inputs(
    fields: Sequence[FieldSchema],
    merged_constraints: Mapping[str, Sequence[InferredConstraintSchema]],
) -> list[CandidateInputSchema]:
    """Build deterministic candidate inputs from field metadata and constraints."""
    candidates: list[CandidateInputSchema] = []
    for field_index, field in enumerate(fields, start=1):
        constraint = _primary_constraint(merged_constraints.get(field.field_id, ()))
        semantic_type = constraint.semantic_type if constraint else _fallback_semantic_type(field)
        likely_format = constraint.likely_format if constraint else ""
        confidence = constraint.confidence.score if constraint else _fallback_confidence(semantic_type)

        for spec_index, spec in enumerate(
            _bounded_specs(_dedupe_specs(_candidate_specs_for(field, semantic_type, likely_format))),
            start=1,
        ):
            candidates.append(
                CandidateInputSchema(
                    candidate_id=f"{field.field_id}_cand_{field_index:03d}_{spec_index:02d}",
                    run_id=field.run_id,
                    field_id=field.field_id,
                    input_value=spec.input_value,
                    category=spec.category,
                    expected_outcome=spec.expected_outcome,
                    priority_score=_priority_for(field, confidence, spec),
                )
            )

    return candidates


def _primary_constraint(
    constraints: Sequence[InferredConstraintSchema],
) -> InferredConstraintSchema | None:
    if not constraints:
        return None
    return max(constraints, key=lambda item: (item.confidence.score, item.constraint_id))


def _candidate_specs_for(
    field: FieldSchema,
    semantic_type: str,
    likely_format: str,
) -> list[_CandidateSpec]:
    specs = _semantic_specs(semantic_type)
    specs.extend(_regex_specs(field.pattern))
    specs.extend(_length_specs(field))
    specs.extend(_numeric_specs(field))
    specs.extend(_date_specs(field, semantic_type, likely_format))
    specs.extend(_structured_identifier_specs(likely_format))
    specs.extend(_required_specs(field))
    specs.extend(_whitespace_specs())
    specs.extend(_security_specs())

    if not any(spec.category == "valid" for spec in specs):
        specs.insert(0, _CandidateSpec(_generic_valid_value(field), "valid", "accept", 0.82))
    return specs


def _semantic_specs(semantic_type: str) -> list[_CandidateSpec]:
    catalog: dict[str, list[_CandidateSpec]] = {
        "phone": [
            _CandidateSpec("+14155552671", "valid", "accept", 0.96),
            _CandidateSpec("415-555-267", "boundary", "reject", 0.88),
            _CandidateSpec("phone-number", "malformed", "reject", 0.9),
        ],
        "mobile_number": [
            _CandidateSpec("9876543210", "valid", "accept", 0.98),
            _CandidateSpec("12345", "invalid", "reject", 0.84),
            _CandidateSpec("98AB765432", "malformed", "reject", 0.9),
        ],
        "loan_account_number": [
            _CandidateSpec("123456789012", "valid", "accept", 0.96),
            _CandidateSpec("1234567", "boundary", "reject", 0.9),
            _CandidateSpec("12345678901234567", "boundary", "reject", 0.9),
            _CandidateSpec("12A456789012", "malformed", "reject", 0.88),
        ],
        "date_of_birth": [
            _CandidateSpec("1990-01-01", "valid", "accept", 0.95),
            _CandidateSpec("01/01/1990", "valid", "accept", 0.86),
            _CandidateSpec("2099-01-01", "invalid", "reject", 0.86),
            _CandidateSpec("1990-02-30", "malformed", "reject", 0.91),
        ],
        "date": [
            _CandidateSpec("2024-12-31", "valid", "accept", 0.9),
            _CandidateSpec("12/31/2024", "valid", "accept", 0.82),
            _CandidateSpec("31-12-2024", "boundary", "reject", 0.78),
            _CandidateSpec("2024-13-40", "malformed", "reject", 0.9),
        ],
        "application_reference_number": [
            _CandidateSpec("APP123456", "valid", "accept", 0.94),
            _CandidateSpec("APP12", "boundary", "reject", 0.88),
            _CandidateSpec("APP-###", "malformed", "reject", 0.9),
        ],
        "account_number": [
            _CandidateSpec("ACCT12345678", "valid", "accept", 0.92),
            _CandidateSpec("1234", "boundary", "reject", 0.86),
            _CandidateSpec("ACCT-12-##", "malformed", "reject", 0.9),
        ],
        "postal_code": [
            _CandidateSpec("90210", "valid", "accept", 0.9),
            _CandidateSpec("12345-6789", "valid", "accept", 0.84),
            _CandidateSpec("12", "boundary", "reject", 0.86),
            _CandidateSpec("ABCDE", "malformed", "reject", 0.82),
        ],
        "address": [
            _CandidateSpec("221B Baker Street", "valid", "accept", 0.88),
            _CandidateSpec("A", "boundary", "reject", 0.8),
            _CandidateSpec("### !!!", "malformed", "reject", 0.82),
        ],
        "city": [
            _CandidateSpec("San Francisco", "valid", "accept", 0.86),
            _CandidateSpec("X", "boundary", "reject", 0.8),
            _CandidateSpec("1234", "malformed", "reject", 0.82),
        ],
        "state": [
            _CandidateSpec("CA", "valid", "accept", 0.84),
            _CandidateSpec("California", "valid", "accept", 0.82),
            _CandidateSpec("C4", "malformed", "reject", 0.8),
        ],
        "amount": [
            _CandidateSpec(100.5, "valid", "accept", 0.9),
            _CandidateSpec(-1, "boundary", "reject", 0.87),
            _CandidateSpec("1,00.00.00", "malformed", "reject", 0.84),
        ],
        "select_option": [
            _CandidateSpec("option_1", "valid", "accept", 0.8),
            _CandidateSpec("", "empty", "reject", 0.88),
            _CandidateSpec("invalid_option", "invalid", "reject", 0.82),
        ],
        "boolean_choice": [
            _CandidateSpec(True, "valid", "accept", 0.82),
            _CandidateSpec(False, "valid", "accept", 0.82),
            _CandidateSpec("", "empty", "reject", 0.84),
        ],
        "email": [
            _CandidateSpec("user@example.com", "valid", "accept", 0.94),
            _CandidateSpec("userexample.com", "malformed", "reject", 0.9),
            _CandidateSpec("user@example", "invalid", "reject", 0.84),
        ],
        "name": [
            _CandidateSpec("Alice Doe", "valid", "accept", 0.86),
            _CandidateSpec("A1ice", "malformed", "reject", 0.76),
        ],
        "generic_text": [
            _CandidateSpec("sample", "valid", "accept", 0.78),
            _CandidateSpec("<script>alert(1)</script>", "suspicious", "reject", 0.91),
        ],
        "free_text": [
            _CandidateSpec("This is a user-entered comment.", "valid", "accept", 0.82),
            _CandidateSpec("x", "boundary", "reject", 0.76),
            _CandidateSpec("<img src=x onerror=alert(1)>", "suspicious", "reject", 0.9),
        ],
    }
    return list(catalog.get(semantic_type, catalog["generic_text"]))


def _regex_specs(pattern: str | None) -> list[_CandidateSpec]:
    if not pattern:
        return []

    exact_digits = re.fullmatch(r"(?:\[0-9\]|\\d)\{(?P<size>\d+)\}", pattern)
    if exact_digits:
        size = int(exact_digits.group("size"))
        return [
            _CandidateSpec(_digits(size), "valid", "accept", 0.94),
            _CandidateSpec(_digits(max(size - 1, 0)), "boundary", "reject", 0.9),
            _CandidateSpec(_digits(size + 1), "boundary", "reject", 0.9),
            _CandidateSpec(f"{_digits(max(size - 1, 1))}A", "malformed", "reject", 0.88),
        ]

    digit_range = re.fullmatch(
        r"(?:\[0-9\]|\\d)\{(?P<min_size>\d+),(?P<max_size>\d+)\}",
        pattern,
    )
    if digit_range:
        min_size = int(digit_range.group("min_size"))
        max_size = int(digit_range.group("max_size"))
        specs = _range_length_specs(min_size, max_size, digits_only=True)
        specs.append(_CandidateSpec("12AB", "malformed", "reject", 0.88))
        return specs

    alnum_range = re.fullmatch(
        r"\[A-Za-z0-9\]\{(?P<min_size>\d+),(?P<max_size>\d+)\}",
        pattern,
    )
    if alnum_range:
        min_size = int(alnum_range.group("min_size"))
        max_size = int(alnum_range.group("max_size"))
        specs = _range_length_specs(min_size, max_size, digits_only=False)
        specs.append(_CandidateSpec("###$$$", "malformed", "reject", 0.88))
        return specs

    return [_CandidateSpec("not-matching-pattern", "malformed", "reject", 0.76)]


def _length_specs(field: FieldSchema) -> list[_CandidateSpec]:
    if field.min_length is not None and field.max_length is not None:
        return _range_length_specs(field.min_length, field.max_length, digits_only=False)
    if field.max_length is not None:
        max_size = field.max_length
        return [
            _CandidateSpec(_letters(max(max_size - 1, 0)), "boundary", "accept", 0.82),
            _CandidateSpec(_letters(max_size), "boundary", "accept", 0.86),
            _CandidateSpec(_letters(max_size + 1), "boundary", "reject", 0.9),
        ]
    if field.min_length is not None:
        min_size = field.min_length
        return [
            _CandidateSpec(_letters(max(min_size - 1, 0)), "boundary", "reject", 0.88),
            _CandidateSpec(_letters(min_size), "boundary", "accept", 0.84),
        ]
    return []


def _numeric_specs(field: FieldSchema) -> list[_CandidateSpec]:
    if field.type != "number" and field.min_val is None and field.max_val is None:
        return []

    specs: list[_CandidateSpec] = []
    if field.min_val is not None:
        specs.append(_CandidateSpec(_number_value(field.min_val - 1), "boundary", "reject", 0.88))
        specs.append(_CandidateSpec(_number_value(field.min_val), "boundary", "accept", 0.86))
    if field.max_val is not None:
        specs.append(_CandidateSpec(_number_value(field.max_val), "boundary", "accept", 0.86))
        specs.append(_CandidateSpec(_number_value(field.max_val + 1), "boundary", "reject", 0.88))
    specs.append(_CandidateSpec("not-a-number", "malformed", "reject", 0.87))
    return specs


def _date_specs(
    field: FieldSchema,
    semantic_type: str,
    likely_format: str,
) -> list[_CandidateSpec]:
    if field.type != "date" and semantic_type != "date_of_birth" and "date" not in likely_format.lower():
        return []

    today = date.today().isoformat()
    return [
        _CandidateSpec("1990-01-01", "valid", "accept", 0.95),
        _CandidateSpec("01/01/1990", "valid", "accept", 0.86),
        _CandidateSpec(today, "boundary", "reject", 0.88),
        _CandidateSpec("2099-01-01", "invalid", "reject", 0.86),
        _CandidateSpec("1990-02-30", "malformed", "reject", 0.91),
    ]


def _required_specs(field: FieldSchema) -> list[_CandidateSpec]:
    if not field.required:
        return []
    return [_CandidateSpec("", "empty", "reject", 0.94)]


def _whitespace_specs() -> list[_CandidateSpec]:
    return [_CandidateSpec("   ", "whitespace", "reject", 0.83)]


def _security_specs() -> list[_CandidateSpec]:
    return [
        _CandidateSpec(SECURITY_PAYLOAD, "suspicious", "reject", 0.92),
        _CandidateSpec("<script>alert(1)</script>", "suspicious", "reject", 0.91),
    ]


def _structured_identifier_specs(likely_format: str) -> list[_CandidateSpec]:
    if likely_format.startswith("pan-india"):
        return [
            _CandidateSpec("ABCDE1234F", "valid", "accept", 0.94),
            _CandidateSpec("ABCD12345F", "malformed", "reject", 0.9),
        ]
    if likely_format.startswith("ssn-us"):
        return [
            _CandidateSpec("123-45-6789", "valid", "accept", 0.92),
            _CandidateSpec("12-345-6789", "malformed", "reject", 0.9),
        ]
    if likely_format.startswith("aadhaar-india"):
        return [
            _CandidateSpec("1234 5678 9012", "valid", "accept", 0.92),
            _CandidateSpec("12345 678 9012", "malformed", "reject", 0.9),
        ]
    if likely_format.startswith("ifsc-india"):
        return [
            _CandidateSpec("HDFC0001234", "valid", "accept", 0.92),
            _CandidateSpec("HDF00001234", "malformed", "reject", 0.9),
        ]
    if likely_format.startswith("zip-us"):
        return [
            _CandidateSpec("12345", "valid", "accept", 0.9),
            _CandidateSpec("12345-6789", "valid", "accept", 0.86),
            _CandidateSpec("1234", "boundary", "reject", 0.88),
        ]
    return []


def _range_length_specs(
    min_size: int,
    max_size: int,
    *,
    digits_only: bool,
) -> list[_CandidateSpec]:
    value_factory = _digits if digits_only else _alnum
    specs = [
        _CandidateSpec(value_factory(min_size), "boundary", "accept", 0.86),
        _CandidateSpec(value_factory(max_size), "boundary", "accept", 0.86),
    ]
    if min_size > 0:
        specs.append(_CandidateSpec(value_factory(min_size - 1), "boundary", "reject", 0.9))
    specs.append(_CandidateSpec(value_factory(max_size + 1), "boundary", "reject", 0.9))
    return specs


def _dedupe_specs(specs: Sequence[_CandidateSpec]) -> list[_CandidateSpec]:
    unique: dict[tuple[str, str], _CandidateSpec] = {}
    for spec in specs:
        key = (str(spec.input_value), spec.category)
        current = unique.get(key)
        if current is None or spec.weight > current.weight:
            unique[key] = spec
    return list(unique.values())


def _bounded_specs(specs: Sequence[_CandidateSpec]) -> list[_CandidateSpec]:
    order = {
        "valid": 0,
        "boundary": 1,
        "malformed": 2,
        "suspicious": 3,
        "empty": 4,
        "whitespace": 5,
        "invalid": 6,
    }
    ranked = sorted(
        specs,
        key=lambda item: (order.get(item.category, 99), -item.weight, str(item.input_value)),
    )
    selected: list[_CandidateSpec] = []
    used: set[tuple[str, str]] = set()
    coverage_categories = ["valid", "boundary", "malformed", "suspicious", "empty", "whitespace"]

    for category in coverage_categories:
        for item in ranked:
            key = (str(item.input_value), item.category)
            if item.category != category or key in used:
                continue
            selected.append(item)
            used.add(key)
            break

    for item in ranked:
        if len(selected) >= MAX_CANDIDATES_PER_FIELD:
            break
        key = (str(item.input_value), item.category)
        if key in used:
            continue
        selected.append(item)
        used.add(key)

    return selected[:MAX_CANDIDATES_PER_FIELD]


def _priority_for(field: FieldSchema, confidence: float, spec: _CandidateSpec) -> float:
    category_boost = {
        "valid": 0.07,
        "empty": 0.1 if field.required else 0.02,
        "boundary": 0.09,
        "suspicious": 0.09,
        "malformed": 0.06,
        "whitespace": 0.04,
        "invalid": 0.03,
    }.get(spec.category, 0.0)
    score = (confidence * 0.45) + (spec.weight * 0.45) + category_boost
    return round(min(max(score, 0.0), 1.0), 4)


def _fallback_semantic_type(field: FieldSchema) -> str:
    haystack = (
        f"{field.name} {field.label or ''} {field.dom_id or ''} "
        f"{field.placeholder or ''} {field.context_text or ''}"
    ).lower()
    if field.type == "select":
        return "select_option"
    if field.type in {"checkbox", "radio"}:
        return "boolean_choice"
    if field.type == "email" or "email" in haystack:
        return "email"
    if field.type == "tel" or "mobile" in haystack or "phone" in haystack or "contact" in haystack:
        return "mobile_number"
    if "address" in haystack or "street" in haystack:
        return "address"
    if "city" in haystack:
        return "city"
    if "state" in haystack or "province" in haystack:
        return "state"
    if "zip" in haystack or "postal" in haystack or "pincode" in haystack:
        return "postal_code"
    if "amount" in haystack or "price" in haystack or "currency" in haystack:
        return "amount"
    if ("loan" in haystack and "account" in haystack) or "lan" in haystack:
        return "loan_account_number"
    if "account" in haystack and ("number" in haystack or "id" in haystack):
        return "account_number"
    if "dob" in haystack or ("date" in haystack and "birth" in haystack):
        return "date_of_birth"
    if field.type == "date" or "date" in haystack:
        return "date"
    if "application" in haystack or "reference" in haystack:
        return "application_reference_number"
    if "name" in haystack:
        return "name"
    if field.type == "textarea" or "comment" in haystack or "message" in haystack:
        return "free_text"
    return "generic_text"


def _fallback_confidence(semantic_type: str) -> float:
    return {
        "phone": 0.78,
        "mobile_number": 0.78,
        "loan_account_number": 0.76,
        "account_number": 0.74,
        "date_of_birth": 0.74,
        "date": 0.7,
        "postal_code": 0.74,
        "address": 0.68,
        "city": 0.68,
        "state": 0.66,
        "amount": 0.72,
        "select_option": 0.68,
        "boolean_choice": 0.66,
        "free_text": 0.6,
        "application_reference_number": 0.72,
        "email": 0.7,
        "name": 0.58,
    }.get(semantic_type, 0.45)


def _generic_valid_value(field: FieldSchema) -> CandidateValue:
    if field.type == "number":
        return _number_value(field.min_val if field.min_val is not None else 1.0)
    if field.type == "date":
        return "1990-01-01"
    return "sample"


def _digits(size: int) -> str:
    if size <= 0:
        return ""
    return ("1234567890" * ((size // 10) + 1))[:size]


def _letters(size: int) -> str:
    if size <= 0:
        return ""
    return ("abcdef" * ((size // 6) + 1))[:size]


def _alnum(size: int) -> str:
    if size <= 0:
        return ""
    return ("A1B2C3" * ((size // 6) + 1))[:size]


def _number_value(value: float) -> int | float:
    return int(value) if value.is_integer() else value
