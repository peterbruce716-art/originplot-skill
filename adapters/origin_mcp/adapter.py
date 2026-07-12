from __future__ import annotations

from typing import Any


class Adapter:
    route = "origin_mcp"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.execution_mode = str(self.config.get("execution_mode") or "live")
        if self.config.get("allow_noop") and self.execution_mode != "test":
            raise RuntimeError("allow_noop is test-only; live MCP execution refuses no-op adapters")

    def supports(self, operation: dict[str, Any]) -> bool:
        return operation.get("adapter_route") == self.route

    def execute(self, operation: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        endpoint = self.config.get("endpoint")
        if not endpoint:
            return {"status": "unsupported", "route": self.route, "operation_id": operation.get("operation_id"), "message": "MCP endpoint is not configured."}
        return {"status": "unsupported", "route": self.route, "operation_id": operation.get("operation_id"), "message": "Wire this adapter to the verified local origin-mcp client before live execution."}


def create_adapter(config: dict[str, Any]) -> Adapter:
    return Adapter(config)
