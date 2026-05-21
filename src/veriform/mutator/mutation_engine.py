"""
veriform.mutator.mutation_engine
================================
Deterministically generates behavioral probes for fields.
"""

from __future__ import annotations

import hashlib
from typing import List

from veriform.models.schemas import FieldSchema
from veriform.schemas.mutations import MutationCategory, MutationProbe, MutationProfile
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


class MutationEngine:
    """Generates behavioral mutation probes for given form fields."""

    def __init__(self, profile: MutationProfile = MutationProfile.BALANCED):
        self.profile = profile

    def _generate_id(self, field_id: str, category: str, value: str) -> str:
        """Create a deterministic unique mutation ID."""
        hash_suffix = hashlib.md5(f"{field_id}_{category}_{value}".encode()).hexdigest()[:6]
        return f"{field_id}_{category}_{hash_suffix}"

    def _create_probe(
        self, field: FieldSchema, category: MutationCategory, purpose: str, value: str
    ) -> MutationProbe:
        return MutationProbe(
            mutation_id=self._generate_id(field.field_id, category.value, value),
            field_id=field.field_id,
            category=category,
            purpose=purpose,
            value=value,
        )

    def generate_for_field(self, field: FieldSchema) -> List[MutationProbe]:
        """Main entry point to generate mutations for a single field."""
        probes: List[MutationProbe] = []

        # 1. Null-like probes (Always included)
        probes.extend(self._generate_null_probes(field))

        # 2. Boundary Length Probes
        probes.extend(self._generate_boundary_probes(field))

        # 3. Charset Probes (Field-aware optimization)
        probes.extend(self._generate_charset_probes(field))

        # 4. Whitespace & Unicode (Based on profile)
        probes.extend(self._generate_edge_case_probes(field))

        # 5. Semantic-specific probes
        probes.extend(self._generate_semantic_probes(field))
        
        # Enforce deterministic caps
        return self._apply_caps(probes)

    def _generate_null_probes(self, field: FieldSchema) -> List[MutationProbe]:
        return [
            self._create_probe(
                field, MutationCategory.NULL_LIKE_PROBE, "discover requiredness", ""
            )
        ]

    def _generate_boundary_probes(self, field: FieldSchema) -> List[MutationProbe]:
        probes = []
        base_char = "9" if field.semantic_type in ("phone", "pincode", "numeric_amount") else "A"
        
        # Min length
        min_len = field.min_length or 1
        if min_len > 1:
            probes.append(
                self._create_probe(
                    field, 
                    MutationCategory.BOUNDARY_UNDERFLOW, 
                    "discover minimum accepted length", 
                    base_char * (min_len - 1)
                )
            )
        probes.append(
            self._create_probe(
                field, 
                MutationCategory.BOUNDARY_EXACT, 
                "validate minimum exact boundary", 
                base_char * min_len
            )
        )

        # Max length
        max_len = field.max_length or (min_len + 50)  # arbitrary upper bound if unknown
        if field.max_length:
            probes.append(
                self._create_probe(
                    field, 
                    MutationCategory.BOUNDARY_EXACT, 
                    "validate maximum exact boundary", 
                    base_char * max_len
                )
            )
            probes.append(
                self._create_probe(
                    field, 
                    MutationCategory.BOUNDARY_OVERFLOW, 
                    "discover maximum accepted length", 
                    base_char * (max_len + 1)
                )
            )

        return probes

    def _generate_charset_probes(self, field: FieldSchema) -> List[MutationProbe]:
        probes = []
        target_len = field.min_length or 5
        
        # Digits
        probes.append(self._create_probe(
            field, MutationCategory.CHARSET_DIGITS, "discover numeric acceptance", "9" * target_len
        ))
        
        # Alpha
        probes.append(self._create_probe(
            field, MutationCategory.CHARSET_ALPHA, "discover alphabet acceptance", "A" * target_len
        ))
        
        # Special
        probes.append(self._create_probe(
            field, MutationCategory.CHARSET_SPECIAL, "discover special character acceptance", "@#$" * (target_len // 3 + 1)
        ))

        return probes

    def _generate_edge_case_probes(self, field: FieldSchema) -> List[MutationProbe]:
        probes = []
        target_len = field.min_length or 5
        base_valid = "9" * target_len if field.semantic_type in ("phone", "pincode") else "A" * target_len
        
        if self.profile in (MutationProfile.BALANCED, MutationProfile.EXHAUSTIVE):
            # Whitespace
            probes.append(self._create_probe(
                field, MutationCategory.WHITESPACE_PROBE, "discover trailing whitespace handling", f"{base_valid}   "
            ))
            # Unicode
            probes.append(self._create_probe(
                field, MutationCategory.UNICODE_PROBE, "discover emoji/unicode rejection", "🔥" * target_len
            ))
            
        if self.profile == MutationProfile.EXHAUSTIVE:
            probes.append(self._create_probe(
                field, MutationCategory.HOMOGLYPH_PROBE, "discover visual spoofing rejection", base_valid.replace('A', 'Α') # Greek Alpha
            ))

        return probes

    def _generate_semantic_probes(self, field: FieldSchema) -> List[MutationProbe]:
        probes = []
        
        if field.semantic_type == "email":
            probes.extend([
                self._create_probe(field, MutationCategory.STRUCTURE_PROBE, "discover valid email structure", "test@example.com"),
                self._create_probe(field, MutationCategory.STRUCTURE_PROBE, "discover missing @ rejection", "testexample.com"),
                self._create_probe(field, MutationCategory.STRUCTURE_PROBE, "discover missing domain rejection", "test@.com"),
            ])
            
        elif field.semantic_type == "phone":
            # Assume 10-digit standard for discovery
            target = field.max_length or 10
            probes.extend([
                self._create_probe(field, MutationCategory.PREFIX_PROBE, "discover prefix constraint (start with 9)", "9" + "1" * (target - 1)),
                self._create_probe(field, MutationCategory.PREFIX_PROBE, "discover prefix constraint (start with 0)", "0" + "1" * (target - 1)),
            ])
            
        return probes

    def _apply_caps(self, probes: List[MutationProbe]) -> List[MutationProbe]:
        """Apply deterministic caps based on profile."""
        if self.profile == MutationProfile.LIGHTWEIGHT:
            max_probes = 8
        elif self.profile == MutationProfile.BALANCED:
            max_probes = 20
        else:
            max_probes = 50
            
        return probes[:max_probes]
