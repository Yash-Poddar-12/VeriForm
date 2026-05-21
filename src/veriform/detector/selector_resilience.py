"""
veriform.detector.selector_resilience
=====================================
Self-healing selector engine based on deterministic heuristics.
"""

from __future__ import annotations

import difflib
from typing import Any, Dict, List, Optional, Tuple

from playwright.async_api import Page
from veriform.models.healing import SelectorFingerprint, RepairCandidate
from veriform.utils.logging import get_logger

logger = get_logger(__name__)


class SelectorResilienceEngine:
    def __init__(self, page: Page):
        self.page = page

    async def build_fingerprint(self, selector: str) -> Optional[SelectorFingerprint]:
        """Extract a semantic signature from the DOM before interaction."""
        try:
            element = await self.page.query_selector(selector)
            if not element:
                return None
                
            tag_name = await element.evaluate("el => el.tagName.toLowerCase()")
            text_content = await element.text_content()
            aria_label = await element.get_attribute("aria-label")
            placeholder = await element.get_attribute("placeholder")
            
            # Simple hierarchy depth heuristic
            depth = await element.evaluate(
                "el => { let d = 0; let curr = el; while(curr.parentElement) { d++; curr = curr.parentElement; } return d; }"
            )
            
            return SelectorFingerprint(
                tag=tag_name,
                text_content=text_content.strip() if text_content else None,
                aria_label=aria_label,
                placeholder=placeholder,
                hierarchy_depth=depth,
            )
        except Exception as e:
            logger.warning("Failed to build fingerprint for %s: %s", selector, e)
            return None

    def _similarity_score(self, a: Optional[str], b: Optional[str]) -> float:
        if not a and not b:
            return 0.0
        if not a or not b:
            return 0.0
        return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()

    def score_candidate(self, historical: SelectorFingerprint, candidate: SelectorFingerprint) -> float:
        """Calculate weighted heuristic similarity."""
        score = 0.0
        weights = 0.0
        
        # Tag name is critical
        if historical.tag == candidate.tag:
            score += 2.0
        weights += 2.0
            
        # Text/Labels
        if historical.text_content or candidate.text_content:
            score += 1.5 * self._similarity_score(historical.text_content, candidate.text_content)
            weights += 1.5
            
        if historical.aria_label or candidate.aria_label:
            score += 1.5 * self._similarity_score(historical.aria_label, candidate.aria_label)
            weights += 1.5
            
        if historical.placeholder or candidate.placeholder:
            score += 1.0 * self._similarity_score(historical.placeholder, candidate.placeholder)
            weights += 1.0
            
        # Hierarchy penalty
        depth_diff = abs(historical.hierarchy_depth - candidate.hierarchy_depth)
        if depth_diff == 0:
            score += 1.0
        elif depth_diff <= 2:
            score += 0.5
        weights += 1.0
        
        return score / weights if weights > 0 else 0.0

    async def attempt_repair(self, failed_selector: str, historical_fingerprint: SelectorFingerprint) -> Optional[RepairCandidate]:
        """Scan the DOM for elements that semantically match the historical fingerprint."""
        logger.info("Attempting heuristic repair for failed selector: %s", failed_selector)
        
        # Extract all interactive or matching tag candidates
        candidates_js = """
        () => {
            const elements = Array.from(document.querySelectorAll('input, button, a, select, textarea, [role="button"]'));
            return elements.map((el, i) => {
                let d = 0; let curr = el; while(curr.parentElement) { d++; curr = curr.parentElement; }
                return {
                    idx: i,
                    tag: el.tagName.toLowerCase(),
                    text: el.innerText || el.textContent || '',
                    aria: el.getAttribute('aria-label') || '',
                    placeholder: el.getAttribute('placeholder') || '',
                    depth: d
                };
            });
        }
        """
        
        dom_elements = await self.page.evaluate(candidates_js)
        
        best_candidate: Optional[RepairCandidate] = None
        highest_score = 0.0
        best_idx = -1
        
        for el in dom_elements:
            cand_fp = SelectorFingerprint(
                tag=el["tag"],
                text_content=el["text"].strip(),
                aria_label=el["aria"],
                placeholder=el["placeholder"],
                hierarchy_depth=el["depth"]
            )
            score = self.score_candidate(historical_fingerprint, cand_fp)
            
            if score > highest_score:
                highest_score = score
                best_idx = el["idx"]
                best_candidate = RepairCandidate(
                    selector=f"nth-match(input, button, a, select, textarea, [role='button'], {best_idx + 1})", # Playwright pseudo selector, rough approx. We will use a unique data attribute or text selector instead in real implementation
                    confidence_score=score,
                    matching_heuristics=["heuristic_similarity"]
                )
        
        # We need a robust selector back to playwright
        if best_candidate and highest_score >= 0.55:
            # Generate a better selector using the dom element text or attributes
            text_match = dom_elements[best_idx]['text'].strip()
            if text_match:
                # Truncate text for selector to prevent huge quotes
                clean_text = text_match.split('\\n')[0][:30].strip()
                safe_selector = f"{dom_elements[best_idx]['tag']}:has-text(\"{clean_text}\")"
            elif dom_elements[best_idx]['aria']:
                safe_selector = f"[aria-label='{dom_elements[best_idx]['aria']}']"
            elif dom_elements[best_idx]['placeholder']:
                safe_selector = f"[placeholder='{dom_elements[best_idx]['placeholder']}']"
            else:
                # Fallback to xpath or nth-match if possible, but keep it simple
                safe_selector = f"{dom_elements[best_idx]['tag']}:nth-of-type(1)"
                
            best_candidate.selector = safe_selector
            logger.info("Found repair candidate with score %.2f: %s", highest_score, safe_selector)
            return best_candidate
            
        logger.warning("No heuristic repair met the 0.55 confidence threshold.")
        return None
