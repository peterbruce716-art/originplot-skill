from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
import traceback
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "schemas"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.schema_utils import SchemaValidationError, read_json as schema_read_json, validate_json_schema  # noqa: E402


OPERATION_PLAN_SCHEMA = "originplot.operation_plan.v5"
CAPABILITIES_SCHEMA = "originplot.capabilities.v5"
RUN_MANIFEST_SCHEMA = "originplot.run_manifest.v5"
SUCCESS_STATUSES = {"ok", "pass", "completed"}
ADAPTER_MODULE_ALLOWLIST = {
    "originpro": "adapters/originpro/adapter.py",
    "inspection": "adapters/inspection/adapter.py",
    "evidence_qa": "adapters/evidence_qa/adapter.py",
    "originpro_labtalk": "adapters/labtalk/adapter.py",
    "origin_mcp": "adapters/origin_mcp/adapter.py",
}

WORKER_ERROR_CODES = {
    "build": "E220_BUILD_FAILED",
    "inspect": "E310_REOPEN_FAILED",
    "qa_structure": "E400_STRUCTURE_MISMATCH",
    "qa_serialization": "E410_SERIALIZATION_DRIFT",
    "qa_visual": "E420_VISUAL_MISMATCH",
}

ERROR_CODES = {
    "E100_SCHEMA_INVALID": "schema or required v5 document field is invalid",
    "E110_CAPABILITY_MISSING": "operation capability is missing or unverified",
    "E120_ENVIRONMENT_MISMATCH": "capability was verified for a different environment",
    "E130_DOCTOR_FAILED": "doctor did not pass for this environment",
    "E210_OPERATION_UNSUPPORTED": "adapter route does not support the operation",
    "E220_BUILD_FAILED": "build worker or adapter operation failed",
    "E310_REOPEN_FAILED": "inspect worker could not reopen OPJU",
    "E400_STRUCTURE_MISMATCH": "reopened OPJU structure differs from contract",
    "E410_SERIALIZATION_DRIFT": "pre-save and post-reopen exports differ unexpectedly",
    "E420_VISUAL_MISMATCH": "Origin-rendered export does not match the source benchmark",
    "E500_PATCH_REJECTED": "candidate patch violates bounds or schema",
    "E510_NO_IMPROVEMENT": "candidate rebuild did not improve the score",
}


class OriginplotV5Error(RuntimeError):
    def __init__(self, code: str, message: str, details: Any | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_optional_json(path: Path) -> dict[str, Any]:
    if path.exists():
        return read_json(path)
    return {}


def require_schema(doc: dict[str, Any], expected: str, label: str) -> None:
    if doc.get("schema") != expected:
        raise OriginplotV5Error("E100_SCHEMA_INVALID", f"{label}.schema must be {expected}", {"actual": doc.get("schema")})
    schema_file = {
        OPERATION_PLAN_SCHEMA: "operation-plan-v5.schema.json",
        CAPABILITIES_SCHEMA: "capabilities-v5.schema.json",
        RUN_MANIFEST_SCHEMA: "run-manifest-v5.schema.json",
        "originplot.artifacts.v1": "artifacts-v1.schema.json",
        "originplot.inspection.v5": "inspection-v5.schema.json",
        "originplot.qa_report.v1": "qa-report-v1.schema.json",
    }.get(expected)
    if schema_file:
        try:
            validate_json_schema(doc, schema_read_json(SCHEMA_DIR / schema_file), label=label)
        except SchemaValidationError as exc:
            raise OriginplotV5Error("E100_SCHEMA_INVALID", f"{label} failed JSON Schema validation", {"error": str(exc)}) from exc


def operation_list(plan: dict[str, Any]) -> list[dict[str, Any]]:
    require_schema(plan, OPERATION_PLAN_SCHEMA, "operation_plan")
    ops = plan.get("operations")
    if not isinstance(ops, list):
        raise OriginplotV5Error("E100_SCHEMA_INVALID", "operation_plan.operations must be a list")
    normalized: list[dict[str, Any]] = []
    for index, operation in enumerate(ops, start=1):
        if not isinstance(operation, dict):
            raise OriginplotV5Error("E100_SCHEMA_INVALID", f"operation #{index} must be an object")
        for key in ["operation_id", "adapter_route", "worker"]:
            if not operation.get(key):
                raise OriginplotV5Error("E100_SCHEMA_INVALID", f"operation #{index} requires {key}")
        normalized.append({**operation, "seq": int(operation.get("seq", index))})
    return normalized


def overall_status(manifest: dict[str, Any]) -> str:
    required = {
        "preflight_status": "pass",
        "build_status": "pass",
        "round_trip_status": "pass",
        "structure_status": "pass",
        "serialization_status": "pass",
        "visual_status": "pass",
    }
    if any(str(manifest.get(key, "")).startswith("failed") for key in required):
        return "failed"
    return "pass" if all(manifest.get(key) == value for key, value in required.items()) else "incomplete"


def base_manifest() -> dict[str, Any]:
    manifest = {
        "schema": RUN_MANIFEST_SCHEMA,
        "created_at": now(),
        "preflight_status": "not_run",
        "build_status": "not_run",
        "round_trip_status": "not_run",
        "structure_status": "not_run",
        "serialization_status": "not_run",
        "visual_status": "not_run",
        "overall_status": "incomplete",
        "error_codes": ERROR_CODES,
    }
    return manifest


@dataclass
class CapabilityRegistry:
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        require_schema(self.payload, CAPABILITIES_SCHEMA, "capabilities")

    def adapters(self) -> dict[str, Any]:
        adapters = self.payload.get("adapters") or {}
        return adapters if isinstance(adapters, dict) else {}

    def check_operation(self, operation: dict[str, Any]) -> dict[str, Any]:
        route = str(operation["adapter_route"])
        operation_id = str(operation["operation_id"])
        adapters = self.adapters()
        route_caps = adapters.get(route)
        if not isinstance(route_caps, dict):
            return {"status": "missing", "code": "E110_CAPABILITY_MISSING", "adapter_route": route, "operation_id": operation_id}
        operations = route_caps.get("operations") or {}
        capability = operations.get(operation_id)
        if not isinstance(capability, dict):
            return {"status": "missing", "code": "E110_CAPABILITY_MISSING", "adapter_route": route, "operation_id": operation_id}
        if capability.get("verified") is not True:
            return {"status": "unverified", "code": "E110_CAPABILITY_MISSING", "adapter_route": route, "operation_id": operation_id}
        required_origin = operation.get("requires_origin_version")
        verified_origin = capability.get("origin_version") or route_caps.get("origin_version")
        if required_origin and verified_origin and str(required_origin) != str(verified_origin):
            return {"status": "environment_mismatch", "code": "E120_ENVIRONMENT_MISMATCH", "adapter_route": route, "operation_id": operation_id}
        return {"status": "ok", "adapter_route": route, "operation_id": operation_id}

    def coverage_report(self, operations: list[dict[str, Any]]) -> dict[str, Any]:
        checks = [self.check_operation(operation) for operation in operations]
        failures = [item for item in checks if item["status"] != "ok"]
        return {
            "status": "pass" if not failures else "failed",
            "checks": checks,
            "failures": failures,
        }


def environment_report(plan: dict[str, Any], capabilities: dict[str, Any]) -> dict[str, Any]:
    contract = plan.get("environment_contract") or {}
    cap_env = capabilities.get("environment") or {}
    failures: list[dict[str, Any]] = []
    expected_origin = str(contract.get("origin_version") or "")
    actual_origin = str(cap_env.get("origin_version") or "")
    if expected_origin and actual_origin and expected_origin != actual_origin:
        failures.append({"field": "origin_version", "expected": expected_origin, "actual": actual_origin})
    expected_fingerprint = str(contract.get("capability_fingerprint") or "")
    actual_fingerprint = str(cap_env.get("fingerprint") or "")
    if expected_fingerprint and actual_fingerprint and expected_fingerprint != actual_fingerprint:
        failures.append({"field": "capability_fingerprint", "expected": expected_fingerprint, "actual": actual_fingerprint})
    return {
        "status": "pass" if not failures else "failed",
        "failures": failures,
        "contract": contract,
        "capability_environment": cap_env,
    }


class DryRunAdapter:
    def __init__(self, route: str) -> None:
        self.route = route

    def supports(self, operation: dict[str, Any]) -> bool:
        return True

    def execute(self, operation: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        return {
            "status": "completed",
            "adapter_route": self.route,
            "operation_id": operation.get("operation_id"),
            "dry_run": True,
            "worker": operation.get("worker"),
        }

    def close(self) -> None:
        return None


def assert_adapter_module_allowed(route: str, module_ref: str) -> None:
    expected = ADAPTER_MODULE_ALLOWLIST.get(route)
    if expected is None:
        raise OriginplotV5Error("E210_OPERATION_UNSUPPORTED", f"adapter route {route} is not in the runtime whitelist")
    normalized = module_ref.replace("\\", "/")
    expected_path = (ROOT / expected).resolve()
    if normalized == expected:
        return
    candidate = Path(module_ref)
    if candidate.is_absolute() and candidate.resolve() == expected_path:
        return
    raise OriginplotV5Error("E210_OPERATION_UNSUPPORTED", f"adapter module for {route} is not whitelisted", {"module": module_ref, "expected": expected})


def load_adapter(route: str, module_ref: str, config: dict[str, Any]) -> Any:
    assert_adapter_module_allowed(route, module_ref)
    path = Path(module_ref)
    if not path.is_absolute() and path.exists() is False:
        path = ROOT / path
    if path.exists():
        spec = importlib.util.spec_from_file_location("originplot_v5_adapter", path)
        if spec is None or spec.loader is None:
            raise OriginplotV5Error("E210_OPERATION_UNSUPPORTED", f"cannot load adapter from {path}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        module = importlib.import_module(module_ref)
    if hasattr(module, "create_adapter"):
        return module.create_adapter(config)
    if hasattr(module, "Adapter"):
        return module.Adapter(config)
    raise OriginplotV5Error("E210_OPERATION_UNSUPPORTED", "adapter must expose create_adapter(config) or Adapter(config)")


def build_adapters(capabilities: CapabilityRegistry, *, dry_run: bool, adapter_modules: dict[str, str], adapter_configs: dict[str, Any], routes: set[str] | None = None) -> dict[str, Any]:
    adapters: dict[str, Any] = {}
    allowed_routes = routes or set(capabilities.adapters())
    for route in allowed_routes:
        if dry_run:
            adapters[route] = DryRunAdapter(route)
            continue
        module_ref = adapter_modules.get(route) or (capabilities.adapters().get(route) or {}).get("module")
        if not module_ref:
            raise OriginplotV5Error("E210_OPERATION_UNSUPPORTED", f"no adapter module configured for {route}")
        adapters[route] = load_adapter(route, str(module_ref), dict(adapter_configs.get(route) or {}))
    return adapters


def execute_operations(operations: list[dict[str, Any]], adapters: dict[str, Any], *, workers: set[str] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    context = context or {"artifacts": {}, "state": {}}
    trace: list[dict[str, Any]] = []
    for operation in operations:
        if workers and operation.get("worker") not in workers:
            continue
        route = str(operation["adapter_route"])
        adapter = adapters.get(route)
        if adapter is None:
            raise OriginplotV5Error("E210_OPERATION_UNSUPPORTED", f"unknown adapter route {route}", operation)
        record = {
            "seq": operation.get("seq"),
            "worker": operation.get("worker"),
            "operation_id": operation.get("operation_id"),
            "adapter_route": route,
            "started_at": now(),
        }
        try:
            supports = getattr(adapter, "supports", None)
            if supports is not None and not bool(supports(operation)):
                raise OriginplotV5Error("E210_OPERATION_UNSUPPORTED", f"adapter {route} does not support {operation.get('operation_id')}", operation)
            result = adapter.execute(operation, context)
            if not isinstance(result, dict):
                result = {"status": "ok", "value": result}
            status = str(result.get("status", "ok"))
            if status not in SUCCESS_STATUSES:
                details = {**result, **operation}
                error_code = WORKER_ERROR_CODES.get(str(operation.get("worker")), "E220_BUILD_FAILED")
                raise OriginplotV5Error(error_code, f"{operation['operation_id']} returned {status}", details)
            record["status"] = status
            record["result"] = result
        except OriginplotV5Error as exc:
            record["status"] = "failed"
            record["error_code"] = exc.code
            record["error"] = str(exc)
            record["failed_worker"] = operation.get("worker")
            record["failed_operation_id"] = operation.get("operation_id")
            record["failed_adapter_route"] = route
            trace.append(record)
            raise
        finally:
            record["finished_at"] = now()
        trace.append(record)
    return {"status": "pass", "trace": trace, "context": context}


def preflight(plan: dict[str, Any], capabilities: dict[str, Any]) -> dict[str, Any]:
    operations = operation_list(plan)
    registry = CapabilityRegistry(capabilities)
    report = registry.coverage_report(operations)
    env_report = environment_report(plan, capabilities)
    manifest = base_manifest()
    manifest["preflight_status"] = "pass" if report["status"] == "pass" and env_report["status"] == "pass" else "failed"
    manifest["capability_report"] = report
    manifest["environment_report"] = env_report
    manifest["operation_plan_schema"] = plan.get("schema")
    manifest["overall_status"] = overall_status(manifest)
    if report["status"] != "pass":
        manifest["error_code"] = "E110_CAPABILITY_MISSING"
    elif env_report["status"] != "pass":
        manifest["error_code"] = "E120_ENVIRONMENT_MISMATCH"
    return manifest


def file_ok(record: dict[str, Any], *, min_size: int = 512) -> bool:
    return bool(record.get("exists")) and int(record.get("size_bytes") or 0) >= min_size


def image_dimensions(path: str | Path) -> tuple[int, int] | None:
    try:
        from PIL import Image

        with Image.open(path) as image:
            return image.size
    except Exception:
        return None


def apply_evidence_gates(manifest: dict[str, Any], artifacts: dict[str, Any], *, workers: set[str] | None) -> None:
    require_schema(artifacts, "originplot.artifacts.v1", "artifact_manifest")
    active_workers = workers or {"build", "inspect", "qa"}
    if "build" in active_workers:
        project_ok = file_ok(artifacts.get("project") or {}, min_size=1024)
        pre_export_ok = file_ok(artifacts.get("pre_save_export") or {}, min_size=512)
        released = bool((artifacts.get("origin_session") or {}).get("released"))
        manifest["build_status"] = "pass" if project_ok and pre_export_ok and released else "failed"
        if manifest["build_status"] == "failed":
            manifest.setdefault("error_code", WORKER_ERROR_CODES["build"])
    if "inspect" in active_workers:
        inspection_record = artifacts.get("inspection") or {}
        post_export = artifacts.get("post_reopen_export") or {}
        inspection_payload = read_optional_json(Path(str(inspection_record.get("path") or ""))) if inspection_record.get("path") else {}
        if inspection_payload:
            require_schema(inspection_payload, "originplot.inspection.v5", "inspection")
        inspect_ok = file_ok(inspection_record, min_size=128) and inspection_payload.get("status") == "pass"
        post_ok = file_ok(post_export, min_size=512)
        manifest["round_trip_status"] = "pass" if inspect_ok and post_ok else "failed"
        manifest["structure_status"] = "pass" if inspect_ok else "failed"
        if manifest["round_trip_status"] == "failed":
            manifest.setdefault("error_code", WORKER_ERROR_CODES["inspect"])
        elif manifest["structure_status"] == "failed":
            manifest.setdefault("error_code", WORKER_ERROR_CODES["qa_structure"])
    if "qa" in active_workers:
        qa_record = artifacts.get("qa_report") or {}
        qa_payload = read_optional_json(Path(str(qa_record.get("path") or ""))) if qa_record.get("path") else {}
        if qa_payload:
            require_schema(qa_payload, "originplot.qa_report.v1", "qa_report")
        checks = qa_payload.get("checks") or []
        structure_ok = any(item.get("operation_id") == "qa.structure.compare" and item.get("status") == "completed" for item in checks)
        serialization_ok = any(item.get("operation_id") == "qa.serialization.compare" and item.get("status") == "completed" for item in checks)
        visual_ok = any(item.get("operation_id") == "qa.image.compare" and item.get("status") == "completed" for item in checks)
        if manifest.get("structure_status") in {"not_run", None}:
            manifest["structure_status"] = "pass" if structure_ok else "failed"
        manifest["serialization_status"] = "pass" if serialization_ok else "failed"
        manifest["visual_status"] = "pass" if visual_ok else "failed"
        if manifest["serialization_status"] == "failed":
            manifest.setdefault("error_code", WORKER_ERROR_CODES["qa_serialization"])
        elif manifest["visual_status"] == "failed":
            manifest.setdefault("error_code", WORKER_ERROR_CODES["qa_visual"])


def run(plan: dict[str, Any], capabilities: dict[str, Any], *, dry_run: bool, adapter_modules: dict[str, str], adapter_configs: dict[str, Any], workers: set[str] | None = None, run_dir: Path | None = None, artifact_manifest: Path | None = None, workspace: Path | None = None, run_id: str | None = None) -> dict[str, Any]:
    operations = operation_list(plan)
    registry = CapabilityRegistry(capabilities)
    capability_report = registry.coverage_report(operations)
    env_report = environment_report(plan, capabilities)
    manifest = base_manifest()
    manifest["execution_mode"] = "dry_run" if dry_run else "live"
    manifest["capability_report"] = capability_report
    manifest["environment_report"] = env_report
    manifest["operation_plan_schema"] = plan.get("schema")
    if capability_report["status"] != "pass":
        manifest["preflight_status"] = "failed"
        manifest["error_code"] = "E110_CAPABILITY_MISSING"
        manifest["overall_status"] = overall_status(manifest)
        return manifest
    if env_report["status"] != "pass":
        manifest["preflight_status"] = "failed"
        manifest["error_code"] = "E120_ENVIRONMENT_MISMATCH"
        manifest["overall_status"] = overall_status(manifest)
        return manifest
    manifest["preflight_status"] = "pass"
    selected_routes = {str(operation["adapter_route"]) for operation in operations if not workers or operation.get("worker") in workers}
    adapters = build_adapters(registry, dry_run=dry_run, adapter_modules=adapter_modules, adapter_configs=adapter_configs, routes=selected_routes)
    run_dir = (run_dir or Path("outputs/originplot_live_run")).resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    artifact_manifest = (artifact_manifest or run_dir / "run_artifacts.json").resolve()
    context = {
        "artifacts": {},
        "state": {},
        "run_dir": str(run_dir),
        "artifact_manifest": str(artifact_manifest),
        "workspace": str((workspace or Path.cwd()).resolve()),
        "run_id": run_id or run_dir.name,
    }
    try:
        execution = execute_operations(operations, adapters, workers=workers, context=context)
        manifest["execution_trace"] = execution["trace"]
        manifest["artifact_manifest"] = str(artifact_manifest)
        if dry_run:
            manifest["simulation_status"] = "pass"
        else:
            apply_evidence_gates(manifest, read_optional_json(artifact_manifest), workers=workers)
    except OriginplotV5Error as exc:
        manifest["error_code"] = exc.code
        manifest["error"] = str(exc)
        manifest["details"] = exc.details
        details = exc.details if isinstance(exc.details, dict) else {}
        manifest["failed_worker"] = details.get("worker")
        manifest["failed_operation_id"] = details.get("operation_id")
        manifest["failed_adapter_route"] = details.get("adapter_route")
        if exc.code in {"E310_REOPEN_FAILED", "E400_STRUCTURE_MISMATCH"} or details.get("worker") == "inspect":
            manifest["round_trip_status"] = "failed"
            manifest["structure_status"] = "failed"
        elif details.get("worker") == "qa":
            manifest["serialization_status"] = "failed"
            manifest["visual_status"] = "failed"
        else:
            manifest["build_status"] = "failed"
    finally:
        for adapter in adapters.values():
            close = getattr(adapter, "close", None)
            if close:
                close()
    manifest["overall_status"] = overall_status(manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="OriginPlot v5 runtime closure controller.")
    sub = parser.add_subparsers(dest="command", required=True)
    p_pre = sub.add_parser("preflight")
    p_pre.add_argument("--operation-plan", required=True, type=Path)
    p_pre.add_argument("--capabilities", required=True, type=Path)
    p_pre.add_argument("--manifest-out", type=Path)
    p_run = sub.add_parser("run")
    p_run.add_argument("--operation-plan", required=True, type=Path)
    p_run.add_argument("--capabilities", required=True, type=Path)
    p_run.add_argument("--manifest-out", type=Path)
    p_run.add_argument("--dry-run", action="store_true")
    p_run.add_argument("--adapter-modules", type=Path, help="JSON mapping route to whitelisted module.")
    p_run.add_argument("--adapter-configs", type=Path, help="JSON mapping route to adapter config.")
    p_run.add_argument("--run-dir", type=Path)
    p_run.add_argument("--artifact-manifest", type=Path)
    p_run.add_argument("--workspace", type=Path)
    p_run.add_argument("--run-id")
    p_run.add_argument("--workers", nargs="*", choices=["build", "inspect", "qa"])
    p_codes = sub.add_parser("error-codes")
    args = parser.parse_args()

    if args.command == "error-codes":
        result = {"schema": "originplot.error_codes.v5", "error_codes": ERROR_CODES}
    elif args.command == "preflight":
        result = preflight(read_json(args.operation_plan), read_json(args.capabilities))
    else:
        adapter_modules = read_json(args.adapter_modules) if args.adapter_modules else {}
        adapter_configs = read_json(args.adapter_configs) if args.adapter_configs else {}
        result = run(
            read_json(args.operation_plan),
            read_json(args.capabilities),
            dry_run=bool(args.dry_run),
            adapter_modules={str(k): str(v) for k, v in adapter_modules.items()},
            adapter_configs=adapter_configs,
            workers=set(args.workers) if args.workers else None,
            run_dir=args.run_dir,
            artifact_manifest=args.artifact_manifest,
            workspace=args.workspace,
            run_id=args.run_id,
        )

    payload = json.dumps(result, ensure_ascii=False, indent=2)
    manifest_out = getattr(args, "manifest_out", None)
    if manifest_out:
        write_json(manifest_out, result)
    print(payload)
    return 0 if result.get("overall_status") in {"pass", "incomplete"} or args.command == "error-codes" else 2


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except OriginplotV5Error as exc:
        print(json.dumps({"schema": RUN_MANIFEST_SCHEMA, "overall_status": "failed", "error_code": exc.code, "error": str(exc), "details": exc.details}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
    except Exception as exc:
        print(json.dumps({"schema": RUN_MANIFEST_SCHEMA, "overall_status": "failed", "error_code": "E220_BUILD_FAILED", "error": str(exc), "traceback": traceback.format_exc()}, ensure_ascii=False, indent=2))
        raise SystemExit(2)
