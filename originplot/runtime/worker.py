from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any, Callable

from originplot.adapters import execute_operation_plan
from originplot.operation_plan import OperationPlan
from originplot.runtime.origin_session import attached_origin, is_administrator
from originplot.runtime.protocol import WORKER_TASK_SCHEMA


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run(
    task_path: Path,
    *,
    op_module: Any | None = None,
    session_factory: Callable[[Any], Any] | None = None,
    admin_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    task = json.loads(task_path.read_text(encoding="utf-8-sig"))
    if task.get("schema") != WORKER_TASK_SCHEMA:
        raise ValueError("unsupported origin worker task schema")
    profile = dict(task.get("profile") or {})
    output_dir = Path(task["output_dir"]).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    if profile.get("name") == "release":
        result = {
            "schema": "originplot.origin_worker_result.v2",
            "profile": "release",
            "command_success": False,
            "overall_status": "failed",
            "error_code": "E440_RELEASE_ROUTE_MISMATCH",
            "message": "AA2195 release evidence remains on the strict benchmark runtime; v6 general release promotion is fail-closed",
        }
    elif not (admin_check or is_administrator)():
        result = {
            "schema": "originplot.origin_worker_result.v2",
            "profile": profile.get("name"),
            "command_success": False,
            "overall_status": "failed",
            "error_code": "E120_ENVIRONMENT_MISMATCH",
            "message": "Origin worker requires an administrator process; controller may remain non-admin",
            "origin_attach_not_attempted": True,
        }
    else:
        try:
            plan = OperationPlan.from_dict(dict(task.get("operation_plan") or {}))
            result = execute_operation_plan(
                plan,
                output_dir,
                op_module=op_module,
                session_factory=session_factory or attached_origin,
                admin_check=admin_check or is_administrator,
            )
            spec_path = Path(str(task.get("figure_spec") or ""))
            destination = output_dir / "figure_spec.json"
            if spec_path.is_file() and spec_path.resolve() != destination.resolve():
                shutil.copyfile(spec_path, destination)
        except Exception as exc:
            result = {
                "schema": "originplot.origin_worker_result.v2",
                "profile": profile.get("name"),
                "command_success": False,
                "overall_status": "failed",
                "error_code": getattr(exc, "code", "E525_ORIGIN_WORKER_FAILED"),
                "message": str(exc),
            }
    _write(output_dir / "verification.json", result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Administrator-only OriginPlot v6 worker protocol endpoint.")
    parser.add_argument("--task", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        result = run(args.task)
    except Exception as exc:
        result = {
            "schema": "originplot.origin_worker_result.v2",
            "command_success": False,
            "overall_status": "failed",
            "error_code": "E525_ORIGIN_WORKER_FAILED",
            "message": str(exc),
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("command_success") else 1


if __name__ == "__main__":
    raise SystemExit(main())
