from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Callable

from originplot.operation_plan import OperationPlan
from originplot.runtime.origin_session import attached_origin, is_administrator
from originplot.spec.io import read_table
from originplot.verification import artifact_is_nonblank, inspect_reopened_project, no_demo_watermark


def _template_for(plan: OperationPlan) -> str:
    if plan.plot_type in {"bar", "grouped_bar", "stacked_bar"}:
        return "COLUMN"
    if plan.plot_type == "contour":
        return "CONTOUR"
    if plan.plot_type == "heatmap":
        return "HEATMAP"
    return "LINE"


def _apply_page_size(page: Any, page_spec: dict[str, Any]) -> None:
    width_cm = page_spec.get("width_cm")
    height_cm = page_spec.get("height_cm")
    if width_cm is None or height_cm is None:
        return
    try:
        width_dots = round(float(width_cm) / 2.54 * float(page.get_float("resx")))
        height_dots = round(float(height_cm) / 2.54 * float(page.get_float("resy")))
        page.lt_exec(f"page.width={width_dots}; page.height={height_dots}; page.emo=0; page.autoSize=2;")
    except Exception as exc:
        raise RuntimeError(f"E521_PAGE_GEOMETRY_FAILED: {exc}") from exc


def _style_plot(plot: Any, style: dict[str, Any]) -> None:
    color = style.get("color") or style.get("line_color")
    if color:
        try:
            plot.color = str(color)
        except Exception:
            pass
    width = style.get("line_width_pt")
    if width is not None:
        for prop in ("line.width", "linewidth", "width"):
            try:
                plot.set_float(prop, float(width))
                break
            except Exception:
                continue
    symbol = style.get("symbol")
    if isinstance(symbol, int):
        for prop in ("symbol.kind", "symbol.type", "symbol"):
            try:
                plot.set_int(prop, symbol)
                break
            except Exception:
                continue


def _ensure_layers(page: Any, count: int) -> None:
    while len(page) < count:
        before = len(page)
        try:
            page.add_layer()
        except Exception:
            try:
                page.lt_exec("layer -n;")
            except Exception as exc:
                raise RuntimeError(f"E522_LAYER_CREATE_FAILED: cannot create {count} layers") from exc
        if len(page) <= before:
            raise RuntimeError(f"E522_LAYER_CREATE_FAILED: Origin did not create layer {before + 1}")


class _SheetWriter:
    def __init__(self, sheet: Any, rows: list[dict[str, Any]]) -> None:
        self.sheet = sheet
        self.rows = rows
        self.next_col = 0
        self.columns: dict[tuple[str, str], int] = {}

    def column(self, name: str, axis: str) -> int:
        key = (name, axis)
        if key in self.columns:
            return self.columns[key]
        values = [row.get(name) for row in self.rows]
        col = self.next_col
        self.next_col += 1
        self.sheet.from_list(col, values, lname=name, axis=axis)
        self.columns[key] = col
        return col

    def derived(self, name: str, values: list[Any], axis: str) -> int:
        col = self.next_col
        self.next_col += 1
        self.sheet.from_list(col, values, lname=name, axis=axis)
        return col


def _error_path(rows: list[dict[str, Any]], mapping: dict[str, Any]) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    x_name, y_name = str(mapping["x"]), str(mapping["y"])
    yerr = mapping.get("y_error")
    xerr = mapping.get("x_error")
    for row in rows:
        x = float(row[x_name])
        y = float(row[y_name])
        if yerr:
            delta = abs(float(row[str(yerr)]))
            cap = max(abs(x) * 0.005, 1e-9)
            xs.extend([x, x, math.nan, x - cap, x + cap, math.nan, x - cap, x + cap, math.nan])
            ys.extend([y - delta, y + delta, math.nan, y - delta, y - delta, math.nan, y + delta, y + delta, math.nan])
        if xerr:
            delta = abs(float(row[str(xerr)]))
            cap = max(abs(y) * 0.005, 1e-9)
            xs.extend([x - delta, x + delta, math.nan, x - delta, x - delta, math.nan, x + delta, x + delta, math.nan])
            ys.extend([y, y, math.nan, y - cap, y + cap, math.nan, y - cap, y + cap, math.nan])
    return xs, ys


def _add_xy(layer: Any, writer: _SheetWriter, rows: list[dict[str, Any]], operation: dict[str, Any]) -> int:
    mapping = operation["mapping"]
    x_col = writer.column(str(mapping["x"]), "X")
    y_col = writer.column(str(mapping["y"]), "Y")
    kind = operation.get("kind")
    plots: list[Any] = []
    if kind == "scatter":
        plots.append(layer.add_plot(writer.sheet, colx=x_col, coly=y_col, type="scatter"))
    elif kind == "line_scatter":
        plots.append(layer.add_plot(writer.sheet, colx=x_col, coly=y_col, type="line"))
        plots.append(layer.add_plot(writer.sheet, colx=x_col, coly=y_col, type="scatter"))
    else:
        plots.append(layer.add_plot(writer.sheet, colx=x_col, coly=y_col, type="line"))
    for plot in plots:
        _style_plot(plot, dict(operation.get("style") or {}))
    if kind == "errorbar":
        error_x, error_y = _error_path(rows, mapping)
        ex_col = writer.derived(f"{operation['series_id']}_error_x", error_x, "X")
        ey_col = writer.derived(f"{operation['series_id']}_error_y", error_y, "Y")
        error_plot = layer.add_plot(writer.sheet, colx=ex_col, coly=ey_col, type="line")
        _style_plot(error_plot, {"line_width_pt": 0.8, "color": "#444444"})
        plots.append(error_plot)
    return len(plots)


def _add_bar(layer: Any, writer: _SheetWriter, operation: dict[str, Any]) -> int:
    mapping = operation["mapping"]
    x_col = writer.column(str(mapping["category"]), "X")
    y_col = writer.column(str(mapping["y"]), "Y")
    plot = layer.add_plot(writer.sheet, colx=x_col, coly=y_col, type="column")
    _style_plot(plot, dict(operation.get("style") or {}))
    return 1


def _add_matrix(layer: Any, writer: _SheetWriter, operation: dict[str, Any]) -> int:
    mapping = operation["mapping"]
    x_col = writer.column(str(mapping["x"]), "X")
    y_col = writer.column(str(mapping["y"]), "Y")
    z_col = writer.column(str(mapping["z"]), "Z")
    kind = str(operation.get("kind") or "contour")
    try:
        plot = layer.add_plot(writer.sheet, colx=x_col, coly=y_col, colz=z_col, type=kind)
    except TypeError as exc:
        raise RuntimeError(f"E523_MATRIX_PLOT_UNAVAILABLE: Origin adapter rejected {kind} XYZ plot") from exc
    _style_plot(plot, dict(operation.get("style") or {}))
    return 1


def _set_axes(layer: Any, axes: dict[str, Any]) -> None:
    for axis_name in ("x", "y"):
        config = axes.get(axis_name) or {}
        title = config.get("title")
        unit = config.get("unit")
        if title:
            text = str(title) + (f" ({unit})" if unit else "")
            try:
                layer.axis(axis_name).title = text
            except Exception:
                pass


def _export_page(page: Any, output_dir: Path) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for suffix, kind in (("png", "png"), ("pdf", "pdf"), ("tif", "tif")):
        path = output_dir / f"figure.{suffix}"
        try:
            page.save_fig(str(path), type=kind, replace=True, width=1600 if kind in {"png", "tif"} else None)
        except TypeError:
            page.save_fig(str(path), type=kind, replace=True)
        outputs[suffix] = str(path)
    return outputs


def execute_operation_plan(
    plan: OperationPlan,
    output_dir: Path,
    *,
    op_module: Any | None = None,
    session_factory: Callable[[Any], Any] | None = None,
    admin_check: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if not (admin_check or is_administrator)():
        raise RuntimeError("E120_ENVIRONMENT_MISMATCH: Origin worker requires an administrator process")
    if op_module is None:
        import originpro as op_module
    session = session_factory or attached_origin
    source_path = Path(str(plan.source["path"]))
    rows = read_table(source_path, plan.source.get("sheet"))
    if not rows:
        raise RuntimeError("E301_FIGURE_DATA_INVALID: source table has no data rows")

    workbook_name = f"{plan.figure_id}_Data"
    opju = output_dir / "figure.opju"
    build_plot_count = 0
    build_identity: dict[str, Any]
    reopen_identity: dict[str, Any]

    with session(op_module) as build_identity:
        op_module.new(asksave=False)
        book = op_module.new_book("w", lname=workbook_name)
        sheet = book[0]
        writer = _SheetWriter(sheet, rows)
        create_graph = next((item for item in plan.operations if item.get("op") == "create_graph"), None)
        if create_graph is None:
            raise RuntimeError("E520_OPERATION_PLAN_INVALID: create_graph operation is required")
        page = op_module.new_graph(lname=plan.figure_id, template=_template_for(plan), hidden=True)
        _ensure_layers(page, int(create_graph.get("layers") or 1))
        bar_layers: set[int] = set()
        stacked_layers: set[int] = set()
        for operation in plan.operations:
            layer_index = int(operation.get("layer") or 0)
            layer = page[layer_index] if len(page) > layer_index else page[0]
            name = operation.get("op")
            if name == "add_xy_plot":
                build_plot_count += _add_xy(layer, writer, rows, operation)
            elif name == "add_bar_plot":
                build_plot_count += _add_bar(layer, writer, operation)
                bar_layers.add(layer_index)
                if operation.get("kind") == "stacked_bar":
                    stacked_layers.add(layer_index)
            elif name == "add_matrix_plot":
                build_plot_count += _add_matrix(layer, writer, operation)
            elif name == "set_axes":
                _set_axes(layer, dict(operation.get("axes") or {}))
            elif name == "set_page":
                _apply_page_size(page, dict(operation.get("page") or {}))
        for layer_index in sorted(bar_layers):
            layer = page[layer_index]
            try:
                layer.group()
            except Exception:
                pass
            if layer_index in stacked_layers:
                try:
                    layer.lt_exec("layer.stack=1;")
                except Exception:
                    pass
        for index in range(len(page)):
            try:
                page[index].rescale()
            except Exception:
                pass
        try:
            page.show = True
        except Exception:
            pass
        op_module.save(str(opju))
        if not opju.is_file():
            raise RuntimeError("E501_OPJU_SAVE_FAILED: Origin did not create the OPJU")

    with session(op_module) as reopen_identity:
        if not op_module.open(str(opju), readonly=False, asksave=False):
            raise RuntimeError("E502_OPJU_REOPEN_FAILED: Origin could not reopen the OPJU")
        readback = inspect_reopened_project(op_module, expected_figure_id=plan.figure_id, expected_workbook=workbook_name)
        pages = list(op_module.pages("g"))
        page = next(item for item in pages if str(getattr(item, "lname", "")) == plan.figure_id or str(getattr(item, "name", "")) == plan.figure_id)
        exports = _export_page(page, output_dir)
        op_module.save(str(opju))

    png = output_dir / "figure.png"
    gates = {
        "opju_saved": "pass" if opju.is_file() else "failed",
        "opju_reopened": "pass",
        "editable_plot_present": "pass" if readback["plot_count"] > 0 else "failed",
        "worksheet_binding": "pass" if readback["worksheet_binding_ok"] else "failed",
        "origin_export_nonblank": "pass" if artifact_is_nonblank(png) else "failed",
        "demo_watermark_absent": "pass" if no_demo_watermark(png) else "failed",
    }
    command_success = all(value == "pass" for value in gates.values())
    return {
        "schema": "originplot.origin_worker_result.v2",
        "profile": plan.profile,
        "mode": "live",
        "command_success": command_success,
        "structure_pass": all(gates[key] == "pass" for key in ("opju_saved", "opju_reopened", "editable_plot_present", "worksheet_binding")),
        "live_origin_verified": True,
        "overall_status": "completed" if command_success else "failed",
        "build_success": True,
        "reopen_success": True,
        "editable_plot_count": readback["plot_count"],
        "worksheet_binding_ok": readback["worksheet_binding_ok"],
        "export_nonblank": gates["origin_export_nonblank"] == "pass",
        "demo_watermark_detected": gates["demo_watermark_absent"] != "pass",
        "gate_results": gates,
        "readback": readback,
        "exports": exports,
        "opju": str(opju),
        "origin_session": {"mode": "administrator_attach_existing_authorized_two_phase", "build": build_identity, "reopen": reopen_identity},
        "build_plot_count": build_plot_count,
    }
