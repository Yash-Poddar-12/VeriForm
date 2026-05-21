"""
veriform.detector.state_summarizer
==================================
Deterministic + AI augmented state clustering.
"""

from __future__ import annotations

import re
from typing import Dict, Any

from veriform.models.schemas import FieldSchema
from veriform.detector.semantic_state import SemanticState
from veriform.config import settings

class StateSummarizer:
    async def summarize_state(self, state_hash: str, fields: list[FieldSchema], page_title: str) -> SemanticState:
        """Classify a state deterministically, with optional AI fallback."""
        # 1. Deterministic Heuristics
        text_corpus = f"{page_title} " + " ".join([f.name or "" for f in fields] + [f.type for f in fields])
        text_corpus = text_corpus.lower()
        
        classification = "generic_form"
        confidence = 0.5
        
        if re.search(r'login|password|auth|sign.in|credential', text_corpus):
            classification = "auth_flow"
            confidence = 0.8
        elif re.search(r'card|cvv|credit|billing|checkout', text_corpus):
            classification = "payment_flow"
            confidence = 0.85
        elif re.search(r'otp|one.time.password|verification.code', text_corpus):
            classification = "otp_screen"
            confidence = 0.9
        elif re.search(r'success|confirm|thank.you', text_corpus) or not fields:
            classification = "confirmation"
            confidence = 0.7
            
        # 2. AI Augmentation (Optional)
        if settings.enable_ai and confidence < 0.8:
            from veriform.ai.registry import get_ai_provider
            provider = get_ai_provider()
            
            prompt = (
                f"Classify this UI state based on its fields: {text_corpus}. "
                "Choices: auth_flow, payment_flow, otp_screen, confirmation, generic_form, error_state."
                "Return exactly JSON format: {\"classification\": \"value\", \"confidence\": 0.9}"
            )
            
            try:
                res = await provider.generate(prompt=prompt, response_format={"type": "json_object"})
                data = res.get("output", {})
                
                if isinstance(data, str):
                    import json
                    data = json.loads(data)
                    
                if "classification" in data and "confidence" in data:
                    classification = data["classification"]
                    confidence = data["confidence"]
            except Exception:
                pass # Fallback to deterministic
                
        return SemanticState(
            classification=classification,
            confidence=confidence,
            field_roles=[f.type for f in fields],
            has_errors=False, # Would need DOM parsing for aria-invalid
            is_terminal=(classification == "confirmation"),
            raw_hash=state_hash
        )
