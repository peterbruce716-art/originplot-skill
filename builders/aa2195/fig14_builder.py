from __future__ import annotations

import math
from typing import Any

import numpy as np

from .common_origin_utils import create_hidden_graph_page, disable_speed_mode, page_dot_command, page_percent_layer_command, remove_default_labels, reveal_graph_page
from .source_geometry import source_geometry_contract


TEMPERATURE = [250.0, 300.0, 350.0, 400.0]
FIG14_FONT = "Times New Roman"
FIG14_FONT_ID = 429
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


def _style_marker(plot: Any, color: str, symbol: int) -> None:
    """Keep symbols while suppressing the connecting line in the marker overlay."""
    _style_symbol(plot, color, symbol)
    for prop in ("line.width", "width"):
        try:
            plot.set_float(prop, 0.0)
        except Exception:
            pass


def _patterned_series(x: list[float], y: list[float], mode: str) -> tuple[list[float], list[float]]:
    """Encode source dash patterns as editable NaN-separated Worksheet data."""
    if mode == "PSC":
        return list(x), list(y)
    dense_x = np.linspace(float(x[0]), float(x[-1]), 441)
    dense_y = np.interp(dense_x, np.asarray(x, dtype=float), np.asarray(y, dtype=float))
    phase = np.mod(dense_x - float(x[0]), 10.0 if mode == "UC" else 20.0)
    if mode == "UC":
        visible = phase < 4.0
    else:
        visible = (phase < 8.0) | ((phase >= 12.0) & (phase < 14.0))
    dense_y = dense_y.astype(float)
    dense_y[~visible] = np.nan
    return dense_x.tolist(), dense_y.tolist()


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
        label.set_int("font", FIG14_FONT_ID)
    except Exception:
        pass
    try:
        label.lt_exec(f"{name}.font=font({FIG14_FONT});")
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
    marker_plot_numbers: dict[str, int] = {}
    styled_lines: list[tuple[Any, str]] = []
    column = 0
    contracts = []
    series_plot_contracts = []
    source_groups: list[dict[str, Any]] = []
    for mode in ("PSC", "UC", "TR"):
        record = SERIES[mode]
        error_x, error_y = _error_paths(record["y"], record["err"])
        patterned_x, patterned_y = _patterned_series(TEMPERATURE, record["y"], mode)
        sheet.from_list(column, patterned_x, lname=f"temperature_{mode}_patterned", axis="X")
        sheet.from_list(column + 1, patterned_y, lname=f"fraction_{mode}_patterned", axis="Y")
        line = layer.add_plot(sheet, colx=column, coly=column + 1, type="line")
        _style_line(line, record["color"])
        styled_lines.append((line, str(record["color"])))
        line_plot_numbers[mode] = plot_count + 1
        contracts.append({"layer_index": 0, "plot_index": plot_count, "plot_type_code": 200, "x_column": chr(ord("A") + column), "y_column": chr(ord("A") + column + 1)})
        plot_count += 1
        marker_column = column + 2
        sheet.from_list(marker_column, TEMPERATURE, lname=f"temperature_{mode}_markers", axis="X")
        sheet.from_list(marker_column + 1, record["y"], lname=f"fraction_{mode}_markers", axis="Y")
        markers = layer.add_plot(sheet, colx=marker_column, coly=marker_column + 1, type="line")
        _style_marker(markers, record["color"], int(record["symbol"]))
        marker_plot_numbers[mode] = plot_count + 1
        contracts.append({"layer_index": 0, "plot_index": plot_count, "plot_type_code": 202, "x_column": chr(ord("A") + marker_column), "y_column": chr(ord("A") + marker_column + 1)})
        plot_count += 1
        error_column = column + 4
        sheet.from_list(error_column, error_x, lname=f"error_x_{mode}", axis="X")
        sheet.from_list(error_column + 1, error_y, lname=f"error_y_{mode}", axis="Y")
        errors = layer.add_plot(sheet, colx=error_column, coly=error_column + 1, type="line")
        _style_line(errors, "#444444", width=0.8, dotted=False)
        contracts.append({"layer_index": 0, "plot_index": plot_count, "plot_type_code": 200, "x_column": chr(ord("A") + error_column), "y_column": chr(ord("A") + error_column + 1)})
        series_plot_contracts.append({"mode": mode, "line_plot": line_plot_numbers[mode], "marker_plot": marker_plot_numbers[mode]})
        source_groups.append({
            "group_id": f"fig14.{mode}.fraction",
            "canonical_source": {
                "source_id": f"fig14.SERIES.{mode}",
                "kind": "temperature_fraction_error_anchors",
            },
            "continuity": "single_xy" if mode == "PSC" else "nan_separated_xy",
            "same_worksheet": True,
            "consumers": [
                {
                    "consumer_id": "continuous_curve",
                    "kind": "plot",
                    "view": "canonical",
                    "layer_index": 0,
                    "plot_index": line_plot_numbers[mode] - 1,
                    "x_column": chr(ord("A") + column),
                    "y_column": chr(ord("A") + column + 1),
                },
                {
                    "consumer_id": "anchor_markers",
                    "kind": "plot",
                    "view": "derived",
                    "derivation": "identity anchor view before NaN dash expansion",
                    "layer_index": 0,
                    "plot_index": marker_plot_numbers[mode] - 1,
                    "x_column": chr(ord("A") + marker_column),
                    "y_column": chr(ord("A") + marker_column + 1),
                },
                {
                    "consumer_id": "error_paths",
                    "kind": "plot",
                    "view": "derived",
                    "derivation": "vertical interval and cap path from the same anchors and err values",
                    "layer_index": 0,
                    "plot_index": plot_count,
                    "x_column": chr(ord("A") + error_column),
                    "y_column": chr(ord("A") + error_column + 1),
                },
            ],
        })
        plot_count += 1
        column += 6

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
        f"layer.x.label.font=font({FIG14_FONT}); layer.y.label.font=font({FIG14_FONT}); "
        f"xb.font=font({FIG14_FONT}); yl.font=font({FIG14_FONT}); "
        "layer.x.label.fsize=20; layer.y.label.fsize=20; xb.fsize=22; yl.fsize=24;"
    )
    legend_text = "\n".join(f"\\l({line_plot_numbers[mode]})\\l({marker_plot_numbers[mode]}) {mode}" for mode in ("PSC", "UC", "TR"))
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
        "subplot_worksheet_contracts": [{
            "subplot_id": "fig14_recrystallization_fraction",
            "layer_index": 0,
            "expected_plot_count": plot_count,
            "worksheet_books": [book_name],
            "worksheet_names": ["Sheet1"],
        }],
        "legend_plot_reference_contracts": [{
            "object_name": "fig14_legend",
            "layer_index": 0,
            "plot_numbers": [
                number
                for mode in ("PSC", "UC", "TR")
                for number in (line_plot_numbers[mode], marker_plot_numbers[mode])
            ],
            "text_contains": "PSC",
        }],
        "series_plot_contracts": series_plot_contracts,
        "source_geometry_groups": source_geometry_contract(source_groups),
        "required_graphobject_names_by_layer": {0: ["fig14_legend"]},
        "required_graphobject_contracts": {"fig14_legend": {"attach": 2, "text_contains": "PSC"}},
        "expected_graphobject_count": 1,
        "construction_visibility": visibility,
        "reproduction_mode": "source_calibrated_reconstructed_approximate",
        "data_provenance": "values and error-bar extents digitized from AA2195 Fig. 14",
        "font_profile": FIG14_FONT,
        "candidate_params": candidate_params,
    }
