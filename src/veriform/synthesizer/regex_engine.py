"""
veriform.synthesizer.regex_engine
=================================
Synthesizes deterministic, explainable regex contracts from inferred behavior.
"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from veriform.inference.dynamic_infer import InferredConstraints
from veriform.models.schemas import FieldSchema
from veriform.schemas.discovery import RegexSynthesisResult
from veriform.schemas.mutations import ProbeResult
from veriform.utils.logging import get_logger

logger = get_logger(__name__)

# Constants for common patterns
REGEX_PAN = r"^[A-Z]{5}[0-9]{4}[A-Z]$"
REGEX_AADHAAR = r"^[2-9]{1}[0-9]{11}$"
REGEX_PINCODE = r"^[1-9][0-9]{5}$"


class RegexEngine:
    """Transforms deterministic constraints into standard regex contracts."""
    
    def synthesize(self, field: FieldSchema, constraints: InferredConstraints, results: List[ProbeResult]) -> RegexSynthesisResult:
        evidence: List[str] = []
        confidence = constraints.confidence
        
        # 1. Contradiction Detection & Normalization
        has_contradiction, conf_penalty, warn_evidence = self._detect_contradictions(constraints, results)
        confidence -= conf_penalty
        evidence.extend(warn_evidence)
        
        # 2. Extract Accepted/Rejected examples
        accepted, rejected = self._extract_examples(results)
        
        # 3. Semantic Override
        semantic_regex, semantic_desc, semantic_conf_boost, semantic_ev = self._apply_semantic_handlers(field, constraints)
        
        if semantic_regex:
            confidence += semantic_conf_boost
            evidence.extend(semantic_ev)
            return RegexSynthesisResult(
                field_id=field.field_id,
                semantic_type=field.semantic_type,
                required=constraints.required or False,
                regex=semantic_regex,
                confidence=min(max(confidence, 0.0), 1.0),
                description=semantic_desc,
                accepted_examples=accepted,
                rejected_examples=rejected,
                evidence=evidence
            )
            
        # 4. Generic Assembly
        gen_regex, gen_desc, gen_ev = self._assemble_generic(constraints)
        evidence.extend(gen_ev)
        
        return RegexSynthesisResult(
            field_id=field.field_id,
            semantic_type=field.semantic_type,
            required=constraints.required or False,
            regex=gen_regex,
            confidence=min(max(confidence, 0.0), 1.0),
            description=gen_desc,
            accepted_examples=accepted,
            rejected_examples=rejected,
            evidence=evidence
        )

    def _detect_contradictions(self, constraints: InferredConstraints, results: List[ProbeResult]) -> Tuple[bool, float, List[str]]:
        has_contradiction = False
        penalty = 0.0
        evidence = []
        
        accepted_lengths = {len(str(r.probe_value)) for r in results if r.accepted and r.probe_value}
        
        if constraints.exact_length:
            invalid_lengths = [l for l in accepted_lengths if l != constraints.exact_length]
            if invalid_lengths:
                has_contradiction = True
                penalty += 0.3
                evidence.append(f"WARNING: exact_length inferred as {constraints.exact_length} but accepted lengths {invalid_lengths}")
        
        # Ensure evidence strings trace the standard constraints
        if constraints.exact_length:
            evidence.append(f"exact length {constraints.exact_length} inferred")
        elif constraints.min_length and constraints.max_length:
            evidence.append(f"length bounds {constraints.min_length}-{constraints.max_length} inferred")
            
        if constraints.allowed_charset:
            evidence.append(f"{constraints.allowed_charset}-only charset inferred")
            
        return has_contradiction, penalty, evidence

    def _extract_examples(self, results: List[ProbeResult]) -> Tuple[List[str], List[str]]:
        accepted = []
        rejected = []
        for r in results:
            if not r.probe_value:
                continue
            val = str(r.probe_value)
            if r.accepted and len(accepted) < 3 and val not in accepted:
                accepted.append(val)
            elif not r.accepted and len(rejected) < 3 and val not in rejected:
                rejected.append(val)
        return accepted, rejected

    def _apply_semantic_handlers(self, field: FieldSchema, constraints: InferredConstraints) -> Tuple[Optional[str], str, float, List[str]]:
        stype = field.semantic_type
        if not stype:
            return None, "", 0.0, []
            
        if stype == "phone":
            # Indian Mobile standard logic based on constraints
            length = constraints.exact_length or 10
            prefix = constraints.prefix_constraint or "[6-9]"
            regex = f"^{prefix}[0-9]{{{length-1}}}$"
            desc = f"{length} digit Indian mobile number starting with {prefix}"
            evidence = [f"prefix {prefix.replace('[','').replace(']','')} accepted"]
            return regex, desc, 0.1, evidence
            
        if stype == "pan":
            return REGEX_PAN, "10-character alphanumeric Indian PAN structure", 0.15, ["semantic PAN structure applied"]
            
        if stype == "aadhaar":
            return REGEX_AADHAAR, "12-digit Indian Aadhaar number not starting with 0 or 1", 0.15, ["semantic Aadhaar structure applied"]
            
        if stype == "pincode":
            return REGEX_PINCODE, "6-digit Indian Postal Code not starting with 0", 0.1, ["semantic pincode structure applied"]
            
        return None, "", 0.0, []

    def _assemble_generic(self, constraints: InferredConstraints) -> Tuple[str, str, List[str]]:
        evidence = []
        
        # Charset mapping
        charset_map = {
            "digits": "[0-9]",
            "alpha": "[A-Za-z]",
            "alphanumeric": "[A-Za-z0-9]",
            "all": "."
        }
        
        cset = charset_map.get(constraints.allowed_charset or "all", ".")
        
        # Length quantifier
        if constraints.exact_length:
            quantifier = f"{{{constraints.exact_length}}}"
            desc_len = f"exactly {constraints.exact_length} characters"
        elif constraints.min_length and constraints.max_length:
            quantifier = f"{{{constraints.min_length},{constraints.max_length}}}"
            desc_len = f"between {constraints.min_length} and {constraints.max_length} characters"
        elif constraints.min_length:
            quantifier = f"{{{constraints.min_length},}}"
            desc_len = f"at least {constraints.min_length} characters"
        elif constraints.max_length:
            quantifier = f"{{0,{constraints.max_length}}}"
            desc_len = f"up to {constraints.max_length} characters"
        else:
            quantifier = "*"
            desc_len = "any length"
            
        regex = f"^{cset}{quantifier}$"
        desc = f"Generic {constraints.allowed_charset or 'any'} string of {desc_len}"
        
        return regex, desc, evidence
