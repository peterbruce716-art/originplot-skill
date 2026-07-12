from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable


PlanValidator = Callable[[dict[str, Any], dict[str, Any] | None], dict[str, Any]]
LiveBuilder = Callable[[str, dict[str, Any], Path], dict[str, Any]]


@dataclass(frozen=True)
class BuilderDefinition:
    builder_id: str
    description: str
    figure_ids: tuple[str, ...] = field(default_factory=tuple)
    supports_live: bool = False
    plan_validator: PlanValidator | None = None
    live_builder: LiveBuilder | None = None

    def validate_plan(
        self,
        candidate: dict[str, Any],
        figure_spec: dict[str, Any] | None,
    ) -> dict[str, Any]:
        declared_builder = candidate.get("builder_id")
        if declared_builder and declared_builder != self.builder_id:
            raise ValueError(
                f"candidate builder_id {declared_builder!r} does not match {self.builder_id!r}"
            )
        if self.plan_validator is not None:
            return self.plan_validator(candidate, figure_spec)
        figure = str(candidate.get("figure", ""))
        if self.figure_ids and figure not in self.figure_ids:
            raise ValueError(
                f"candidate figure {figure!r} is not accepted by builder {self.builder_id!r}"
            )
        return {
            "builder_id": self.builder_id,
            "figure": figure,
            "validation": "offline_plan_validated",
        }

    def build_live(
        self,
        figure: str,
        candidate: dict[str, Any],
        output_dir: Path,
    ) -> dict[str, Any]:
        if not self.supports_live or self.live_builder is None:
            return {
                "schema": "originplot.builder_result.v1",
                "status": "failed",
                "error_code": "E440_PLOT_FAMILY_NOT_IMPLEMENTED",
                "message": f"Builder {self.builder_id!r} has no verified live implementation.",
                "pass_eligible": False,
            }
        return self.live_builder(figure, candidate, output_dir)


@dataclass(frozen=True)
class BuilderResult:
    builder_id: str
    status: str
    pass_eligible: bool
    details: dict[str, Any] = field(default_factory=dict)
