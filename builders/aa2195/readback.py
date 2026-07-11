from __future__ import annotations

from collections import Counter
import math
import re
from typing import Any

from adapters.inspection.adapter import inspect_graph_objects, inspect_layer_plots

from .common_origin_utils import page_name


AXIS_PROPERTIES = {
    "x.showAxes": "layer.x.showAxes",
    "y.showAxes": "layer.y.showAxes",
    "x.showLabels": "layer.x.showLabels",
    "y.showLabels": "layer.y.showLabels",
    "x.ticks": "layer.x.ticks",
    "y.ticks": "layer.y.ticks",
    "x.arrow.show": "layer.x.arrow.show",
    "y.arrow.show": "layer.y.arrow.show",
    "y.type": "layer.y.type",
    "y.minorTicks": "layer.y.minorTicks",
    "y_title_rotation": "yl.rotate",
}


def inspect_axis_state(op: Any, page: Any, layer: Any) -> dict[str, Any]:
    values: dict[str, int] = {}
    errors: dict[str, str] = {}
    try:
        page.activate()
        layer.activate()
    except Exception as exc:
        errors["activate"] = f"{exc.__class__.__name__}: {exc}"
    for prop, expression in AXIS_PROPERTIES.items():
        try:
            values[prop] = int(op.lt_int(expression))
        except Exception as exc:
            errors[prop] = f"{exc.__class__.__name__}: {exc}"
    return {
        "status": "ok" if not errors and len(values) == len(AXIS_PROPERTIES) else "partial",
        "values": values,
        "errors": errors,
    }


def inspect_speed_mode_state(op: Any, page: Any, layers: list[Any]) -> dict[str, Any]:
    values: dict[str, Any] = {"layers": []}
    errors: dict[str, str] = {}
    try:
        page.activate()
    except Exception as exc:
        errors["page.activate"] = f"{exc.__class__.__name__}: {exc}"
    try:
        values["page.speedMode"] = int(op.lt_int("page.speedMode"))
    except Exception as exc:
        errors["page.speedMode"] = f"{exc.__class__.__name__}: {exc}"
    for index, layer in enumerate(layers):
        try:
            page.activate()
            layer.activate()
            layer_value = int(op.lt_int("layer.speedMode"))
            values["layers"].append({"index": index, "layer.speedMode": layer_value})
        except Exception as exc:
            errors[f"layer[{index}].speedMode"] = f"{exc.__class__.__name__}: {exc}"
    expected_count = 1 + len(layers)
    actual_count = int("page.speedMode" in values) + len(values["layers"])
    all_off = values.get("page.speedMode") == 0 and all(
        record.get("layer.speedMode") == 0 for record in values["layers"]
    )
    return {
        "status": "ok" if not errors and actual_count == expected_count else "partial",
        "all_off": all_off if actual_count == expected_count else False,
        "values": values,
        "errors": errors,
    }


def inspect_page(
    op: Any,
    page: Any,
    expected_graphobject_names_by_layer: dict[int, list[str]] | None = None,
) -> dict[str, Any]:
    layers = []
    page_layers = list(page)
    expected_by_layer = expected_graphobject_names_by_layer or {}
    speed_mode_state = inspect_speed_mode_state(op, page, page_layers)
    for index, layer in enumerate(page_layers):
        labtalk_count = None
        try:
            page.activate()
            layer.activate()
            op.lt_exec("layer -c;")
            labtalk_count = int(op.lt_int("count"))
        except Exception:
            pass
        layers.append(
            {
                "index": index,
                **inspect_layer_plots(layer, labtalk_count=labtalk_count, op=op),
                "axis_state": inspect_axis_state(op, page, layer),
                "graph_object_readback": inspect_graph_objects(
                    layer,
                    expected_names=expected_by_layer.get(index, []),
                ),
            }
        )
    return {
        "page": page_name(page),
        "layer_count": len(layers),
        "speed_mode_state": speed_mode_state,
        "layers": layers,
        "plot_count": sum(int(layer["plot_count"]) for layer in layers),
    }


def validate_axis_contract(readback: dict[str, Any], contract: list[dict[str, Any]]) -> dict[str, Any]:
    if not contract:
        return {"status": "not_required", "mismatches": []}
    layers = {int(layer.get("index", -1)): layer for layer in readback.get("layers", [])}
    mismatches: list[dict[str, Any]] = []
    for expected in contract:
        layer_index = int(expected["layer_index"])
        actual_values = layers.get(layer_index, {}).get("axis_state", {}).get("values", {})
        for prop, expected_value in expected.items():
            if prop == "layer_index":
                continue
            actual_value = actual_values.get(prop)
            if actual_value != expected_value:
                mismatches.append(
                    {
                        "layer_index": layer_index,
                        "property": prop,
                        "expected": expected_value,
                        "actual": actual_value,
                    }
                )
    return {"status": "ok" if not mismatches else "failed", "mismatches": mismatches}


def validate_direct_worksheet_plot_bindings(
    readback: dict[str, Any],
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Require every reopened Origin plot to resolve to native Worksheet columns."""
    plots: list[dict[str, Any]] = []
    for layer in readback.get("layers", []):
        layer_index = int(layer.get("index", -1))
        for fallback_index, plot in enumerate(layer.get("plot_details", [])):
            plots.append({"layer_index": layer_index, "plot_index": int(plot.get("index", fallback_index)), **plot})
    mismatches: list[dict[str, Any]] = []
    if not plots:
        mismatches.append({"property": "plot_count", "expected": ">0", "actual": 0})
    for plot in plots:
        required = ["data_workbook", "data_worksheet", "x_column", "y_column"]
        if int(plot.get("plot_type_code") or 0) == 243:
            required.append("z_column")
        for field in required:
            if not plot.get(field):
                mismatches.append({
                    "layer_index": plot["layer_index"], "plot_index": plot["plot_index"],
                    "property": field, "expected": "nonempty Worksheet binding", "actual": plot.get(field),
                })
    indexed = {(p["layer_index"], p["plot_index"]): p for p in plots}
    for expected in contracts:
        key = (int(expected["layer_index"]), int(expected["plot_index"]))
        actual = indexed.get(key)
        if actual is None:
            mismatches.append({"layer_index": key[0], "plot_index": key[1], "property": "exists", "expected": True, "actual": False})
            continue
        for field in ("plot_type_code", "data_workbook", "data_worksheet", "x_column", "y_column", "z_column"):
            if field in expected and actual.get(field) != expected[field]:
                mismatches.append({"layer_index": key[0], "plot_index": key[1], "property": field, "expected": expected[field], "actual": actual.get(field)})
    return {"status": "ok" if not mismatches else "failed", "plot_count": len(plots), "mismatches": mismatches}


def validate_graphobject_contracts(
    readback: dict[str, Any],
    contracts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    if not contracts:
        return {"status": "not_required", "mismatches": []}
    objects: dict[str, dict[str, Any]] = {}
    reported_missing_names: list[str] = []
    enumerated_names: list[str] = []
    enumeration_errors: list[str] = []
    for layer in readback.get("layers", []):
        graph_readback = layer.get("graph_object_readback", {})
        reported_missing_names.extend(str(name) for name in graph_readback.get("missing_names", []))
        for record in graph_readback.get("enumerated_objects", []):
            record_name = str(record.get("name", ""))
            if not record_name:
                continue
            enumerated_names.append(record_name)
            objects.setdefault(record_name.lower(), record)
        if graph_readback.get("enumeration_status") == "unavailable":
            enumeration_errors.append(str(graph_readback.get("enumeration_error") or "enumeration unavailable"))
        for record in graph_readback.get("objects", []):
            record_name = str(record.get("name", ""))
            if record_name:
                objects[record_name.lower()] = record
    missing_names = sorted(
        {
            name
            for name in reported_missing_names
            if name.lower() not in objects
        },
        key=str.lower,
    )
    mismatches: list[dict[str, Any]] = []
    for name, expected in contracts.items():
        actual = objects.get(name.lower())
        if actual is None:
            mismatches.append({"name": name, "property": "exists", "expected": True, "actual": False})
            continue
        if "attach" in expected and int(float(actual.get("attach", -1))) != int(expected["attach"]):
            mismatches.append(
                {"name": name, "property": "attach", "expected": expected["attach"], "actual": actual.get("attach")}
            )
        text_contains = expected.get("text_contains")
        if text_contains and str(text_contains) not in str(actual.get("text", "")):
            mismatches.append(
                {"name": name, "property": "text_contains", "expected": text_contains, "actual": actual.get("text")}
            )
        geometry = expected.get("geometry") or {}
        tolerance = float(geometry.get("tolerance", 0.75))
        for prop in ["x", "y", "dx", "dy"]:
            if prop not in geometry:
                continue
            expected_value = float(geometry[prop])
            actual_value = actual.get(prop)
            try:
                actual_float = float(actual_value)
            except (TypeError, ValueError):
                actual_float = math.nan
            if not math.isfinite(actual_float) or abs(actual_float - expected_value) > tolerance:
                mismatches.append(
                    {
                        "name": name,
                        "property": prop,
                        "expected": expected_value,
                        "actual": actual_value,
                        "tolerance": tolerance,
                    }
                )
        line_geometry = expected.get("line_geometry") or {}
        line_tolerance = float(line_geometry.get("tolerance", 0.75))
        for prop in ["x1", "y1", "x2", "y2"]:
            if prop not in line_geometry:
                continue
            expected_value = float(line_geometry[prop])
            actual_value = actual.get(prop)
            try:
                actual_float = float(actual_value)
            except (TypeError, ValueError):
                actual_float = math.nan
            if not math.isfinite(actual_float) or abs(actual_float - expected_value) > line_tolerance:
                mismatches.append(
                    {
                        "name": name,
                        "property": prop,
                        "expected": expected_value,
                        "actual": actual_value,
                        "tolerance": line_tolerance,
                    }
                )
    controlled_prefixes = {
        match.group(1).lower()
        for name in contracts
        if (match := re.match(r"^(fig\d+_)", name, flags=re.IGNORECASE))
    }
    expected_names = {name.lower() for name in contracts}
    unexpected_fig_prefixed_names = sorted(
        {
            name
            for name in enumerated_names
            if any(name.lower().startswith(prefix) for prefix in controlled_prefixes)
            and name.lower() not in expected_names
        },
        key=str.lower,
    )
    controlled_enumerated_names = [
        name
        for name in enumerated_names
        if any(name.lower().startswith(prefix) for prefix in controlled_prefixes)
    ]
    name_counts = Counter(name.lower() for name in controlled_enumerated_names)
    canonical_names = {name.lower(): name for name in controlled_enumerated_names}
    duplicate_names = sorted(
        [canonical_names[name] for name, count in name_counts.items() if count > 1],
        key=str.lower,
    )
    return {
        "status": (
            "ok"
            if not mismatches
            and not missing_names
            and not unexpected_fig_prefixed_names
            and not duplicate_names
            and not enumeration_errors
            else "failed"
        ),
        "mismatches": mismatches,
        "missing_names": sorted(set(missing_names)),
        "unexpected_fig_prefixed_names": unexpected_fig_prefixed_names,
        "duplicate_names": duplicate_names,
        "enumeration_errors": enumeration_errors,
    }
