from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

OPERATION_PLAN_SCHEMA = "originplot.operation_plan.v1"


@dataclass(frozen=True)
class OperationPlan:
    figure_id: str
    plot_type: str
    source: dict[str, Any]
    profile: str
    operations: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": OPERATION_PLAN_SCHEMA,
            "figure_id": self.figure_id,
            "plot_type": self.plot_type,
            "source": dict(self.source),
            "profile": self.profile,
            "operations": [dict(item) for item in self.operations],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "OperationPlan":
        if payload.get("schema") != OPERATION_PLAN_SCHEMA:
            raise ValueError(f"unsupported operation plan schema: {payload.get('schema')}")
        return cls(
            figure_id=str(payload.get("figure_id") or "figure"),
            plot_type=str(payload.get("plot_type") or ""),
            source=dict(payload.get("source") or {}),
            profile=str(payload.get("profile") or "standard"),
            operations=tuple(dict(item) for item in payload.get("operations") or []),
            metadata=dict(payload.get("metadata") or {}),
        )
