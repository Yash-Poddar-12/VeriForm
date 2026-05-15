"""Field dependency graph primitives.

Phase 1 keeps this graph lightweight for single-page forms. The interface is
kept extensible for future multi-page and adaptive planning workflows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class FieldDependency:
    """Directed dependency from source field to target field."""

    source_field_id: str
    target_field_id: str
    rule_name: str


class DependencyGraph:
    """Minimal directed graph to hold field dependencies."""

    def __init__(self) -> None:
        self._forward: dict[str, set[str]] = {}
        self._reverse: dict[str, set[str]] = {}

    def add_dependency(self, dependency: FieldDependency) -> None:
        self._forward.setdefault(dependency.source_field_id, set()).add(
            dependency.target_field_id
        )
        self._reverse.setdefault(dependency.target_field_id, set()).add(
            dependency.source_field_id
        )

    def downstream(self, field_id: str) -> tuple[str, ...]:
        """Return sorted dependent fields for *field_id*."""
        return tuple(sorted(self._forward.get(field_id, set())))

    def upstream(self, field_id: str) -> tuple[str, ...]:
        """Return sorted prerequisite fields for *field_id*."""
        return tuple(sorted(self._reverse.get(field_id, set())))

    def iter_edges(self) -> Iterable[tuple[str, str]]:
        """Yield edges as (source, target) pairs in deterministic order."""
        for source in sorted(self._forward):
            for target in sorted(self._forward[source]):
                yield source, target
