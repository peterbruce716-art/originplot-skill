from __future__ import annotations

from typing import Any


class UnsupportedOperation(RuntimeError):
    pass


class BaseAdapter:
    route = "base"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}

    def supports(self, operation: dict[str, Any]) -> bool:
        return bool((self.config.get("operations") or {}).get(operation.get("operation_id"), True))

    def execute(self, operation: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        raise UnsupportedOperation(f"{self.route} adapter has no implementation for {operation.get('operation_id')}")

    def close(self) -> None:
        return None
