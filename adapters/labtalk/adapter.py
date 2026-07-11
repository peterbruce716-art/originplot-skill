from __future__ import annotations

from typing import Any


class Adapter:
    route = "originpro_labtalk"

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.execution_mode = str(self.config.get("execution_mode") or "live")
        if self.config.get("allow_noop") and self.execution_mode != "test":
            raise RuntimeError("allow_noop is test-only; live LabTalk execution refuses no-op adapters")
        self.allow_noop = bool(self.config.get("allow_noop"))

    def supports(self, operation: dict[str, Any]) -> bool:
        return operation.get("adapter_route") == self.route

    def execute(self, operation: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        if self.allow_noop:
            return {"status": "completed", "route": self.route, "operation_id": operation.get("operation_id"), "noop": True}
        return {"status": "unsupported", "route": self.route, "operation_id": operation.get("operation_id"), "message": "Verified LabTalk command config is required."}


def create_adapter(config: dict[str, Any]) -> Adapter:
    return Adapter(config)
