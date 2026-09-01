"""Capability contracts for builders and adapters.

This module defines the minimal compatibility layer used by v6 execution
contracts. Builders describe what they can emit; adapters describe what they
can execute.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, FrozenSet


@dataclass(frozen=True)
class CapabilitySet:
    """Declared operations supported by a component."""

    name: str
    operations: FrozenSet[str] = field(default_factory=frozenset)

    @classmethod
    def from_iterable(cls, name: str, operations: Iterable[str]) -> "CapabilitySet":
        return cls(name=name, operations=frozenset(operations))

    def supports(self, operation: str) -> bool:
        return operation in self.operations


def validate_capability_subset(
    required: Iterable[str], supported: Iterable[str]
) -> set[str]:
    """Return unsupported operations required by a producer.

    The caller decides whether the returned set should fail execution or CI.
    Keeping this pure makes it usable by runtime checks and offline tests.
    """

    return set(required) - set(supported)
