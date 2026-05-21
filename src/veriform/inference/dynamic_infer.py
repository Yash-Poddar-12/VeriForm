"""
veriform.inference.dynamic_infer
================================
Infers deterministic validation contracts from raw probe executions.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from veriform.models.schemas import FieldSchema
from veriform.schemas.mutations import MutationCategory, ProbeResult
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


class InferredConstraints(BaseModel):
    """The deduced deterministic validation rules for a field."""
    field_id: str
    required: Optional[bool] = None
    exact_length: Optional[int] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    allowed_charset: Optional[str] = None
    prefix_constraint: Optional[str] = None
    confidence: float = 0.0


class BehavioralInferencer:
    """Analyzes a history of ProbeResults to deduce constraints."""
    
    def infer(self, field: FieldSchema, results: List[ProbeResult]) -> InferredConstraints:
        """Main inference loop."""
        constraints = InferredConstraints(field_id=field.field_id)
        
        if not results:
            return constraints
            
        # Organize results by category
        by_category = {}
        for r in results:
            cat = r.mutation_id.split("_")[2] if "_" in r.mutation_id else "unknown"
            # Extract category name matching enum logic roughly, but cleaner to use map if we stored it
            # We didn't store category in ProbeResult, so let's match substring
            for enum_cat in MutationCategory:
                if enum_cat.value in r.mutation_id:
                    by_category.setdefault(enum_cat.value, []).append(r)
                    
        self._infer_requiredness(by_category, constraints)
        self._infer_length_bounds(by_category, constraints)
        self._infer_charsets(by_category, constraints)
        self._infer_prefixes(by_category, constraints)
        
        self._calculate_confidence(constraints)
        return constraints

    def _infer_requiredness(self, by_category: Dict[str, List[ProbeResult]], constraints: InferredConstraints):
        null_probes = by_category.get(MutationCategory.NULL_LIKE_PROBE.value, [])
        if null_probes:
            # If null probe is rejected, field is required
            constraints.required = not null_probes[0].accepted

    def _infer_length_bounds(self, by_category: Dict[str, List[ProbeResult]], constraints: InferredConstraints):
        underflows = by_category.get(MutationCategory.BOUNDARY_UNDERFLOW.value, [])
        exacts = by_category.get(MutationCategory.BOUNDARY_EXACT.value, [])
        overflows = by_category.get(MutationCategory.BOUNDARY_OVERFLOW.value, [])
        
        # Analyze exact accepted matches
        accepted_lengths = set()
        for e in exacts:
            if e.accepted:
                accepted_lengths.add(len(e.probe_value))
                
        if len(accepted_lengths) == 1:
            constraints.exact_length = list(accepted_lengths)[0]
            constraints.min_length = constraints.exact_length
            constraints.max_length = constraints.exact_length
        elif len(accepted_lengths) > 1:
            constraints.min_length = min(accepted_lengths)
            constraints.max_length = max(accepted_lengths)
            
        # Verify with underflows/overflows if they are rejected
        if underflows and not underflows[0].accepted and constraints.min_length is None:
            constraints.min_length = len(underflows[0].probe_value) + 1
            
        if overflows and not overflows[0].accepted and constraints.max_length is None:
            constraints.max_length = len(overflows[0].probe_value) - 1

    def _infer_charsets(self, by_category: Dict[str, List[ProbeResult]], constraints: InferredConstraints):
        digits = by_category.get(MutationCategory.CHARSET_DIGITS.value, [])
        alpha = by_category.get(MutationCategory.CHARSET_ALPHA.value, [])
        special = by_category.get(MutationCategory.CHARSET_SPECIAL.value, [])
        
        d_ok = digits[0].accepted if digits else False
        a_ok = alpha[0].accepted if alpha else False
        s_ok = special[0].accepted if special else False
        
        if d_ok and not a_ok and not s_ok:
            constraints.allowed_charset = "digits"
        elif a_ok and not d_ok and not s_ok:
            constraints.allowed_charset = "alpha"
        elif d_ok and a_ok and not s_ok:
            constraints.allowed_charset = "alphanumeric"
        elif d_ok and a_ok and s_ok:
            constraints.allowed_charset = "all"

    def _infer_prefixes(self, by_category: Dict[str, List[ProbeResult]], constraints: InferredConstraints):
        prefixes = by_category.get(MutationCategory.PREFIX_PROBE.value, [])
        if not prefixes:
            return
            
        accepted_prefixes = []
        for p in prefixes:
            if p.accepted and p.probe_value:
                accepted_prefixes.append(str(p.probe_value)[0])
                
        if accepted_prefixes and len(accepted_prefixes) < len(prefixes):
            # We found a constraint
            constraints.prefix_constraint = f"[{''.join(sorted(set(accepted_prefixes)))}]"

    def _calculate_confidence(self, constraints: InferredConstraints):
        score = 0.5
        if constraints.required is not None:
            score += 0.1
        if constraints.min_length is not None or constraints.max_length is not None:
            score += 0.2
        if constraints.allowed_charset is not None:
            score += 0.16
        constraints.confidence = min(score, 1.0)
