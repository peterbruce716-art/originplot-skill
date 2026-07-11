from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


def _load_adapter(module_ref: str, config: dict[str, Any]):
    path = Path(module_ref)
    if path.exists():
        spec = importlib.util.spec_from_file_location("originplot_runtime_adapter", path)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load adapter module from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(module_ref)
    if hasattr(module, "create_adapter"):
        return module.create_adapter(config)
    if hasattr(module, "Adapter"):
        return module.Adapter(config)
    raise RuntimeError("adapter module must expose create_adapter(config) or Adapter(config)")


class DryRunAdapter:
    def supports(self, op: str, payload: dict[str, Any]) -> bool:
        return True

    def execute(self, op: str, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {"status": "dry_run", "op": op}

    def close(self) -> None:
        return None


def execute_plan(plan: dict[str, Any], adapter: Any, trace_path: Path | None = None) -> dict[str, Any]:
    context: dict[str, Any] = {"artifacts": {}, "state": {}, "plan_status": plan.get("status")}
    trace: dict[str, Any] = {
        "started_at": datetime.now().isoformat(timespec="seconds"),
        "status": "running",
        "operations": [],
    }
    if plan.get("status") != "ok":
        trace["status"] = "invalid_plan"
        trace["error"] = "plan.status is not ok"
        return trace

    def flush() -> None:
        if trace_path:
            trace_path.parent.mkdir(parents=True, exist_ok=True)
            trace_path.write_text(json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    try:
        for operation in plan.get("operations", []):
            op = str(operation.get("op"))
            record = {
                "seq": operation.get("seq"),
                "stage": operation.get("stage"),
                "op": op,
                "adapter_route": operation.get("adapter_route"),
                "started_at": datetime.now().isoformat(timespec="seconds"),
            }
            trace["operations"].append(record)
            flush()
            supports = getattr(adapter, "supports", None)
            if supports is not None and not bool(supports(op, operation)):
                record["status"] = "unsupported"
                raise RuntimeError(f"adapter does not support operation: {op}")
            result = adapter.execute(op, operation, context)
            if result is None:
                result = {"status": "ok"}
            if not isinstance(result, dict):
                result = {"status": "ok", "value": result}
            record["result"] = result
            record["status"] = result.get("status", "ok")
            record["finished_at"] = datetime.now().isoformat(timespec="seconds")
            if record["status"] in {"failed", "error", "unsupported"}:
                raise RuntimeError(f"operation {op} returned status={record['status']}")
            flush()
        trace["status"] = "ok"
    except Exception as exc:
        trace["status"] = "failed"
        trace["error"] = {"error_class": exc.__class__.__name__, "message": str(exc), "traceback": traceback.format_exc()}
    finally:
        close = getattr(adapter, "close", None)
        if close is not None:
            try:
                close()
            except Exception as exc:
                trace["close_error"] = {"error_class": exc.__class__.__name__, "message": str(exc)}
        trace["finished_at"] = datetime.now().isoformat(timespec="seconds")
        flush()
    return trace


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute a compiled Origin operation plan through a project-local adapter plugin.")
    parser.add_argument("plan", type=Path)
    parser.add_argument("--adapter-module", help="Python module name or .py path exposing create_adapter(config) or Adapter(config).")
    parser.add_argument("--adapter-config", type=Path, help="Optional JSON adapter configuration.")
    parser.add_argument("--trace-out", type=Path, default=Path("execution_trace.json"))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
    config = json.loads(args.adapter_config.read_text(encoding="utf-8-sig")) if args.adapter_config else {}
    if args.dry_run:
        adapter = DryRunAdapter()
    elif args.adapter_module:
        adapter = _load_adapter(args.adapter_module, config)
    else:
        print("ERROR: --adapter-module is required unless --dry-run is used")
        return 2
    trace = execute_plan(plan, adapter, args.trace_out)
    print(json.dumps(trace, ensure_ascii=False, indent=2))
    return 0 if trace.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
