"""Typed primitives for future OperationPlan v6 schema.

This module starts the migration away from unvalidated dictionaries while
keeping runtime integration incremental.
"""

from dataclasses import dataclass, field
from typing import Any

from .operations import is_supported_operation


@dataclass(frozen=True)
class Operation:
    name: str
    version: int = 1
    payload: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not is_supported_operation(self.name):
            raise ValueError(f"unsupported operation: {self.name}")


@dataclass(frozen=True)
class OperationPlan:
    schema_version: str
    builder: str
    operations: list[Operation]
    source_hash: str = ""
    figure_hash: str = ""

    def validate(self) -> None:
        for operation in self.operations:
            operation.validate()
