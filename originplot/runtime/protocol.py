from __future__ import annotations

from pathlib import Path
from typing import Any


WORKER_TASK_SCHEMA = "originplot.origin_worker_task.v2"
WORKER_RESULT_SCHEMA = "originplot.origin_worker_result.v2"


def build_worker_task(
    *,
    profile: dict[str, Any],
    figure_spec: str,
    output_dir: Path,
    operation_plan: dict[str, Any],
    template_decision: dict[str, Any] | None = None,
    source_policy: str = "supplied",
) -> dict[str, Any]:
    return {
        "schema": WORKER_TASK_SCHEMA,
        "profile": profile,
        "figure_spec": figure_spec,
        "output_dir": str(output_dir.resolve()),
        "operation_plan": operation_plan,
        "template_decision": dict(template_decision or {}),
        "source_policy": source_policy,
        "controller_privilege": "standard_user_allowed",
        "worker_privilege": "administrator_required_for_origin",
        "admin_policy": "unchanged_from_v5",
    }
