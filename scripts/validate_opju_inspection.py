from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

from validate_figurespec_v2 import load_document


def _names(items: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("name")) for item in items if item.get("name")}


def _close(a: Any, b: Any, tol: float) -> bool:
    try:
        return math.isclose(float(a), float(b), abs_tol=tol, rel_tol=0.0)
    except (TypeError, ValueError):
        return False


def _compare_numeric_list(label: str, expected: Any, actual: Any, tol: float, failures: list[str]) -> None:
    if not isinstance(actual, (list, tuple)) or len(actual) != len(expected):
        failures.append(f"{label} missing or length mismatch: expected {expected}, got {actual}")
        return
    for index, (e, a) in enumerate(zip(expected, actual)):
        if not _close(e, a, tol):
            failures.append(f"{label}[{index}] mismatch: expected {e}, got {a}, tol={tol}")


def _find(items: list[dict[str, Any]], *keys: str) -> dict[str, Any] | None:
    wanted = {str(key) for key in keys if key is not None}
    for item in items:
        candidates = {str(item.get("id")), str(item.get("name")), str(item.get("origin_name"))}
        if wanted & candidates:
            return item
    return None


def _style_subset(label: str, expected: dict[str, Any], actual: dict[str, Any], tol: float, failures: list[str]) -> None:
    for key, expected_value in expected.items():
        if key not in actual:
            failures.append(f"{label}.style missing {key}")
        elif isinstance(expected_value, (int, float)):
            if not _close(expected_value, actual.get(key), tol):
                failures.append(f"{label}.style.{key} mismatch: expected {expected_value}, got {actual.get(key)}")
        elif actual.get(key) != expected_value:
            failures.append(f"{label}.style.{key} mismatch: expected {expected_value!r}, got {actual.get(key)!r}")


def validate_inspection(spec: dict[str, Any], inspection: dict[str, Any]) -> dict[str, Any]:
    failures: list[str] = []
    warnings: list[str] = []
    origin = spec.get("origin") or {}
    contracts = spec.get("contracts") or {}
    expected = contracts.get("expected") or {}
    tol = contracts.get("tolerances") or {}
    geometry_tol = float(tol.get("geometry_mm", 0.25))
    coordinate_tol = float(tol.get("coordinate", 1e-4))
    style_tol = float(tol.get("style_numeric", 0.05))
    detailed = bool(contracts.get("require_detailed_inspection"))
    primary_name = contracts.get("primary_graph") or origin.get("primary_graph")

    if inspection.get("open_status") != "ok":
        failures.append("inspection.open_status is not ok")
    if inspection.get("second_export_status") != "ok":
        failures.append("inspection.second_export_status is not ok")

    workbooks = inspection.get("workbooks") or []
    graph_pages = inspection.get("graph_pages") or []
    wb_names = _names(workbooks)
    graph_names = _names(graph_pages)
    for name in expected.get("workbooks", []):
        if name not in wb_names:
            failures.append(f"missing workbook: {name}")
    for name in expected.get("graph_pages", []):
        if name not in graph_names:
            failures.append(f"missing graph page: {name}")

    primary = _find(graph_pages, str(primary_name))
    if primary is None:
        failures.append(f"primary graph not found: {primary_name}")
    else:
        prohibited = contracts.get("prohibited_on_primary") or {}
        if prohibited.get("raster_source_image") and primary.get("raster_source_image_count", 0):
            failures.append("primary graph contains raster source image objects")
        if prohibited.get("unnamed_objects") and primary.get("unnamed_object_count", 0):
            failures.append("primary graph contains unnamed objects")
        if prohibited.get("placeholder_plots") and primary.get("placeholder_plot_count", 0):
            failures.append("primary graph contains placeholder plots")
        if prohibited.get("auto_rescale_after_annotations") and inspection.get("rescale_after_annotations"):
            failures.append("execution trace reports rescale after annotations")

        page_size = (spec.get("page") or {}).get("size_mm")
        if page_size:
            actual_size = primary.get("size_mm")
            if actual_size is None and detailed:
                failures.append("primary graph inspection missing size_mm")
            elif actual_size is not None:
                _compare_numeric_list("primary.size_mm", page_size, actual_size, geometry_tol, failures)

        actual_layers = primary.get("layers") or []
        layer_contracts = expected.get("layers") or {}
        if not detailed:
            for layer_id, layer_contract in layer_contracts.items():
                layer = _find(actual_layers, str(layer_id))
                if layer is None:
                    failures.append(f"missing layer: {layer_id}")
                    continue
                if "plot_count" in layer_contract and len(layer.get("plots", [])) != int(layer_contract["plot_count"]):
                    failures.append(f"layer {layer_id} plot_count mismatch")
                object_names = _names(layer.get("objects", []))
                for obj_name in layer_contract.get("object_names", []):
                    if obj_name not in object_names:
                        failures.append(f"layer {layer_id} missing object: {obj_name}")
            return {
                "status": "pass" if not failures else "fail",
                "failures": failures,
                "warnings": warnings,
                "primary_graph": primary_name,
                "observed": {"workbooks": sorted(wb_names), "graph_pages": sorted(graph_names)},
                "tolerances": {"geometry_mm": geometry_tol, "coordinate": coordinate_tol, "style_numeric": style_tol},
            }
        actual_layers = primary.get("layers") or []
        layer_contracts = expected.get("layers") or {}
        spec_layers = {str(layer.get("id")): layer for layer in spec.get("layers", []) if isinstance(layer, dict)}
        spec_plots = [plot for plot in spec.get("plots", []) if isinstance(plot, dict)]
        spec_annotations = [ann for ann in spec.get("annotations", []) if isinstance(ann, dict)]

        for layer_id, layer_spec in spec_layers.items():
            layer_contract = layer_contracts.get(layer_id) or {}
            layer = _find(actual_layers, layer_id, str(layer_spec.get("origin_name")))
            if layer is None:
                failures.append(f"missing layer: {layer_id}")
                continue
            expected_bbox = layer_contract.get("bbox_mm") or layer_spec.get("position_abs_mm")
            if expected_bbox:
                actual_bbox = layer.get("bbox_mm") or layer.get("position_abs_mm")
                if actual_bbox is None and detailed:
                    failures.append(f"layer {layer_id} inspection missing bbox_mm")
                elif actual_bbox is not None:
                    _compare_numeric_list(f"layer {layer_id}.bbox_mm", expected_bbox, actual_bbox, geometry_tol, failures)

            axes_actual = layer.get("axes") or {}
            for axis_name in ["x", "y"]:
                axis_expected = layer_contract.get("axes", {}).get(axis_name) or layer_spec.get(axis_name) or {}
                axis_actual = axes_actual.get(axis_name)
                if axis_actual is None:
                    if detailed:
                        failures.append(f"layer {layer_id} inspection missing {axis_name} axis")
                    continue
                for key in ["scale", "title"]:
                    if key in axis_expected and axis_actual.get(key) != axis_expected.get(key):
                        failures.append(f"layer {layer_id} {axis_name}.{key} mismatch: expected {axis_expected.get(key)!r}, got {axis_actual.get(key)!r}")
                if isinstance(axis_expected.get("limits"), list):
                    actual_limits = axis_actual.get("limits")
                    if actual_limits is None:
                        failures.append(f"layer {layer_id} {axis_name}.limits missing")
                    else:
                        _compare_numeric_list(f"layer {layer_id}.{axis_name}.limits", axis_expected["limits"], actual_limits, coordinate_tol, failures)

            actual_plots = layer.get("plots") or []
            expected_plots = layer_contract.get("plots")
            if expected_plots is None:
                expected_plots = [plot for plot in spec_plots if plot.get("layer") == layer_id]
                for ann in spec_annotations:
                    if ann.get("layer") == layer_id and ann.get("editable_route") == "data_plot":
                        overlay = dict(ann.get("data_plot") or {})
                        overlay.setdefault("id", (ann.get("origin_object") or {}).get("name") or ann.get("id"))
                        overlay.setdefault("type", overlay.get("plot_type", "line"))
                        expected_plots.append(overlay)
            if "plot_count" in layer_contract and len(actual_plots) != int(layer_contract["plot_count"]):
                failures.append(f"layer {layer_id} plot_count mismatch: expected {layer_contract['plot_count']}, got {len(actual_plots)}")
            for plot_expected in expected_plots:
                plot_id = str(plot_expected.get("id") or plot_expected.get("name"))
                plot_actual = _find(actual_plots, plot_id)
                if plot_actual is None:
                    failures.append(f"layer {layer_id} missing plot: {plot_id}")
                    continue
                for exp_key, act_key in [("type", "type"), ("data_ref", "data_ref"), ("draw_order", "draw_order")]:
                    if plot_expected.get(exp_key) is not None and plot_actual.get(act_key) != plot_expected.get(exp_key):
                        failures.append(f"plot {plot_id} {act_key} mismatch: expected {plot_expected.get(exp_key)!r}, got {plot_actual.get(act_key)!r}")
                if plot_expected.get("map") and plot_actual.get("map") != plot_expected.get("map"):
                    failures.append(f"plot {plot_id} data mapping mismatch")
                if isinstance(plot_expected.get("style"), dict):
                    _style_subset(f"plot {plot_id}", plot_expected["style"], plot_actual.get("style") or {}, style_tol, failures)

            actual_objects = layer.get("objects") or []
            expected_objects = layer_contract.get("objects")
            if expected_objects is None:
                expected_objects = []
                for ann in spec_annotations:
                    if ann.get("layer") == layer_id and ann.get("editable_route", "graph_object") != "data_plot":
                        obj = dict(ann.get("origin_object") or {})
                        obj["id"] = ann.get("id")
                        obj["style"] = ann.get("style") or {}
                        expected_objects.append(obj)
            object_names = _names(actual_objects)
            for obj_name in layer_contract.get("object_names", []):
                if obj_name not in object_names:
                    failures.append(f"layer {layer_id} missing object: {obj_name}")
            for obj_expected in expected_objects:
                obj_name = str(obj_expected.get("name"))
                obj_actual = _find(actual_objects, obj_name, str(obj_expected.get("id")))
                if obj_actual is None:
                    failures.append(f"layer {layer_id} missing object: {obj_name}")
                    continue
                for key in ["kind", "attach_to", "position_units", "z_order", "text"]:
                    if obj_expected.get(key) is not None and obj_actual.get(key) != obj_expected.get(key):
                        failures.append(f"object {obj_name} {key} mismatch: expected {obj_expected.get(key)!r}, got {obj_actual.get(key)!r}")
                if obj_expected.get("coordinates") is not None:
                    actual_coords = obj_actual.get("coordinates")
                    if actual_coords is None:
                        failures.append(f"object {obj_name} coordinates missing")
                    else:
                        _compare_numeric_list(f"object {obj_name}.coordinates", obj_expected["coordinates"], actual_coords, coordinate_tol, failures)
                if isinstance(obj_expected.get("style"), dict):
                    _style_subset(f"object {obj_name}", obj_expected["style"], obj_actual.get("style") or {}, style_tol, failures)

        if detailed and not primary.get("inspection_backend"):
            warnings.append("primary graph inspection_backend was not recorded")

    return {
        "status": "pass" if not failures else "fail",
        "failures": failures,
        "warnings": warnings,
        "primary_graph": primary_name,
        "observed": {"workbooks": sorted(wb_names), "graph_pages": sorted(graph_names)},
        "tolerances": {"geometry_mm": geometry_tol, "coordinate": coordinate_tol, "style_numeric": style_tol},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a clean-session OPJU inspection report against FigureSpec v2/v3.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("inspection", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    spec = load_document(args.spec)
    inspection = json.loads(args.inspection.read_text(encoding="utf-8-sig"))
    result = validate_inspection(spec, inspection)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
