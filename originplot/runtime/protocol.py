from __future__ import annotations

from pathlib import Path
from typing import Any


WORKER_TASK_SCHEMA = "originplot.origin_worker_task.v1"
WORKER_RESULT_SCHEMA = "originplot.origin_worker_result.v1"


def build_worker_task(
    *,
    profile: dict[str, Any],
    figure_spec: str | None,
    candidate: str | None,
    builder: str | None,
    figure: str | None,
    output_dir: Path,
    template_decision: dict[str, Any],
    data_payload: dict[str, Any] | None = None,
    source_policy: str = "supplied",
) -> dict[str, Any]:
    return {
        "schema": WORKER_TASK_SCHEMA,
        "profile": profile,
        "figure_spec": figure_spec,
        "candidate": candidate,
        "builder": builder,
        "figure": figure,
        "output_dir": str(output_dir.resolve()),
        "template_decision": template_decision,
        "data_payload": data_payload,
        "source_policy": source_policy,
        "controller_privilege": "standard_user_allowed",
        "worker_privilege": "administrator_required_for_origin",
    }
