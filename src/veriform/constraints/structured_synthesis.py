"""Structured deterministic synthesis for likely field formats."""

from __future__ import annotations

import re

from veriform.models.schemas import FieldSchema


def synthesize_likely_format(field: FieldSchema, semantic_type: str) -> str:
    """Infer a stable likely-format descriptor from deterministic metadata."""
    pattern = (field.pattern or "").strip()
    if pattern:
        structured = _pattern_descriptor(pattern)
        if structured:
            return structured

    if field.type == "email" or semantic_type == "email":
        return "email-local-domain"
    if field.type == "date" or semantic_type in {"date", "date_of_birth"}:
        return "date-iso-or-common"
    if field.type == "number" or semantic_type == "amount":
        return "numeric-decimal"
    if semantic_type in {"mobile_number", "phone"}:
        return "phone-local-or-international"
    if semantic_type in {"postal_code"}:
        return "postal-code"
    if semantic_type in {"application_reference_number", "account_number", "loan_account_number"}:
        return _length_descriptor(field, fallback="identifier-alphanumeric")
    return _length_descriptor(field, fallback="free-text")


def _pattern_descriptor(pattern: str) -> str | None:
    normalized = pattern.replace("\\\\", "\\")
    known_patterns = {
        "^[A-Z]{5}[0-9]{4}[A-Z]{1}$": "pan-india-alpha5-digit4-alpha1",
        "^[0-9]{3}-[0-9]{2}-[0-9]{4}$": "ssn-us-3-2-4",
        "^[0-9]{4}\\s?[0-9]{4}\\s?[0-9]{4}$": "aadhaar-india-4-4-4",
        "^[A-Z]{4}0[A-Z0-9]{6}$": "ifsc-india-alpha4-0-alnum6",
        "^[0-9]{5}(?:-[0-9]{4})?$": "zip-us-5-or-9",
    }
    descriptor = known_patterns.get(normalized)
    if descriptor is not None:
        return descriptor

    if re.fullmatch(r"(?:\[0-9\]|\\d)\{\d+\}", normalized):
        length = int(re.search(r"\{(\d+)\}", normalized).group(1))  # type: ignore[union-attr]
        return f"fixed-digits-{length}"
    digit_range = re.fullmatch(r"(?:\[0-9\]|\\d)\{(\d+),(\d+)\}", normalized)
    if digit_range:
        min_size, max_size = digit_range.groups()
        return f"digits-{min_size}-{max_size}"
    alnum_range = re.fullmatch(r"\[A-Za-z0-9\]\{(\d+),(\d+)\}", normalized)
    if alnum_range:
        min_size, max_size = alnum_range.groups()
        return f"alnum-{min_size}-{max_size}"
    return None


def _length_descriptor(field: FieldSchema, fallback: str) -> str:
    if field.min_length is not None and field.max_length is not None:
        return f"{fallback}-len-{field.min_length}-{field.max_length}"
    if field.max_length is not None:
        return f"{fallback}-max-{field.max_length}"
    if field.min_length is not None:
        return f"{fallback}-min-{field.min_length}"
    return fallback
