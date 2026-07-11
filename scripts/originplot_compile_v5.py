from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any


FIGURESPEC_SCHEMA = "originplot.figurespec.v5"
COMPILED_IR_SCHEMA = "originplot.compiled_ir.v5"
OPERATION_PLAN_SCHEMA = "originplot.operation_plan.v5"
REGISTRY_SCHEMA = "originplot.operation_registry.v1"


class CompileError(ValueError):
    pass


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def route(origin: dict[str, Any], key: str) -> str:
    routes = origin.get("operation_routes") or {}
    return str(routes.get(key, "unsupported"))


def registry_path() -> Path:
    return Path(__file__).resolve().parents[1] / "operation_registry" / "operation_registry_v1.json"


def load_registry(path: Path | None = None) -> dict[str, Any]:
    payload = read_json(path or registry_path())
    if payload.get("schema") != REGISTRY_SCHEMA:
        raise CompileError(f"operation registry schema must be {REGISTRY_SCHEMA}")
    operations = payload.get("operations")
    if not isinstance(operations, dict):
        raise CompileError("operation registry must contain operations object")
    return operations


def validate_figurespec(spec: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if spec.get("schema") != FIGURESPEC_SCHEMA:
        errors.append(f"schema must be {FIGURESPEC_SCHEMA}")
    for section in ["figure", "runtime", "origin", "page", "contracts"]:
        if not isinstance(spec.get(section), dict):
            errors.append(f"{section} must be an object")
    for section in ["data", "layers", "plots", "annotations"]:
        if section == "annotations" and spec.get(section) is None:
            continue
        if not isinstance(spec.get(section), list):
            errors.append(f"{section} must be a list")
    origin = spec.get("origin") or {}
    for key in ["target_version", "adapter_policy", "primary_graph", "capability_profile"]:
        if not origin.get(key):
            errors.append(f"origin.{key} is required")
    contracts = spec.get("contracts") or {}
    if contracts.get("primary_graph") != origin.get("primary_graph"):
        errors.append("contracts.primary_graph must equal origin.primary_graph")
    runtime = spec.get("runtime") or {}
    for key in ["project_path", "pre_save_export", "post_reopen_export"]:
        if not runtime.get(key):
            errors.append(f"runtime.{key} is required")
    page = spec.get("page") or {}
    size = page.get("size_mm")
    if not (isinstance(size, list) and len(size) == 2 and all(isinstance(value, (int, float)) and value > 0 for value in size)):
        errors.append("page.size_mm must contain two positive numbers")
    data = spec.get("data") if isinstance(spec.get("data"), list) else []
    layers = spec.get("layers") if isinstance(spec.get("layers"), list) else []
    plots = spec.get("plots") if isinstance(spec.get("plots"), list) else []
    data_ids = [item.get("id") for item in data if isinstance(item, dict)]
    layer_ids = [item.get("id") for item in layers if isinstance(item, dict)]
    if len(data_ids) != len(set(data_ids)):
        errors.append("data ids must be unique")
    if len(layer_ids) != len(set(layer_ids)):
        errors.append("layer ids must be unique")
    for layer in layers:
        if not isinstance(layer, dict):
            continue
        for axis in ["x", "y"]:
            limits = (layer.get(axis) or {}).get("limits")
            if limits is not None and not (isinstance(limits, list) and len(limits) == 2):
                errors.append(f"layer {layer.get('id')} {axis}.limits must have length 2")
    for plot in plots:
        if not isinstance(plot, dict):
            continue
        if plot.get("data_ref") not in data_ids:
            errors.append(f"plot {plot.get('id')} references unknown data_ref {plot.get('data_ref')}")
        if plot.get("layer") not in layer_ids:
            errors.append(f"plot {plot.get('id')} references unknown layer {plot.get('layer')}")
    for key, value in (origin.get("operation_routes") or {}).items():
        if str(value) == "unsupported":
            errors.append(f"origin.operation_routes.{key} is unsupported")
    expected = (contracts.get("expected") or {}) if isinstance(contracts.get("expected"), dict) else {}
    if expected.get("graph_pages") and int(expected.get("graph_pages")) != int(page.get("expected_graph_pages", expected.get("graph_pages"))):
        errors.append("page.expected_graph_pages must match contracts.expected.graph_pages when both are present")
    return {"status": "pass" if not errors else "fail", "errors": errors}


def compile_v5(spec: dict[str, Any]) -> dict[str, Any]:
    registry = load_registry()
    validation = validate_figurespec(spec)
    if validation["status"] != "pass":
        return {"status": "invalid_spec", "validation": validation, "compiled_ir": None, "operation_plan": None}

    origin = spec["origin"]
    operations: list[dict[str, Any]] = []
    seq = 0

    def add(worker: str, operation_id: str, route_key: str, **payload: Any) -> None:
        nonlocal seq
        registered = registry.get(operation_id)
        if not registered:
            raise CompileError(f"Unregistered operation: {operation_id}")
        if registered.get("worker") != worker:
            raise CompileError(f"Operation {operation_id} must run in worker {registered.get('worker')}, not {worker}")
        adapter_route = route(origin, route_key)
        if adapter_route == "unsupported":
            raise CompileError(f"Unsupported adapter route for {operation_id}: origin.operation_routes.{route_key}")
        seq += 1
        operations.append(
            {
                "seq": seq,
                "worker": worker,
                "operation_id": operation_id,
                "adapter_route": adapter_route,
                "payload": payload,
            }
        )

    add("build", "session.start_clean", "session", target_version=origin["target_version"])
    add("build", "session.assert_capabilities", "session", capability_profile=origin["capability_profile"])
    for data in spec.get("data", []):
        data_kind = str(data.get("kind", "worksheet")).lower()
        if data_kind in {"matrix", "xyz_matrix"}:
            add("build", "matrix.create", "data", data_id=data.get("id"), origin_name=data.get("origin_name"))
            add("build", "matrix.import", "data", data_id=data.get("id"), source=data.get("source"), roles=data.get("roles"))
            if data_kind == "xyz_matrix" or data.get("gridding"):
                add("build", "matrix.xyz_gridding", "data", data_id=data.get("id"), gridding=data.get("gridding"))
        else:
            add("build", "workbook.create", "data", data_id=data.get("id"), origin_name=data.get("origin_name"))
            add("build", "worksheet.import", "data", data_id=data.get("id"), source=data.get("source"), roles=data.get("roles"))
    add("build", "graph.create", "graph", graph_name=origin["primary_graph"], seed_template=origin.get("seed_template"))
    add("build", "page.configure", "graph", page=spec.get("page"), panel_layout=(spec.get("page") or {}).get("panel_layout"))
    for layer in spec.get("layers", []):
        add("build", "layer.add", "graph", layer=layer)
        add("build", "layer.geometry.apply", "graph", layer_id=layer.get("id"), geometry=layer.get("position_abs_mm") or layer.get("bbox"))
        add("build", "layer.configure", "graph", layer=layer)
        if layer.get("link_axes"):
            add("build", "layer.link_axes", "graph", layer_id=layer.get("id"), link_axes=layer.get("link_axes"))
    for plot in spec.get("plots", []):
        plot_type = str(plot.get("type", "line")).lower()
        op_id = "plot.add.line" if plot_type == "line" else f"plot.add.{plot_type}"
        add("build", op_id, "plot", plot=plot)
        if plot_type in {"stacked_column", "grouped_stacked_column"}:
            add("build", "plot.stack.configure", "plot", plot_id=plot.get("id"), stack=plot.get("stack"))
        if plot_type in {"column", "stacked_column", "grouped_stacked_column"}:
            add("build", "plot.group.configure", "plot", plot_id=plot.get("id"), group=plot.get("group"))
            add("build", "plot.gap.configure", "plot", plot_id=plot.get("id"), gap=plot.get("gap"))
        if plot_type == "contour":
            add("build", "contour.fill.configure", "style", plot_id=plot.get("id"), fill=plot.get("fill"))
            add("build", "contour.lines.configure", "style", plot_id=plot.get("id"), lines=plot.get("lines"))
            add("build", "contour.labels.configure", "style", plot_id=plot.get("id"), labels=plot.get("labels"))
            add("build", "colormap.discrete.configure", "style", plot_id=plot.get("id"), colormap=plot.get("colormap"))
            add("build", "colorbar.create", "object", plot_id=plot.get("id"), colorbar=plot.get("colorbar"))
            add("build", "colorbar.configure", "object", plot_id=plot.get("id"), colorbar=plot.get("colorbar"))
        add("build", "plot.style.apply", "style", plot_id=plot.get("id"), style=plot.get("style"))
    for layer in spec.get("layers", []):
        add("build", "axis.configure", "axis", layer_id=layer.get("id"), x=layer.get("x"), y=layer.get("y"))
        if (layer.get("x") or {}).get("scale") == "category" or (layer.get("y") or {}).get("scale") == "category":
            add("build", "category_axis.configure", "axis", layer_id=layer.get("id"), x=layer.get("x"), y=layer.get("y"))
    add("build", "axis.verify_final", "axis", graph_name=origin["primary_graph"])
    for annotation in spec.get("annotations", []):
        kind = str(annotation.get("kind") or annotation.get("origin_object", {}).get("kind") or "create").lower()
        object_map = {
            "text": "object.text.create",
            "line": "object.line.create",
            "arrow": "object.arrow.create",
            "rectangle": "object.rectangle.create",
            "ellipse": "object.ellipse.create",
            "ellipse_text": "object.ellipse.create",
            "group": "object.group.create",
            "legend": "legend.create",
        }
        add("build", object_map.get(kind, "object.create"), "object", annotation=annotation)
        if annotation.get("style"):
            add("build", "object.style.apply", "style", object_id=annotation.get("id"), style=annotation.get("style"))
    add("build", "graph.export.presave", "export", path=(spec.get("runtime") or {}).get("pre_save_export"))
    add("build", "project.save", "save", project_path=(spec.get("runtime") or {}).get("project_path"))
    add("build", "session.release", "session")
    add(
        "inspect",
        "project.reopen.clean",
        "reopen",
        project_path=(spec.get("runtime") or {}).get("project_path"),
        read_only=False,
        verify_same_path_save=True,
    )
    add("inspect", "project.inspect", "inspect", contracts=spec.get("contracts"))
    for layer in spec.get("layers", []):
        add("inspect", "layer.geometry.verify", "inspect", layer_id=layer.get("id"), geometry=layer.get("position_abs_mm") or layer.get("bbox"))
    for annotation in spec.get("annotations", []):
        add("inspect", "object.geometry.verify", "inspect", object_id=annotation.get("id"), expected=annotation.get("origin_object") or annotation)
    add("inspect", "graph.export.postreopen", "inspect", path=(spec.get("runtime") or {}).get("post_reopen_export"))
    add("qa", "qa.structure.compare", "qa", contracts=spec.get("contracts"))
    add("qa", "qa.serialization.compare", "qa")
    add("qa", "qa.image.compare", "qa")
    if spec.get("benchmark"):
        add("qa", "qa.semantic_benchmark", "qa", benchmark=spec.get("benchmark"), required_objects=spec.get("required_objects"), rois=spec.get("rois"))
        add("qa", "qa.deviation_ledger.generate", "qa", benchmark=spec.get("benchmark"))
    add("qa", "manifest.finalize", "qa")

    runtime = spec.get("runtime") or {}
    base = Path.cwd()
    operation_ids = [op["operation_id"] for op in operations]
    compiled_ir = {
        "schema": COMPILED_IR_SCHEMA,
        "compiled_at": datetime.now().isoformat(timespec="seconds"),
        "resolved_environment": {
            "origin_version": origin["target_version"],
            "capability_profile": origin["capability_profile"],
        },
        "resources": {
            "project_path": str((base / str(runtime.get("project_path"))).resolve()),
            "pre_save_export": str((base / str(runtime.get("pre_save_export"))).resolve()),
            "post_reopen_export": str((base / str(runtime.get("post_reopen_export"))).resolve()),
        },
        "resolved_data": spec.get("data", []),
        "resolved_layers": spec.get("layers", []),
        "resolved_plots": spec.get("plots", []),
        "resolved_annotations": spec.get("annotations", []),
        "resolved_required_objects": spec.get("required_objects", []),
        "resolved_rois": spec.get("rois", []),
        "benchmark": spec.get("benchmark", {}),
        "contracts": spec.get("contracts", {}),
        "operation_ids": operation_ids,
    }
    operation_plan = {
        "schema": OPERATION_PLAN_SCHEMA,
        "status": "ok",
        "compiled_ir_schema": COMPILED_IR_SCHEMA,
        "environment_contract": {
            "origin_version": origin["target_version"],
            "capability_profile": origin["capability_profile"],
            "doctor_fingerprint": origin.get("doctor_fingerprint", ""),
            "capability_fingerprint": origin.get("capability_fingerprint", ""),
            "adapter_bundle_hash": origin.get("adapter_bundle_hash", ""),
        },
        "operations": operations,
    }
    return {"status": "ok", "validation": validation, "compiled_ir": compiled_ir, "operation_plan": operation_plan}


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile originplot.figurespec.v5 into compiled IR and operation plan v5.")
    parser.add_argument("figurespec", type=Path)
    parser.add_argument("--compiled-ir-out", required=True, type=Path)
    parser.add_argument("--operation-plan-out", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        result = compile_v5(read_json(args.figurespec))
    except CompileError as exc:
        result = {"status": "compile_error", "validation": {"status": "fail", "errors": [str(exc)]}, "compiled_ir": None, "operation_plan": None}
    if result["status"] == "ok":
        write_json(args.compiled_ir_out, result["compiled_ir"])
        write_json(args.operation_plan_out, result["operation_plan"])
    if args.json_out:
        write_json(args.json_out, result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
