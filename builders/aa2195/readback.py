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
        expected_zlevels = expected.get("zlevels")
        if expected_zlevels is not None:
            actual_zlevels = actual.get("zlevels")
            if not isinstance(actual_zlevels, dict):
                mismatches.append({
                    "layer_index": key[0],
                    "plot_index": key[1],
                    "property": "zlevels",
                    "expected": expected_zlevels,
                    "actual": actual_zlevels,
                })
                continue
            expected_minors = int(expected_zlevels.get("minors", 0))
            try:
                actual_minors = int(actual_zlevels.get("minors"))
            except (TypeError, ValueError):
                actual_minors = None
            if actual_minors != expected_minors:
                mismatches.append({
                    "layer_index": key[0],
                    "plot_index": key[1],
                    "property": "zlevels.minors",
                    "expected": expected_minors,
                    "actual": actual_minors,
                })
            expected_levels = [float(value) for value in expected_zlevels.get("levels", [])]
            try:
                actual_levels = [float(value) for value in actual_zlevels.get("levels", [])]
            except (TypeError, ValueError):
                actual_levels = []
            levels_match = len(actual_levels) == len(expected_levels) and all(
                math.isclose(actual_value, expected_value, rel_tol=1e-7, abs_tol=1e-6)
                for actual_value, expected_value in zip(actual_levels, expected_levels)
            )
            if not levels_match:
                mismatches.append({
                    "layer_index": key[0],
                    "plot_index": key[1],
                    "property": "zlevels.levels",
                    "expected": expected_levels,
                    "actual": actual_levels,
                })
    return {"status": "ok" if not mismatches else "failed", "plot_count": len(plots), "mismatches": mismatches}


def validate_plot_style_contracts(
    readback: dict[str, Any],
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate persisted plot styles that are not reliable through OriginPro properties alone."""
    if not contracts:
        return {
            "schema": "originplot.plot_style_contracts.v1",
            "status": "not_required",
            "plots": [],
            "mismatches": [],
        }
    indexed: dict[tuple[int, int], dict[str, Any]] = {}
    for layer in readback.get("layers", []):
        layer_index = int(layer.get("index", -1))
        for fallback_index, plot in enumerate(layer.get("plot_details", [])):
            indexed[(layer_index, int(plot.get("index", fallback_index)))] = plot
    records: list[dict[str, Any]] = []
    mismatches: list[dict[str, Any]] = []
    for expected in contracts:
        layer_index = int(expected["layer_index"])
        plot_index = int(expected["plot_index"])
        actual = indexed.get((layer_index, plot_index))
        if actual is None:
            mismatches.append({
                "layer_index": layer_index,
                "plot_index": plot_index,
                "property": "exists",
                "expected": True,
                "actual": False,
            })
            continue
        style = actual.get("style", {})
        record = {
            "layer_index": layer_index,
            "plot_index": plot_index,
            "plot_type_code": actual.get("plot_type_code"),
            "line_style": style.get("line_style", actual.get("line_style")),
            "symbol_shape": style.get("symbol_shape", actual.get("symbol_shape")),
            "symbol_size": style.get("symbol_size", actual.get("symbol_size")),
        }
        records.append(record)
        for prop in ("plot_type_code", "symbol_shape"):
            if prop not in expected:
                continue
            try:
                matches = int(record.get(prop)) == int(expected[prop])
            except (TypeError, ValueError):
                matches = False
            if not matches:
                mismatches.append({
                    "layer_index": layer_index,
                    "plot_index": plot_index,
                    "property": prop,
                    "expected": expected[prop],
                    "actual": record.get(prop),
                })
        if "line_style" in expected:
            try:
                matches = int(record.get("line_style")) == int(expected["line_style"])
            except (TypeError, ValueError):
                matches = False
            if not matches:
                mismatches.append({
                    "layer_index": layer_index,
                    "plot_index": plot_index,
                    "property": "line_style",
                    "expected": expected["line_style"],
                    "actual": record.get("line_style"),
                })
        if "symbol_size" in expected:
            try:
                matches = math.isclose(
                    float(record.get("symbol_size")),
                    float(expected["symbol_size"]),
                    rel_tol=1e-7,
                    abs_tol=0.05,
                )
            except (TypeError, ValueError):
                matches = False
            if not matches:
                mismatches.append({
                    "layer_index": layer_index,
                    "plot_index": plot_index,
                    "property": "symbol_size",
                    "expected": expected["symbol_size"],
                    "actual": record.get("symbol_size"),
                    "tolerance": 0.05,
                })
    return {
        "schema": "originplot.plot_style_contracts.v1",
        "status": "ok" if not mismatches else "failed",
        "plots": records,
        "mismatches": mismatches,
    }


def validate_native_yerror_pairs(
    readback: dict[str, Any],
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Validate Origin 2022 native column/YErr plot pairs after reopen.

    Origin persists native Y error bars as separate type-231 plots. Two
    Origin 2022 readback forms are supported: ``dataset_linked`` for a
    ``colyerr`` pair, and explicitly declared ``implicit_error_column`` for a
    type-231 plot appended after grouped or intentionally overlapped columns.
    The latter reads the Error column as both X and Y even though Origin renders
    it on the corresponding preceding column. Native YErr pairs therefore count
    as two plots.
    """
    layers = {int(layer.get("index", -1)): layer for layer in readback.get("layers", [])}
    mismatches: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for contract in contracts:
        layer_index = int(contract["layer_index"])
        layer = layers.get(layer_index)
        if layer is None:
            mismatches.append(
                {"layer_index": layer_index, "property": "layer_exists", "expected": True, "actual": False}
            )
            continue
        plots = layer.get("plot_details", [])
        expected_plot_count = int(contract.get("expected_plot_count", 2 * len(contract.get("pairs", []))))
        if int(layer.get("plot_count", len(plots))) != expected_plot_count:
            mismatches.append(
                {
                    "layer_index": layer_index,
                    "property": "native_column_yerr_plot_count",
                    "expected": expected_plot_count,
                    "actual": layer.get("plot_count", len(plots)),
                }
            )
        for pair in contract.get("pairs", []):
            column_index = int(pair["column_plot_index"])
            error_index = int(pair["error_plot_index"])
            binding_mode = str(pair.get("binding_mode", "dataset_linked"))
            column_plot = plots[column_index] if 0 <= column_index < len(plots) else None
            error_plot = plots[error_index] if 0 <= error_index < len(plots) else None
            if column_plot is None or error_plot is None:
                mismatches.append(
                    {
                        "layer_index": layer_index,
                        "property": "pair_exists",
                        "expected": [column_index, error_index],
                        "actual": len(plots),
                    }
                )
                continue
            expected = {
                "column_plot_type_code": 203,
                "error_plot_type_code": 231,
                "column_x": pair.get("column_x"),
                "column_y": pair.get("column_y"),
                "error_value_column": pair.get("error_value_column"),
            }
            actual = {
                "column_plot_type_code": column_plot.get("plot_type_code"),
                "error_plot_type_code": error_plot.get("plot_type_code"),
                "column_x": column_plot.get("x_column"),
                "column_y": column_plot.get("y_column"),
                "error_source_column": error_plot.get("x_column"),
                "error_value_column": error_plot.get("y_column"),
                "column_y_dataset": column_plot.get("y_dataset"),
                "error_x_dataset": error_plot.get("x_dataset"),
                "error_y_dataset": error_plot.get("y_dataset"),
            }
            checks: dict[str, bool] = {
                "column_plot_type_code": actual["column_plot_type_code"] == 203,
                "error_plot_type_code": actual["error_plot_type_code"] == 231,
                "column_x": actual["column_x"] == expected["column_x"],
                "column_y": actual["column_y"] == expected["column_y"],
                "same_workbook": column_plot.get("data_workbook") == error_plot.get("data_workbook"),
                "same_worksheet": column_plot.get("data_worksheet") == error_plot.get("data_worksheet"),
                "error_plot_follows_column_plot": error_index > column_index,
            }
            if binding_mode == "dataset_linked":
                checks.update(
                    {
                        "error_source_column": actual["error_source_column"] == expected["column_y"],
                        "error_value_column": actual["error_value_column"] == expected["error_value_column"],
                        "dataset_link": bool(actual["column_y_dataset"])
                        and actual["column_y_dataset"] == actual["error_x_dataset"],
                    }
                )
            elif binding_mode == "implicit_error_column":
                checks.update(
                    {
                        "error_source_column": actual["error_source_column"] == expected["error_value_column"],
                        "error_value_column": actual["error_value_column"] == expected["error_value_column"],
                        "implicit_error_dataset": bool(actual["error_x_dataset"])
                        and actual["error_x_dataset"] == actual["error_y_dataset"],
                    }
                )
            else:
                checks["supported_binding_mode"] = False
            for prop, passed in checks.items():
                if not passed:
                    mismatches.append(
                        {
                            "layer_index": layer_index,
                            "column_plot_index": column_index,
                            "error_plot_index": error_index,
                            "property": prop,
                            "expected": expected,
                            "actual": actual,
                        }
                    )
            records.append(
                {
                    "layer_index": layer_index,
                    "column_plot_index": column_index,
                    "error_plot_index": error_index,
                    "binding_mode": binding_mode,
                    "status": "ok" if all(checks.values()) else "failed",
                    "actual": actual,
                }
            )
    return {
        "schema": "originplot.native_yerror_pairs.v1",
        "status": "ok" if not mismatches else "failed",
        "pair_count": len(records),
        "pairs": records,
        "mismatches": mismatches,
    }


def validate_subplot_worksheet_bindings(
    readback: dict[str, Any],
    contracts: list[dict[str, Any]],
    workbook_aliases: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    """Prove every declared subplot has editable plots bound to its Worksheets."""
    if not contracts:
        return {
            "schema": "originplot.subplot_worksheet_bindings.v1",
            "status": "not_required",
            "subplots": [],
            "mismatches": [],
        }

    aliases = workbook_aliases or {}
    layers = {int(layer.get("index", -1)): layer for layer in readback.get("layers", [])}
    mismatches: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    seen_layers: set[int] = set()

    for contract in contracts:
        subplot_id = str(contract.get("subplot_id", "")).strip()
        layer_index = int(contract.get("layer_index", -1))
        expected_plot_count = int(contract.get("expected_plot_count", 0))
        expected_books = [str(value) for value in contract.get("worksheet_books", []) if str(value)]
        expected_sheets = [str(value) for value in contract.get("worksheet_names", []) if str(value)]
        if not subplot_id or subplot_id in seen_ids:
            mismatches.append({
                "subplot_id": subplot_id,
                "layer_index": layer_index,
                "property": "unique nonempty subplot_id",
                "expected": True,
                "actual": subplot_id or None,
            })
        seen_ids.add(subplot_id)
        if layer_index in seen_layers:
            mismatches.append({
                "subplot_id": subplot_id,
                "layer_index": layer_index,
                "property": "unique layer contract",
                "expected": True,
                "actual": False,
            })
        seen_layers.add(layer_index)
        if expected_plot_count <= 0:
            mismatches.append({
                "subplot_id": subplot_id,
                "layer_index": layer_index,
                "property": "expected_plot_count",
                "expected": ">0",
                "actual": expected_plot_count,
            })

        layer = layers.get(layer_index)
        plots = list(layer.get("plot_details", [])) if layer else []
        if layer is None:
            mismatches.append({
                "subplot_id": subplot_id,
                "layer_index": layer_index,
                "property": "editable graph layer exists",
                "expected": True,
                "actual": False,
            })
        if len(plots) != expected_plot_count:
            mismatches.append({
                "subplot_id": subplot_id,
                "layer_index": layer_index,
                "property": "editable plot count",
                "expected": expected_plot_count,
                "actual": len(plots),
            })

        allowed_aliases: set[str] = set()
        alias_to_book: dict[str, str] = {}
        for book in expected_books:
            book_aliases = {book, *[str(value) for value in aliases.get(book, []) if str(value)]}
            allowed_aliases.update(book_aliases)
            for alias in book_aliases:
                alias_to_book[alias] = book
        bindings: list[dict[str, Any]] = []
        used_books: set[str] = set()
        for fallback_index, plot in enumerate(plots):
            plot_index = int(plot.get("index", fallback_index))
            workbook = str(plot.get("data_workbook") or "")
            worksheet = str(plot.get("data_worksheet") or "")
            binding = {
                "plot_index": plot_index,
                "plot_type_code": plot.get("plot_type_code"),
                "data_workbook": workbook or None,
                "data_worksheet": worksheet or None,
                "x_column": plot.get("x_column"),
                "y_column": plot.get("y_column"),
                "z_column": plot.get("z_column"),
            }
            bindings.append(binding)
            required = ["data_workbook", "data_worksheet", "x_column", "y_column"]
            if int(plot.get("plot_type_code") or 0) == 243:
                required.append("z_column")
            for field in required:
                if not plot.get(field):
                    mismatches.append({
                        "subplot_id": subplot_id,
                        "layer_index": layer_index,
                        "plot_index": plot_index,
                        "property": field,
                        "expected": "nonempty direct Worksheet binding",
                        "actual": plot.get(field),
                    })
            if expected_books and workbook not in allowed_aliases:
                mismatches.append({
                    "subplot_id": subplot_id,
                    "layer_index": layer_index,
                    "plot_index": plot_index,
                    "property": "corresponding worksheet book",
                    "expected": expected_books,
                    "actual": workbook or None,
                })
            elif workbook in alias_to_book:
                used_books.add(alias_to_book[workbook])
            if expected_sheets and worksheet not in expected_sheets:
                mismatches.append({
                    "subplot_id": subplot_id,
                    "layer_index": layer_index,
                    "plot_index": plot_index,
                    "property": "corresponding worksheet name",
                    "expected": expected_sheets,
                    "actual": worksheet or None,
                })
        missing_books = [book for book in expected_books if book not in used_books]
        if missing_books:
            mismatches.append({
                "subplot_id": subplot_id,
                "layer_index": layer_index,
                "property": "all declared worksheet books used",
                "expected": expected_books,
                "actual": sorted(used_books),
            })
        records.append({
            "subplot_id": subplot_id,
            "layer_index": layer_index,
            "editable_plot_count": len(plots),
            "declared_worksheet_books": expected_books,
            "declared_worksheet_names": expected_sheets,
            "resolved_worksheet_books": sorted(used_books),
            "plot_bindings": bindings,
        })

    return {
        "schema": "originplot.subplot_worksheet_bindings.v1",
        "status": "ok" if not mismatches else "failed",
        "subplot_count": len(records),
        "subplots": records,
        "mismatches": mismatches,
    }


def validate_plot_derived_legends(
    readback: dict[str, Any],
    contracts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Require legends to reference existing plots instead of legend-only data."""
    if not contracts:
        return {
            "schema": "originplot.plot_derived_legends.v1",
            "status": "not_required",
            "legends": [],
            "mismatches": [],
        }

    layers = {int(layer.get("index", -1)): layer for layer in readback.get("layers", [])}
    mismatches: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    for contract in contracts:
        object_name = str(contract.get("object_name", ""))
        layer_index = int(contract.get("layer_index", -1))
        expected_numbers = [int(value) for value in contract.get("plot_numbers", [])]
        layer = layers.get(layer_index, {})
        graph_readback = layer.get("graph_object_readback", {})
        objects: dict[str, dict[str, Any]] = {}
        for collection in ("objects", "enumerated_objects"):
            for record in graph_readback.get(collection, []):
                name = str(record.get("name", ""))
                if name:
                    objects[name.lower()] = record
        actual = objects.get(object_name.lower())
        text = str(actual.get("text", "")) if actual else ""
        actual_numbers = [int(value) for value in re.findall(r"\\l\((\d+)\)", text, flags=re.IGNORECASE)]
        plot_details = layer.get("plot_details", [])
        plot_count = len(plot_details)
        if actual is None:
            mismatches.append({
                "object_name": object_name,
                "layer_index": layer_index,
                "property": "plot-derived legend object exists",
                "expected": True,
                "actual": False,
            })
        if actual_numbers != expected_numbers:
            mismatches.append({
                "object_name": object_name,
                "layer_index": layer_index,
                "property": "plot references",
                "expected": expected_numbers,
                "actual": actual_numbers,
            })
        invalid_numbers = [number for number in expected_numbers if number <= 0 or number > plot_count]
        if invalid_numbers:
            mismatches.append({
                "object_name": object_name,
                "layer_index": layer_index,
                "property": "referenced plots exist in legend layer",
                "expected": f"1..{plot_count}",
                "actual": invalid_numbers,
            })
        expected_line_style = contract.get("expected_plot_line_style")
        actual_line_styles: list[Any] = []
        if expected_line_style is not None and not invalid_numbers:
            actual_line_styles = [
                plot_details[number - 1].get("line_style")
                for number in expected_numbers
            ]
            unexpected_styles = [
                {"plot_number": number, "line_style": style}
                for number, style in zip(expected_numbers, actual_line_styles)
                if style != expected_line_style
            ]
            if unexpected_styles:
                mismatches.append({
                    "object_name": object_name,
                    "layer_index": layer_index,
                    "property": "referenced plot line styles",
                    "expected": expected_line_style,
                    "actual": unexpected_styles,
                })
        text_contains = str(contract.get("text_contains", ""))
        if text_contains and text_contains not in text:
            mismatches.append({
                "object_name": object_name,
                "layer_index": layer_index,
                "property": "text_contains",
                "expected": text_contains,
                "actual": text,
            })
        records.append({
            "object_name": object_name,
            "layer_index": layer_index,
            "plot_numbers": actual_numbers,
            "plot_count_in_layer": plot_count,
            "expected_plot_line_style": expected_line_style,
            "actual_plot_line_styles": actual_line_styles,
            "text": text,
        })
    return {
        "schema": "originplot.plot_derived_legends.v1",
        "status": "ok" if not mismatches else "failed",
        "legend_count": len(records),
        "legends": records,
        "mismatches": mismatches,
    }


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
        if "object_type" in expected:
            try:
                actual_object_type = int(float(actual.get("object_type")))
            except (TypeError, ValueError):
                actual_object_type = None
            if actual_object_type != int(expected["object_type"]):
                mismatches.append(
                    {
                        "name": name,
                        "property": "object_type",
                        "expected": int(expected["object_type"]),
                        "actual": actual.get("object_type"),
                    }
                )
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
