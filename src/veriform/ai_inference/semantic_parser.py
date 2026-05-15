"""Semantic parsing helpers for deterministic token extraction.

This parser is intentionally lightweight and independent from browser automation.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SemanticHints:
    """Normalized semantic tokens extracted from field metadata."""

    tokens: tuple[str, ...]
    raw_text: str


def parse_semantic_hints(*values: str | None) -> SemanticHints:
    """Parse and normalize semantic hints from field label/name/id text."""
    joined = " ".join(value.strip() for value in values if value and value.strip())
    normalized = joined.replace("_", " ").replace("-", " ").lower()
    tokens = tuple(token for token in normalized.split() if token)
    # TODO: plug in locale-aware tokenization in Phase 2.
    return SemanticHints(tokens=tokens, raw_text=joined)
