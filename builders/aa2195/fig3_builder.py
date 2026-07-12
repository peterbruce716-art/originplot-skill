from __future__ import annotations

from typing import Any

import numpy as np

from .common_origin_utils import create_hidden_graph_page, disable_speed_mode, page_dot_command, page_percent_layer_command, remove_default_labels, reveal_graph_page
from .fig3_data import COLORS, LINE_STYLES, PANELS


FIG3_FONT = "Times New Roman"
FIG3_FONT_ID = 429


def _set_plot_style(plot: Any, color: str, line_style: int) -> None:
    try:
        plot.color = color
    except Exception:
        pass
    for prop, value in (("line.width", 3.5), ("width", 3.5)):
        try:
            plot.set_float(prop, value)
        except Exception:
            pass
    for prop in ("line.style", "style"):
        try:
            plot.set_int(prop, int(line_style))
        except Exception:
            pass
    try:
        plot.lt_exec(f"set %C -d {int(line_style)};")
    except Exception:
        pass


def _name_label(
    label: Any,
    name: str,
    size: float = 9.0,
    *,
    color: str | None = None,
    bold: bool = False,
) -> None:
    if label is None:
        return
    try:
        label.obj.SetName(name)
    except Exception:
        pass
    try:
        label.set_int("attach", 2)
        label.set_float("fsize", size)
        label.set_int("font", FIG3_FONT_ID)
        label.set_int("fontWeight", 700 if bold else 400)
    except Exception:
        pass
    if color is not None:
        try:
            label.color = color
        except Exception:
            pass
    try:
        label.lt_exec(f"{name}.font=font({FIG3_FONT});")
    except Exception:
        pass


def _patterned_series(x: list[float], y: list[float], mode: str) -> tuple[list[float], list[float]]:
    if mode == "PSC":
        return list(x), list(y)
    dense_x = np.linspace(float(x[0]), float(x[-1]), 441)
    dense_y = np.interp(dense_x, np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    if mode == "UC":
        phase = np.mod(dense_x, 0.035)
        visible = phase < 0.012
    else:
        phase = np.mod(dense_x, 0.070)
        visible = (phase < 0.035) | ((phase >= 0.047) & (phase < 0.053))
    dense_y = dense_y.astype(float)
    dense_y[~visible] = np.nan
    return dense_x.tolist(), dense_y.tolist()


def _legend_segment(start: float, end: float, y: float, mode: str) -> tuple[list[float], list[float]]:
    """Return a short editable legend segment whose gaps survive OPJU reopen."""
    if mode == "PSC":
        return [start, end], [y, y]
    dense_x = np.linspace(float(start), float(end), 81)
    phase = np.linspace(0.0, 1.0, 81, endpoint=False)
    if mode == "UC":
        visible = np.mod(phase, 0.18) < 0.045
    else:
        cycle = np.mod(phase, 0.42)
        visible = (cycle < 0.22) | ((cycle >= 0.30) & (cycle < 0.335))
    dense_y = np.full(dense_x.shape, float(y), dtype=float)
    dense_y[~visible] = np.nan
    return dense_x.tolist(), dense_y.tolist()


def _column_name(index: int) -> str:
    if not 0 <= index < 26:
        raise ValueError("Fig3 worksheet columns must remain within A:Z")
    return chr(ord("A") + index)


def _add_panel(
    op: Any,
    layer: Any,
    panel: dict[str, Any],
    layer_index: int,
) -> tuple[int, list[str], list[str], list[dict[str, Any]]]:
    book_name = f"Fig3_{panel['name']}_source_calibrated_curves"
    sheet = op.new_book(lname=book_name)[0]
    column = 0
    plot_count = 0
    plot_styles: list[tuple[Any, str, int]] = []
    plot_contracts: list[dict[str, Any]] = []
    for temperature in ("250", "300", "350", "400"):
        for mode in ("PSC", "UC", "TR"):
            record = panel["series"].get(temperature, {}).get(mode)
            if record is None:
                continue
            plot_x, plot_y = _patterned_series(record["x"], record["y"], mode)
            sheet.from_list(column, plot_x, lname=f"strain_{temperature}_{mode}", axis="X")
            sheet.from_list(column + 1, plot_y, lname=f"stress_{temperature}_{mode}", axis="Y")
            plot = layer.add_plot(sheet, colx=column, coly=column + 1, type="line")
            _set_plot_style(plot, COLORS[temperature], LINE_STYLES[mode])
            plot_styles.append((plot, COLORS[temperature], LINE_STYLES[mode]))
            plot_contracts.append({
                "layer_index": layer_index,
                "plot_index": plot_count,
                "plot_type_code": 200,
                "x_column": _column_name(column),
                "y_column": _column_name(column + 1),
            })
            plot_count += 1
            column += 2

    # Origin may refresh grouped plot styles while subsequent plots are added.
    # Reapply after the group is complete so the saved OPJU retains mode dashes.
    for plot, color, line_style in plot_styles:
        _set_plot_style(plot, color, line_style)

    layer.set_xlim(0.0, 1.1)
    layer.set_ylim(0.0, float(panel["ymax"]))
    layer.lt_exec(page_percent_layer_command(tuple(panel["frame_percent"])))
    remove_default_labels(layer)
    y_major = 50
    layer.lt_exec(
        "layer.x.from=0; layer.x.to=1.1; layer.x.inc=0.2; layer.x.minorTicks=1; "
        f"layer.y.from=0; layer.y.to={float(panel['ymax']):g}; layer.y.inc={y_major}; layer.y.minorTicks=1; "
        "layer.x.opposite=1; layer.y.opposite=1; layer.x.showopposite=1; layer.y.showopposite=1; "
        "label -xb \"Equivalent strain\"; label -yl \"Equivalent stress/MPa\"; yl.rotate=90; "
        f"layer.x.label.font=font({FIG3_FONT}); layer.y.label.font=font({FIG3_FONT}); "
        f"xb.font=font({FIG3_FONT}); yl.font=font({FIG3_FONT}); "
        "layer.x.label.fsize=32; layer.y.label.fsize=32; xb.fsize=38; yl.fsize=38;"
    )
    labels: list[str] = []
    panel_label = layer.add_label(panel["panel"], -0.27, float(panel["ymax"]) * 1.04)
    panel_name = f"fig3_panel_{panel['name']}"
    _name_label(panel_label, panel_name, 38.0)
    labels.append(panel_name)
    modes = ("PSC", "UC") if panel["name"] == "d" else ("PSC", "UC", "TR")
    legend_book_name = f"Fig3_{panel['name']}_editable_legend_segments"
    legend_sheet = op.new_book(lname=legend_book_name)[0]
    legend_column = 0
    legend_y_fractions = {"PSC": 0.94, "UC": 0.86, "TR": 0.78}
    for mode in modes:
        legend_y = float(panel["ymax"]) * legend_y_fractions[mode]
        for color_index, temperature in enumerate(("250", "300", "350", "400")):
            start = 0.055 + color_index * 0.148
            end = start + 0.128
            legend_x, legend_y_values = _legend_segment(start, end, legend_y, mode)
            legend_sheet.from_list(legend_column, legend_x, lname=f"legend_x_{mode}_{temperature}", axis="X")
            legend_sheet.from_list(legend_column + 1, legend_y_values, lname=f"legend_y_{mode}_{temperature}", axis="Y")
            legend_plot = layer.add_plot(legend_sheet, colx=legend_column, coly=legend_column + 1, type="line")
            _set_plot_style(legend_plot, COLORS[temperature], LINE_STYLES["PSC"])
            plot_contracts.append({
                "layer_index": layer_index,
                "plot_index": plot_count,
                "plot_type_code": 200,
                "x_column": _column_name(legend_column),
                "y_column": _column_name(legend_column + 1),
            })
            plot_count += 1
            legend_column += 2
        legend = layer.add_label(mode, 0.655, legend_y)
        legend_name = f"fig3_legend_{panel['name']}_{mode.lower()}"
        _name_label(legend, legend_name, 31.0)
        labels.append(legend_name)
    label_y = {temp: panel["series"][temp]["PSC"]["y"][-1] for temp in panel["series"]}
    for temperature, y_value in label_y.items():
        label = layer.add_label(f"{temperature}°C", 0.92, float(y_value))
        name = f"fig3_temp_{panel['name']}_{temperature}"
        _name_label(label, name, 31.0, color=COLORS[temperature], bold=True)
        labels.append(name)
    disable_speed_mode(layer)
    return plot_count, [book_name, legend_book_name], labels, plot_contracts


def build(op: Any, candidate_params: dict[str, Any]) -> dict[str, Any]:
    page_size_inches = (12.45, 9.0)
    page = create_hidden_graph_page(op, lname="Fig3_source_calibrated_four_panel", template="LINE")
    page.lt_exec(page_dot_command(*page_size_inches, page.get_float("resx"), page.get_float("resy")))
    layers = [page[0], page.add_layer(), page.add_layer(), page.add_layer()]
    counts: dict[int, int] = {}
    books: list[str] = []
    names_by_layer: dict[int, list[str]] = {}
    contracts: dict[str, dict[str, Any]] = {}
    plot_contracts: list[dict[str, Any]] = []
    for index, (layer, panel) in enumerate(zip(layers, PANELS)):
        count, panel_books, names, panel_plot_contracts = _add_panel(op, layer, panel, index)
        counts[index] = count
        books.extend(panel_books)
        names_by_layer[index] = names
        contracts.update({name: {"attach": 2} for name in names})
        plot_contracts.extend(panel_plot_contracts)
    visibility = reveal_graph_page(page)
    return {
        "page_name": "Fig3_source_calibrated_four_panel",
        "expected_plot_count": sum(counts.values()),
        "expected_plot_count_by_layer": counts,
        "route": "worksheet_backed_source_calibrated_four_layer_line",
        "canvas_size": (1245, 900),
        "page_size_inches": page_size_inches,
        "required_worksheet_books": books,
        "direct_worksheet_plot_contracts": plot_contracts,
        "required_graphobject_names_by_layer": names_by_layer,
        "required_graphobject_contracts": contracts,
        "expected_graphobject_count": len(contracts),
        "axis_contract": [],
        "construction_visibility": visibility,
        "reproduction_mode": "source_calibrated_reconstructed_approximate",
        "data_provenance": "manual source-curve anchors from AA2195 Fig. 3 vector render",
        "font_profile": FIG3_FONT,
        "font_sizes": {"axis_tick": 32.0, "axis_title": 38.0, "panel": 38.0, "legend": 31.0, "temperature": 31.0},
        "candidate_params": candidate_params,
    }
