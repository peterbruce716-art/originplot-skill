from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.artifact_manifest import file_record, note_operation, update_artifacts  # noqa: E402
from runtime.editable_opju import ensure_opju_file_editable, open_opju_editable  # noqa: E402


PLOT_TYPE_FAMILIES = {
    200: "line",
    201: "scatter",
    202: "line_symbol",
    203: "column",
    226: "contour",
    230: "auto",
    243: "worksheet_xyz_contour",
}

GRAPH_OBJECT_TYPE_FAMILIES = {
    2: "text",
    4: "line",
    6: "line",
    7: "line",
    8: "rectangle",
    9: "ellipse",
    11: "polygon",
    19: "polygon",
}


def origin_graph_pages(op: Any) -> list[Any]:
    """Return graph pages using OriginPro's documented single-letter page code."""
    return list(op.pages("g"))


def ensure_opju_editable(path: Path) -> dict[str, Any]:
    return ensure_opju_file_editable(path)


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    return str(value)


def _read_property(obj: Any, names: list[str]) -> Any:
    for name in names:
        try:
            value = getattr(obj, name)
            if callable(value):
                value = value()
            return _json_value(value)
        except Exception:
            continue
    return None


def _read_parameterized_property(obj: Any, methods: list[str], names: list[str]) -> Any:
    for method_name in methods:
        method = getattr(obj, method_name, None)
        if not callable(method):
            continue
        for name in names:
            try:
                return _json_value(method(name))
            except Exception:
                continue
    return None


def _plot_family(plot_type: Any) -> str:
    try:
        code = int(plot_type)
    except (TypeError, ValueError):
        code = None
    if code in PLOT_TYPE_FAMILIES:
        return PLOT_TYPE_FAMILIES[code]
    normalized = str(plot_type or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "l": "line",
        "line": "line",
        "s": "scatter",
        "scatter": "scatter",
        "y": "line_symbol",
        "line_symbols": "line_symbol",
        "line_symbol": "line_symbol",
        "c": "column",
        "column": "column",
        "bar": "bar",
        "contour": "contour",
    }
    return aliases.get(normalized, "unknown")


def _parse_origin_binding(value: Any) -> dict[str, Any]:
    raw = None if value is None else str(value)
    result = {
        "data_binding_raw": raw,
        "data_workbook": None,
        "data_worksheet": None,
        "x_column": None,
        "y_column": None,
    }
    if not raw:
        return result
    match = re.match(r"^\[([^\]]+)\]([^!]+)!\(([^)]*)\)$", raw.strip())
    if not match:
        return result
    columns = [item.strip() for item in match.group(3).split(",")]
    result.update(
        {
            "data_workbook": match.group(1).strip(),
            "data_worksheet": match.group(2).strip(),
            "x_column": columns[0] if columns else None,
            "y_column": columns[1] if len(columns) > 1 else None,
        }
    )
    return result


def _parse_origin_dataset(value: Any, op: Any | None = None) -> dict[str, Any]:
    raw = None if value is None else str(value).strip()
    result = {
        "dataset": raw,
        "workbook": None,
        "worksheet": None,
        "worksheet_index": None,
        "column": None,
    }
    if not raw:
        return result
    match = re.match(r"^(?P<book>.+)_(?P<column>[^_@]+)(?:@(?P<sheet_index>\d+))?$", raw)
    if not match:
        return result
    workbook = match.group("book")
    column = match.group("column")
    worksheet_index = int(match.group("sheet_index") or 1)
    worksheet = f"Sheet{worksheet_index}"
    find_book = getattr(op, "find_book", None) if op is not None else None
    if callable(find_book):
        try:
            book = find_book("w", workbook)
            if book is not None and 0 < worksheet_index <= len(book):
                worksheet = str(getattr(book[worksheet_index - 1], "name", worksheet))
        except Exception:
            pass
    result.update(
        {
            "workbook": workbook,
            "worksheet": worksheet,
            "worksheet_index": worksheet_index,
            "column": column,
        }
    )
    return result


def _labtalk_plot_semantics(op: Any, plot_number: int) -> dict[str, Any]:
    errors: dict[str, str] = {}
    plot_type_code = None
    visible = None
    y_dataset = None
    x_dataset = None
    z_dataset = None
    try:
        candidate = int(op.lt_int(f"layer.plot{plot_number}.pid"))
        plot_type_code = candidate if candidate > 0 else None
    except Exception as exc:
        errors["plot_type_code"] = f"{exc.__class__.__name__}: {exc}"
    try:
        visible = bool(int(op.lt_int(f"layer.plot{plot_number}.show")))
    except Exception as exc:
        errors["visible"] = f"{exc.__class__.__name__}: {exc}"
    try:
        y_dataset = str(op.get_lt_str(f"layer.plot{plot_number}.name$") or "").strip() or None
    except Exception as exc:
        errors["y_dataset"] = f"{exc.__class__.__name__}: {exc}"
    if y_dataset:
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_@]*", y_dataset):
            previous_register = None
            register_read = False
            try:
                previous_register = op.get_lt_str("%A")
                register_read = True
                if not op.lt_exec(f"%A=xof({y_dataset});"):
                    raise RuntimeError("LabTalk xof command returned false")
                x_dataset = str(op.get_lt_str("%A") or "").strip() or None
            except Exception as exc:
                errors["x_dataset"] = f"{exc.__class__.__name__}: {exc}"
            finally:
                if register_read:
                    try:
                        op.set_lt_str("%A", previous_register)
                    except Exception as exc:
                        errors["register_restore"] = f"{exc.__class__.__name__}: {exc}"
        else:
            errors["x_dataset"] = "unsafe or unsupported Origin dataset identifier"
    # For an XYZ-range contour (PID 243), plotN.name$ is Z and xof(Z) is Y.
    # Resolve xof(Y) once more so readback proves the complete Worksheet X/Y/Z chain.
    if plot_type_code == 243 and y_dataset and x_dataset:
        z_dataset = y_dataset
        y_dataset = x_dataset
        previous_register = None
        register_read = False
        try:
            previous_register = op.get_lt_str("%A")
            register_read = True
            if not op.lt_exec(f"%A=xof({y_dataset});"):
                raise RuntimeError("LabTalk xof command returned false")
            x_dataset = str(op.get_lt_str("%A") or "").strip() or None
        except Exception as exc:
            errors["xyz_x_dataset"] = f"{exc.__class__.__name__}: {exc}"
        finally:
            if register_read:
                try:
                    op.set_lt_str("%A", previous_register)
                except Exception as exc:
                    errors["xyz_register_restore"] = f"{exc.__class__.__name__}: {exc}"
    y_parts = _parse_origin_dataset(y_dataset, op=op)
    x_parts = _parse_origin_dataset(x_dataset, op=op)
    z_parts = _parse_origin_dataset(z_dataset, op=op)
    workbook = y_parts["workbook"]
    worksheet = y_parts["worksheet"]
    x_column = x_parts["column"]
    y_column = y_parts["column"]
    z_column = z_parts["column"]
    binding = None
    if workbook and worksheet and x_column and y_column:
        columns = f"{x_column},{y_column},{z_column}" if z_column else f"{x_column},{y_column}"
        binding = f"[{workbook}]{worksheet}!({columns})"
    result = {
        "plot_type": plot_type_code,
        "plot_type_code": plot_type_code,
        "plot_family": _plot_family(plot_type_code),
        "visible": visible,
        "x_dataset": x_dataset,
        "y_dataset": y_dataset,
        "z_dataset": z_dataset,
        "data_binding": binding,
        "data_binding_raw": binding,
        "data_workbook": workbook,
        "data_worksheet": worksheet,
        "data_worksheet_index": y_parts["worksheet_index"],
        "x_column": x_column,
        "y_column": y_column,
        "z_column": z_column,
        "semantic_route": "labtalk_layer_plotn_xof",
    }
    if errors:
        result["semantic_readback_errors"] = errors
    return result


def _plot_detail(plot: Any, index: int) -> dict[str, Any]:
    plot_type = _read_property(plot, ["type"])
    if plot_type is None:
        candidate_type = _read_parameterized_property(plot, ["get_int"], ["type"])
        try:
            plot_type = candidate_type if int(candidate_type) > 0 else None
        except (TypeError, ValueError):
            plot_type = candidate_type
    raw_plot = getattr(plot, "obj", None)
    plot_type_name = _read_property(raw_plot, ["GetTypeName", "TypeName"]) if raw_plot is not None else None
    binding = _read_property(plot, ["lt_range"])
    visible = _read_property(plot, ["visible"])
    if visible is None and raw_plot is not None:
        visible = _read_property(raw_plot, ["GetShow", "Show"])
    if visible is None:
        visible = _read_parameterized_property(plot, ["get_int"], ["visible", "show"])
    line_color = _read_property(plot, ["color"])
    if line_color is None:
        line_color = _read_parameterized_property(plot, ["get_str", "get_int"], ["color", "line.color"])
    line_width = _read_property(plot, ["linewidth", "width"])
    if line_width is None:
        line_width = _read_parameterized_property(plot, ["get_float"], ["line.width", "linewidth", "width"])
    line_style = _read_property(plot, ["line_style", "linestyle"])
    if line_style is None:
        line_style = _read_parameterized_property(plot, ["get_int", "get_str"], ["line.style", "style"])
    zlevels = _read_property(plot, ["zlevels"])
    style = {
        key: value
        for key, value in {
            "line_color": line_color,
            "line_width": line_width,
            "line_style": line_style,
            "colormap": _read_property(plot, ["colormap"]),
            "symbol_size": _read_property(plot, ["symbol_size"]),
            "transparency": _read_property(plot, ["transparency"]),
        }.items()
        if value is not None
    }
    detail = {
        "index": index,
        "name": _read_property(plot, ["name"]),
        "plot_type": plot_type,
        "plot_type_code": plot_type,
        "plot_type_name": plot_type_name,
        "plot_family": _plot_family(plot_type if plot_type is not None else plot_type_name),
        "data_binding": binding,
        **_parse_origin_binding(binding),
        "visible": visible,
        "line_color": line_color,
        "line_width": line_width,
        "line_style": line_style,
        "zlevels": zlevels,
        "style": style,
    }
    return detail


def _labtalk_plot_line_style(op: Any, plot: Any) -> int | None:
    """Read the persisted Set -d value; Origin 2022 Plot properties report 0 for every dash style."""
    plot_name = _read_property(plot, ["name"])
    if not plot_name:
        return None
    variable = "__opls"
    try:
        layer = getattr(plot, "layer", None)
        execute = getattr(layer, "LT_execute", None)
        if callable(execute):
            execute(f"get {plot_name} -d {variable};")
        else:
            op.lt_exec(f"get {plot_name} -d {variable};")
        return int(op.lt_int(variable))
    except Exception:
        return None


def _labtalk_plot_symbol_style(op: Any, plot: Any) -> dict[str, Any]:
    """Read persisted Set -k/-z marker shape and size values in Origin 2022."""
    plot_name = _read_property(plot, ["name"])
    if not plot_name:
        return {}
    try:
        command = f"get {plot_name} -k __opsk; get {plot_name} -z __opsz;"
        layer = getattr(plot, "layer", None)
        execute = getattr(layer, "LT_execute", None)
        if callable(execute):
            execute(command)
        else:
            op.lt_exec(command)
        return {
            "symbol_shape": int(op.lt_int("__opsk")),
            "symbol_size": float(op.lt_float("__opsz")),
        }
    except Exception:
        return {}


def inspect_layer_plots(layer: Any, labtalk_count: int | None = None, op: Any | None = None) -> dict[str, Any]:
    """Read plots through the public GLayer API and cross-check LabTalk count."""
    plot_list_error = None
    try:
        plots = list(layer.plot_list())
    except Exception as exc:
        plots = []
        plot_list_error = f"{exc.__class__.__name__}: {exc}"
    plot_list_count = len(plots)
    plot_details = []
    for index, plot in enumerate(plots):
        line_style = None
        if op is not None:
            try:
                parent_name = layer.obj.GetParent().GetName()
                op.lt_exec(f"win -a {parent_name};")
            except Exception:
                pass
            try:
                layer.activate()
            except Exception:
                pass
            line_style = _labtalk_plot_line_style(op, plot)
        detail = _plot_detail(plot, index)
        detail["graph_plot_range"] = detail.get("data_binding")
        if op is not None:
            semantics = _labtalk_plot_semantics(op, index + 1)
            detail.update({key: value for key, value in semantics.items() if value is not None})
            if line_style is not None:
                detail["line_style"] = line_style
                detail.setdefault("style", {})["line_style"] = line_style
                detail["line_style_readback_route"] = "labtalk_get_dash"
            if detail.get("plot_type_code") in {201, 202}:
                symbol_style = _labtalk_plot_symbol_style(op, plot)
                if symbol_style:
                    detail.setdefault("style", {}).update(symbol_style)
                    detail.update(symbol_style)
                    detail["symbol_style_readback_route"] = "labtalk_get_shape_size"
        plot_details.append(detail)
    result = {
        "primary_route": "plot_list",
        "plot_count": plot_list_count,
        "plot_list_count": plot_list_count,
        "labtalk_layer_count": labtalk_count,
        "readback_disagreement": labtalk_count is not None and plot_list_count != int(labtalk_count),
        "plot_details": plot_details,
    }
    if plot_list_error:
        result["plot_list_error"] = plot_list_error
    return result


def _normalize_type_name(value: Any) -> str:
    text = str(value or "").strip()
    return "Unknown" if text.lower() in {"", "unknow", "unknown"} else text


def _standard_graph_object_type(object_type: Any, type_name: Any) -> str:
    try:
        code = int(object_type)
    except (TypeError, ValueError):
        code = None
    if code in GRAPH_OBJECT_TYPE_FAMILIES:
        return GRAPH_OBJECT_TYPE_FAMILIES[code]
    normalized = str(type_name or "").strip().lower()
    if "text" in normalized or "label" in normalized:
        return "text"
    if "rect" in normalized:
        return "rectangle"
    if "ellipse" in normalized or "circle" in normalized:
        return "ellipse"
    if "polygon" in normalized:
        return "polygon"
    if "line" in normalized or "arrow" in normalized or "bezier" in normalized:
        return "line"
    return "unknown"


def _graph_object_record(obj: Any, index: int) -> dict[str, Any]:
    object_type = _read_property(obj, ["GetObjectType", "GetType", "Type", "type"])
    type_name = _normalize_type_name(_read_property(obj, ["GetTypeName"]))
    record: dict[str, Any] = {
        "index": index,
        "name": _read_property(obj, ["GetName", "Name", "name"]),
        "object_type": object_type,
        "type_name": type_name,
        "standard_type": _standard_graph_object_type(object_type, type_name),
    }
    for prop, names in {
        "x": ["GetX", "X"],
        "y": ["GetY", "Y"],
        "dx": ["GetDX", "DX"],
        "dy": ["GetDY", "DY"],
        "left": ["GetLeft", "Left"],
        "top": ["GetTop", "Top"],
        "width": ["GetWidth", "Width"],
        "height": ["GetHeight", "Height"],
    }.items():
        value = _read_property(obj, names)
        if value is not None:
            record[prop] = value
    for prop in ["attach", "x1", "y1", "x2", "y2", "color", "fillColor", "text"]:
        value = None
        for getter_name in ["GetNumProp", "GetStrProp"]:
            try:
                value = getattr(obj, getter_name)(prop)
                break
            except Exception:
                continue
        if value is not None and value != "":
            record[prop] = _json_value(value)
    text = _read_property(obj, ["GetText", "Text"])
    if text not in {None, ""}:
        record["text"] = text
    return record


def inspect_graph_objects(layer: Any, expected_names: list[str] | None = None) -> dict[str, Any]:
    objects: list[dict[str, Any]] = []
    errors: list[str] = []
    try:
        collection = layer.obj.GraphObjects
        count = int(collection.GetCount())
    except Exception as exc:
        return {"status": "unavailable", "objects": [], "error": f"{exc.__class__.__name__}: {exc}"}
    enumerated_objects: list[dict[str, Any]] = []
    enumeration_error = None
    try:
        enumerated_objects = [_graph_object_record(obj, index) for index, obj in enumerate(collection)]
    except Exception as exc:
        enumeration_error = f"{exc.__class__.__name__}: {exc}"
    names = [str(name) for name in (expected_names or [])]
    if not names:
        result = {
            "status": "names_required" if count else "ok",
            "object_count": count,
            "objects": [],
            "enumerated_objects": enumerated_objects,
            "enumeration_status": "ok" if enumeration_error is None else "unavailable",
            "missing_names": [],
            "errors": [],
            "note": "PyOrigin GraphObjects is name-indexed; provide expected_names for deterministic readback.",
        }
        if enumeration_error:
            result["enumeration_error"] = enumeration_error
        return result
    missing_names: list[str] = []
    for index, expected_name in enumerate(names):
        try:
            obj = collection(expected_name)
            if obj is None:
                obj = collection(expected_name.upper())
            if obj is None:
                missing_names.append(expected_name)
                continue
            objects.append(_graph_object_record(obj, index))
        except Exception as exc:
            errors.append(f"name {expected_name}: {exc.__class__.__name__}: {exc}")
            missing_names.append(expected_name)
    status = "ok" if not errors and not missing_names else "partial"
    result = {
        "status": status,
        "object_count": count,
        "objects": objects,
        "enumerated_objects": enumerated_objects,
        "enumeration_status": "ok" if enumeration_error is None else "unavailable",
        "missing_names": missing_names,
        "errors": errors,
    }
    if enumeration_error:
        result["enumeration_error"] = enumeration_error
    return result


class Adapter:
    route = "inspection"

    OPERATIONS = {"project.reopen.clean", "project.inspect", "graph.export.postreopen"}

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self.config = config or {}
        self.execution_mode = str(self.config.get("execution_mode") or "live")
        if self.config.get("allow_noop") and self.execution_mode != "test":
            raise RuntimeError("allow_noop is test-only; live inspection refuses no-op adapters")
        self.allow_noop = bool(self.config.get("allow_noop"))
        self.op = None
        self.project_path: Path | None = None

    def supports(self, operation: dict[str, Any]) -> bool:
        return operation.get("adapter_route") == self.route and operation.get("operation_id") in self.OPERATIONS

    def execute(self, operation: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        operation_id = str(operation.get("operation_id"))
        if self.allow_noop:
            note_operation(context, operation, "completed", {"noop": True})
            return {"status": "completed", "route": self.route, "operation_id": operation_id, "noop": True}
        method = getattr(self, f"op_{operation_id.replace('.', '_')}", None)
        if method is None:
            return {"status": "unsupported", "route": self.route, "operation_id": operation_id}
        result = method(operation.get("payload") or {}, context)
        note_operation(context, operation, "completed", result)
        return {"status": "completed", "route": self.route, "operation_id": operation_id, **result}

    def _origin(self):
        if self.op is None:
            import originpro as op

            op.set_show(False)
            op.new(asksave=False)
            self.op = op
        return self.op

    def op_project_reopen_clean(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        project_path = Path(str(payload.get("project_path") or ""))
        if not project_path.is_absolute():
            project_path = (Path(context.get("workspace") or ".") / project_path).resolve()
        if not project_path.exists():
            raise FileNotFoundError(f"project.reopen.clean cannot find OPJU: {project_path}")
        self.project_path = project_path
        op = self._origin()
        editable_evidence = open_opju_editable(op, project_path)
        return {
            "project_path": str(project_path),
            "opened": True,
            "inspect_pid": os.getpid(),
            "editable_open_evidence": editable_evidence,
        }

    def op_project_inspect(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        op = self._origin()
        contracts = payload.get("contracts") or {}
        graph_pages = []
        workbook_pages = []
        matrices = []
        warnings: list[dict[str, Any]] = []
        for page in op.pages():
            page_type = getattr(page, "type", "")
            record = {
                "name": getattr(page, "name", ""),
                "long_name": getattr(page, "lname", ""),
                "type": page_type,
                "layers": len(page),
            }
            if page_type == "GPage":
                layers = []
                page_key = record["long_name"] or record["name"]
                expected_object_contract = contracts.get("expected_graph_objects") or {}
                expected_object_names = (
                    expected_object_contract.get(page_key, [])
                    if isinstance(expected_object_contract, dict)
                    else []
                )
                for layer_index, layer in enumerate(page):
                    labtalk_count = None
                    labtalk_error = None
                    try:
                        page.activate()
                        layer.activate()
                        op.lt_exec("layer -c;")
                        labtalk_count = int(op.lt_int("count"))
                    except Exception as exc:
                        labtalk_error = f"{exc.__class__.__name__}: {exc}"
                    plot_readback = inspect_layer_plots(layer, labtalk_count=labtalk_count, op=op)
                    layer_record = {
                        "index": layer_index,
                        "name": getattr(layer, "name", ""),
                        "plots": plot_readback["plot_count"],
                        **plot_readback,
                        "graph_object_readback": inspect_graph_objects(layer, expected_names=expected_object_names),
                    }
                    if labtalk_error:
                        layer_record["labtalk_layer_count_error"] = labtalk_error
                    if plot_readback["readback_disagreement"]:
                        warnings.append(
                            {
                                "code": "W402_PLOT_READBACK_DISAGREEMENT",
                                "page": record["long_name"] or record["name"],
                                "layer_index": layer_index,
                                "plot_list_count": plot_readback["plot_list_count"],
                                "labtalk_layer_count": plot_readback["labtalk_layer_count"],
                            }
                        )
                    for axis_name, attr in {"x": "xlim", "y": "ylim"}.items():
                        try:
                            values = getattr(layer, attr)
                            layer_record[f"{axis_name}_limits"] = [float(values[0]), float(values[1])]
                        except Exception as exc:
                            layer_record[f"{axis_name}_limits_error"] = str(exc)
                    layers.append(layer_record)
                record["layer_details"] = layers
                graph_pages.append(record)
            elif page_type == "WBook":
                workbook_pages.append(record)
            elif page_type == "MBook":
                matrices.append(record)
        expected = contracts.get("expected") or {}
        primary = contracts.get("primary_graph")
        errors: list[str] = []
        if primary and primary not in {item["long_name"] or item["name"] for item in graph_pages}:
            errors.append(f"primary graph not found: {primary}")
        if expected.get("graph_pages") is not None and len(graph_pages) < int(expected["graph_pages"]):
            errors.append("graph page count below expected")
        if expected.get("workbooks") is not None and len(workbook_pages) < int(expected["workbooks"]):
            errors.append("workbook count below expected")
        actual_plot_count = sum(
            int(layer.get("plot_count", 0))
            for page in graph_pages
            for layer in page.get("layer_details", [])
        )
        if expected.get("plots") is not None and actual_plot_count < int(expected["plots"]):
            errors.append("plot count below expected")
        inspection = {
            "schema": "originplot.inspection.v5",
            "project": {"path": str(self.project_path), "exists": bool(self.project_path and self.project_path.exists())},
            "process": {"pid": os.getpid()},
            "workbooks": workbook_pages,
            "matrices": matrices,
            "graph_pages": graph_pages,
            "exports": {},
            "warnings": warnings,
            "errors": errors,
            "status": "pass" if not errors else "failed",
        }
        run_dir = Path(context.get("run_dir") or ".").resolve()
        inspection_path = run_dir / "inspection.json"
        inspection_path.parent.mkdir(parents=True, exist_ok=True)
        inspection_path.write_text(json.dumps(inspection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _, artifacts_path, run_id = _artifact_context(context)
        update_artifacts(artifacts_path, run_id, {"inspection": file_record(inspection_path)})
        if errors:
            raise RuntimeError("; ".join(errors))
        return {"inspection_path": str(inspection_path), "graph_pages": len(graph_pages), "workbooks": len(workbook_pages)}

    def op_graph_export_postreopen(self, payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
        op = self._origin()
        path = Path(str(payload.get("path") or "post_reopen.png"))
        if not path.is_absolute():
            path = (Path(context.get("workspace") or ".") / path).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        pages = origin_graph_pages(op)
        if not pages:
            raise RuntimeError("no graph page available for post-reopen export")
        export = payload.get("export") or {}
        fmt = str(export.get("format") or path.suffix.lower().lstrip(".") or "png")
        width = int(export.get("width_px") or self.config.get("export_width_px") or 1600)
        replace = bool(export.get("replace", True))
        try:
            pages[0].save_fig(str(path), type=fmt, replace=replace, width=width)
        except TypeError as exc:
            raise RuntimeError(f"Origin export must support fixed type/replace/width parameters: {exc}") from exc
        _, artifacts_path, run_id = _artifact_context(context)
        update_artifacts(artifacts_path, run_id, {"post_reopen_export": file_record(path)})
        return {"path": str(path), "size_bytes": path.stat().st_size, "export": {"format": fmt, "width_px": width, "replace": replace}}

    def close(self) -> None:
        if self.op is None:
            return
        try:
            self.op.exit()
        finally:
            self.op = None


def _artifact_context(context: dict[str, Any]) -> tuple[Path, Path, str]:
    from runtime.artifact_manifest import context_paths

    return context_paths(context)


def create_adapter(config: dict[str, Any]) -> Adapter:
    return Adapter(config)
