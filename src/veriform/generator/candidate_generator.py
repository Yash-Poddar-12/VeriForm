"""Semantic-aware candidate input generation powered by Constraint Profiles."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Sequence, Union

from veriform.constraint_ir.enums import CharsetCategory
from veriform.constraint_ir.models.profile import ConstraintProfile
from veriform.models.schemas import CandidateInputSchema, FieldSchema

CandidateValue = Union[str, int, float, bool]

SECURITY_PAYLOAD = "' OR '1'='1"
MAX_CANDIDATES_PER_FIELD = 12


@dataclass(frozen=True)
class _CandidateSpec:
    input_value: CandidateValue
    category: str
    expected_outcome: str
    weight: float


async def build_candidate_inputs(
    fields: Sequence[FieldSchema],
    constraint_profiles: Sequence[ConstraintProfile],
) -> list[CandidateInputSchema]:
    """Build deterministic candidate inputs directly from IR constraint profiles."""
    candidates: list[CandidateInputSchema] = []
    
    # Map for easy lookup
    profiles_by_id = {p.profile_id.replace("profile_", ""): p for p in constraint_profiles}

    for field_index, field in enumerate(fields, start=1):
        profile = profiles_by_id.get(field.field_id)
        if not profile:
            continue

        specs = _candidate_specs_for_profile(field, profile)
        
        # Phase 3: AI-Assisted Candidate Expansion
        from veriform.config import settings
        if settings.enable_ai:
            ai_specs = await _ai_expand_candidates(field, profile)
            specs.extend(ai_specs)
            
        deduped = _dedupe_specs(specs)
        bounded = _bounded_specs(deduped)

        for spec_index, spec in enumerate(bounded, start=1):
            candidates.append(
                CandidateInputSchema(
                    candidate_id=f"{field.field_id}_cand_{field_index:03d}_{spec_index:02d}",
                    run_id=field.run_id,
                    field_id=field.field_id,
                    input_value=spec.input_value,
                    category=spec.category,
                    expected_outcome=spec.expected_outcome,
                    priority_score=_priority_for(field, profile.confidence, spec),
                )
            )

    return candidates

async def _ai_expand_candidates(field: FieldSchema, profile: ConstraintProfile) -> list[_CandidateSpec]:
    """Optionally generate semantic edge cases and adversarial payloads using AI."""
    from veriform.ai.registry import get_ai_provider
    provider = get_ai_provider()
    
    prompt = (
        f"Generate 3 extreme malicious payloads and 2 semantic edge cases for an HTML form field.\n"
        f"Field Type: {field.type}\nField Name: {field.name}\n"
        f"Semantic Profile: {profile.semantic_type}\n"
        "Return exactly JSON format: {\"candidates\": [{\"value\": \"val\", \"category\": \"suspicious\", \"outcome\": \"reject\"}]}"
    )
    
    try:
        res = await provider.generate(prompt=prompt, response_format={"type": "json_object"})
        data = res.get("output", {})
        
        # Safe structural parsing, fail gracefully if AI hallucinated format
        if isinstance(data, str):
            import json
            data = json.loads(data)
            
        new_specs = []
        for c in data.get("candidates", []):
            if "value" in c and "category" in c:
                new_specs.append(_CandidateSpec(
                    input_value=c["value"],
                    category=c["category"],
                    expected_outcome=c.get("outcome", "reject"),
                    weight=0.9
                ))
        return new_specs
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning("AI Candidate Expansion failed, falling back to deterministic: %s", e)
        return []



def _candidate_specs_for_profile(field: FieldSchema, profile: ConstraintProfile) -> list[_CandidateSpec]:
    """Generate all possible candidate specs using the semantic type and structural IR."""
    specs: list[_CandidateSpec] = []
    
    # 1. Semantic catalog (covers valid, malformed, boundary for known types)
    specs.extend(_semantic_specs(profile.semantic_type))
    
    # 2. Structural bounds and exact formats
    specs.extend(_structural_specs(profile))
    
    # 3. Numeric bounds (if field has min/max value)
    specs.extend(_numeric_bounds_specs(field))
    
    # 4. Date specifics
    specs.extend(_date_specs(field, profile.semantic_type))
    
    # 5. Required empty cases
    specs.extend(_required_specs(field))
    
    # 6. Malicious/security payloads
    specs.extend(_security_specs())
    specs.extend(_whitespace_specs())

    # Fallback to ensure at least one valid candidate
    if not any(spec.category == "valid" for spec in specs):
        specs.insert(0, _CandidateSpec(_generic_valid_value(field), "valid", "accept", 0.82))
        
    return specs
    
def _structural_specs(profile: ConstraintProfile) -> list[_CandidateSpec]:
    """Use the ConstraintProfile's segments and charsets to generate structural tests."""
    specs: list[_CandidateSpec] = []
    
    # Try to generate a valid string matching all segments exactly
    valid_parts = []
    malformed_parts = []
    dominant_factory = _alnum
    
    for seg in profile.segment_model.segments:
        min_l = 1
        max_l = 1
        charset = CharsetCategory.ALPHANUMERIC
        
        for c in seg.constraints:
            if c.type == "length":
                min_l = c.min_length
                max_l = c.max_length
            elif c.type == "charset":
                charset = c.category
                
        # Generate valid part
        target_len = min(min_l, 20)  # Bound to reasonable
        if charset == CharsetCategory.NUMERIC:
            valid_parts.append(_digits(target_len))
            malformed_parts.append(_letters(target_len) or "A")
            dominant_factory = _digits
        elif charset == CharsetCategory.ALPHA_UPPER:
            valid_parts.append(_letters(target_len).upper())
            malformed_parts.append(_digits(target_len) or "1")
            dominant_factory = _letters
        else:
            valid_parts.append(_alnum(target_len))
            malformed_parts.append("###")

    sep = profile.segment_model.separator or ""
    valid_str = sep.join(valid_parts)
    if valid_str:
        specs.append(_CandidateSpec(valid_str, "valid", "accept", 0.95))
        
    malformed_str = sep.join(malformed_parts)
    if malformed_str:
        specs.append(_CandidateSpec(malformed_str, "malformed", "reject", 0.88))

    # Boundary specs based on total lengths
    min_len = profile.total_min_length()
    max_len = profile.total_max_length()
    
    if max_len < 500: # Don't test valid upper bound if it's implicitly 500
        specs.append(_CandidateSpec(dominant_factory(max_len), "boundary", "accept", 0.86))
        
    if min_len > 0:
        specs.append(_CandidateSpec(dominant_factory(min_len), "boundary", "accept", 0.84))
        
    # Invalid boundary points
    if max_len < 500:
        specs.append(_CandidateSpec(dominant_factory(max_len + 1), "boundary", "reject", 0.9))
        
    if min_len > 1:
        specs.append(_CandidateSpec(dominant_factory(min_len - 1), "boundary", "reject", 0.88))
        
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
            _CandidateSpec("12A456789012", "malformed", "reject", 0.88),
        ],
        "date_of_birth": [
            _CandidateSpec("1990-01-01", "valid", "accept", 0.95),
            _CandidateSpec("2099-01-01", "invalid", "reject", 0.86),
            _CandidateSpec("1990-02-30", "malformed", "reject", 0.91),
        ],
        "date": [
            _CandidateSpec("2024-12-31", "valid", "accept", 0.9),
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
        ],
        "postal_code": [
            _CandidateSpec("90210", "valid", "accept", 0.9),
            _CandidateSpec("12345-6789", "valid", "accept", 0.84),
            _CandidateSpec("12", "boundary", "reject", 0.86),
            _CandidateSpec("ABCDE", "malformed", "reject", 0.82),
        ],
        "address": [
            _CandidateSpec("221B Baker Street", "valid", "accept", 0.88),
            _CandidateSpec("### !!!", "malformed", "reject", 0.82),
        ],
        "city": [
            _CandidateSpec("San Francisco", "valid", "accept", 0.86),
            _CandidateSpec("1234", "malformed", "reject", 0.82),
        ],
        "state": [
            _CandidateSpec("CA", "valid", "accept", 0.84),
            _CandidateSpec("C4", "malformed", "reject", 0.8),
        ],
        "amount": [
            _CandidateSpec(100.5, "valid", "accept", 0.9),
            _CandidateSpec(-1, "boundary", "reject", 0.87),
        ],
        "select_option": [
            _CandidateSpec("option_1", "valid", "accept", 0.8),
            _CandidateSpec("invalid_option", "invalid", "reject", 0.82),
        ],
        "boolean_choice": [
            _CandidateSpec(True, "valid", "accept", 0.82),
            _CandidateSpec(False, "valid", "accept", 0.82),
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
            _CandidateSpec("sample text", "valid", "accept", 0.78),
        ],
        "free_text": [
            _CandidateSpec("This is a user-entered comment.", "valid", "accept", 0.82),
        ],
    }
    return list(catalog.get(semantic_type, catalog["generic_text"]))


def _structural_length_specs(profile: ConstraintProfile) -> list[_CandidateSpec]:
    """Use the ConstraintProfile's segments and length to generate structural tests."""
    specs: list[_CandidateSpec] = []
    
    # Extract dominant charset from the first segment if single-segment
    # (For complex multi-segment we rely on semantic catalog + future combinatorics)
    digits_only = False
    if profile.is_single_segment():
        seg = profile.segment_model.segments[0]
        charsets = [c for c in seg.constraints if c.type == "charset"]
        if charsets and charsets[0].category == CharsetCategory.NUMERIC:
            digits_only = True
            
    min_len = profile.total_min_length()
    max_len = profile.total_max_length()
    
    value_factory = _digits if digits_only else _letters

    # Valid boundary points
    if max_len < 500: # Don't test valid upper bound if it's implicitly 500
        specs.append(_CandidateSpec(value_factory(max_len), "boundary", "accept", 0.86))
        
    if min_len > 0:
        specs.append(_CandidateSpec(value_factory(min_len), "boundary", "accept", 0.84))
        
    # Invalid boundary points
    if max_len < 500:
        specs.append(_CandidateSpec(value_factory(max_len + 1), "boundary", "reject", 0.9))
        
    if min_len > 1:
        specs.append(_CandidateSpec(value_factory(min_len - 1), "boundary", "reject", 0.88))
        
    return specs


def _numeric_bounds_specs(field: FieldSchema) -> list[_CandidateSpec]:
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


def _date_specs(field: FieldSchema, semantic_type: str) -> list[_CandidateSpec]:
    if field.type != "date" and semantic_type not in ("date", "date_of_birth"):
        return []

    today = date.today().isoformat()
    return [
        _CandidateSpec("1990-01-01", "valid", "accept", 0.95),
        _CandidateSpec(today, "boundary", "reject" if semantic_type == "date_of_birth" else "accept", 0.88),
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
        _CandidateSpec("../../../../etc/passwd", "suspicious", "reject", 0.85),
    ]


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
    coverage_categories = ["valid", "boundary", "malformed", "suspicious", "empty", "whitespace", "invalid"]

    # Ensure representation from each critical category
    for category in coverage_categories:
        for item in ranked:
            key = (str(item.input_value), item.category)
            if item.category != category or key in used:
                continue
            selected.append(item)
            used.add(key)
            break

    # Fill the rest ordered by rank
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
