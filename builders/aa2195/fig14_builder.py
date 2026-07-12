from __future__ import annotations

import math
from typing import Any

from .common_origin_utils import create_hidden_graph_page, disable_speed_mode, page_dot_command, page_percent_layer_command, remove_default_labels, reveal_graph_page


TEMPERATURE = [250.0, 300.0, 350.0, 400.0]
SERIES = {
    "PSC": {"y": [0.035, 0.070, 0.128, 0.185], "err": [0.008, 0.012, 0.018, 0.010], "color": "#ef4b4b", "symbol": 1},
    "UC": {"y": [0.060, 0.102, 0.155, 0.240], "err": [0.007, 0.011, 0.018, 0.013], "color": "#2675d8", "symbol": 2},
    "TR": {"y": [0.092, 0.150, 0.190, 0.270], "err": [0.010, 0.030, 0.015, 0.010], "color": "#35a66b", "symbol": 3},
}


def _style_line(plot: Any, color: str, *, width: float = 1.2, dotted: bool = True) -> None:
    try:
        plot.color = color
    except Exception:
        pass
    for prop in ("line.width", "width"):
        try:
            plot.set_float(prop, width)
        except Exception:
            pass
    if dotted:
        for prop in ("line.style", "style"):
            try:
                plot.set_int(prop, 1)
            except Exception:
                pass
        try:
            plot.lt_exec("set %C -d 1;")
        except Exception:
            pass


def _style_symbol(plot: Any, color: str, symbol: int) -> None:
    try:
        plot.color = color
    except Exception:
        pass
    for prop in ("symbol.kind", "symbol.type", "symbol"):
        try:
            plot.set_int(prop, symbol)
        except Exception:
            pass
    for prop in ("symbol.size", "size"):
        try:
            plot.set_float(prop, 10.5)
        except Exception:
            pass


def _error_paths(y: list[float], err: list[float]) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    half_cap = 3.0
    for x, center, delta in zip(TEMPERATURE, y, err):
        low, high = center - delta, center + delta
        xs.extend([x, x, math.nan, x - half_cap, x + half_cap, math.nan, x - half_cap, x + half_cap, math.nan])
        ys.extend([low, high, math.nan, low, low, math.nan, high, high, math.nan])
    return xs, ys


def _name_label(label: Any, name: str, size: float = 18.0) -> None:
    if label is None:
        return
    try:
        label.obj.SetName(name)
    except Exception:
        pass
    try:
        label.set_int("attach", 2)
        label.set_float("fsize", size)
    except Exception:
        pass


def build(op: Any, candidate_params: dict[str, Any]) -> dict[str, Any]:
    page_size_inches = (8.0, 6.45)
    page = create_hidden_graph_page(op, lname="Fig14_source_calibrated_errorbar", template="LINE")
    page.lt_exec(page_dot_command(*page_size_inches, page.get_float("resx"), page.get_float("resy")))
    layer = page[0]
    book_name = "Fig14_recrystallization_fraction_source_values"
    sheet = op.new_book(lname=book_name)[0]
    plot_count = 0
    line_plot_numbers: dict[str, int] = {}
    styled_lines: list[tuple[Any, str]] = []
    column = 0
    contracts = []
    for mode in ("PSC", "UC", "TR"):
        record = SERIES[mode]
        error_x, error_y = _error_paths(record["y"], record["err"])
        sheet.from_list(column, TEMPERATURE, lname=f"temperature_{mode}", axis="X")
        sheet.from_list(column + 1, record["y"], lname=f"fraction_{mode}", axis="Y")
        line = layer.add_plot(sheet, colx=column, coly=column + 1, type="line")
        _style_line(line, record["color"])
        _style_symbol(line, record["color"], int(record["symbol"]))
        styled_lines.append((line, str(record["color"])))
        line_plot_numbers[mode] = plot_count + 1
        contracts.append({"layer_index": 0, "plot_index": plot_count, "plot_type_code": 202, "x_column": chr(ord("A") + column), "y_column": chr(ord("A") + column + 1)})
        plot_count += 1
        sheet.from_list(column + 2, error_x, lname=f"error_x_{mode}", axis="X")
        sheet.from_list(column + 3, error_y, lname=f"error_y_{mode}", axis="Y")
        errors = layer.add_plot(sheet, colx=column + 2, coly=column + 3, type="line")
        _style_line(errors, "#444444", width=0.8, dotted=False)
        contracts.append({"layer_index": 0, "plot_index": plot_count, "plot_type_code": 200, "x_column": chr(ord("A") + column + 2), "y_column": chr(ord("A") + column + 3)})
        plot_count += 1
        column += 4

    for line, color in styled_lines:
        _style_line(line, color)

    layer.set_xlim(230.0, 420.0)
    layer.set_ylim(0.0, 0.4)
    layer.lt_exec(page_percent_layer_command((14.0, 4.3, 80.0, 80.0)))
    remove_default_labels(layer)
    layer.lt_exec(
        "layer.x.from=230; layer.x.to=420; layer.x.inc=50; layer.x.minorTicks=1; "
        "layer.y.from=0; layer.y.to=0.4; layer.y.inc=0.1; layer.y.minorTicks=1; "
        "layer.x.opposite=1; layer.y.opposite=1; layer.x.showopposite=1; layer.y.showopposite=1; "
        "label -xb \"Temperature/°C\"; label -yl \"Recrystallization fraction\"; yl.rotate=90; "
        "layer.x.label.fsize=20; layer.y.label.fsize=20; xb.fsize=24; yl.fsize=24;"
    )
    legend_text = "\n".join(f"\\l({line_plot_numbers[mode]}) {mode}" for mode in ("PSC", "UC", "TR"))
    legend = layer.add_label(legend_text, 242.0, 0.37)
    _name_label(legend, "fig14_legend", 24.0)
    disable_speed_mode(layer)
    visibility = reveal_graph_page(page)
    return {
        "page_name": "Fig14_source_calibrated_errorbar",
        "expected_plot_count": plot_count,
        "expected_plot_count_by_layer": {0: plot_count},
        "route": "worksheet_backed_source_calibrated_line_symbol_error_paths",
        "canvas_size": (800, 645),
        "page_size_inches": page_size_inches,
        "required_worksheet_books": [book_name],
        "direct_worksheet_plot_contracts": contracts,
        "required_graphobject_names_by_layer": {0: ["fig14_legend"]},
        "required_graphobject_contracts": {"fig14_legend": {"attach": 2, "text_contains": "PSC"}},
        "expected_graphobject_count": 1,
        "construction_visibility": visibility,
        "reproduction_mode": "source_calibrated_reconstructed_approximate",
        "data_provenance": "values and error-bar extents digitized from AA2195 Fig. 14",
        "candidate_params": candidate_params,
    }
