from __future__ import annotations

from typing import Any

import math

from .common_origin_utils import (
    axisless_layer_command,
    create_hidden_graph_page,
    disable_speed_mode,
    origin_font_size,
    page_dot_command,
    page_percent_layer_command,
    remove_default_labels,
    reveal_graph_page,
)
from .geometry import fig15_geometry


TEXT_Y_OFFSETS = {
    "panel": -10.0,
    "title": -15.0,
    "axis": -8.0,
    "stress": -6.0,
    "stage": -6.0,
    "header_stage": -4.0,
    "description": -4.0,
}


def _candidate_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _text_size(record: dict[str, Any], candidate_params: dict[str, Any]) -> float:
    role = str(record["role"])
    global_scale = _candidate_float(candidate_params.get("text_scale"), 1.0)
    role_scales = candidate_params.get("text_role_scales", {})
    role_scale = (
        _candidate_float(role_scales.get(role), 1.0)
        if isinstance(role_scales, dict)
        else 1.0
    )
    return float(record["font_size"]) * global_scale * role_scale


def _set_plot_style(plot: Any, *, color: str, width: float, dotted: bool = False) -> None:
    try:
        plot.color = color
    except Exception:
        try:
            plot.set_str("color", color)
        except Exception:
            pass
    for prop in ["line.width", "width"]:
        try:
            plot.set_float(prop, width)
        except Exception:
            pass
    if dotted:
        for prop in ["line.style", "style"]:
            try:
                plot.set_int(prop, 2)
            except Exception:
                pass


def _set_layer_frame(layer: Any, frame: tuple[float, float, float, float]) -> None:
    left, top, width, height = frame
    command = page_percent_layer_command(frame)
    layer.lt_exec(command)
    for prop, value in {"left": left, "top": top, "width": width, "height": height}.items():
        try:
            layer.set_float(prop, value)
        except Exception:
            pass


def _set_object_name(obj: Any, name: str) -> None:
    try:
        obj.obj.SetName(name)
        return
    except Exception:
        pass
    try:
        obj.name = name
    except Exception:
        pass


def _add_scale_label(
    layer: Any,
    panel: dict[str, Any],
    name: str,
    text: str,
    source_x: float,
    source_y: float,
    size: float,
) -> bool:
    left, top, right, bottom = panel["axis_bounds_source_pixels"]
    local_x = (float(source_x) - left) / (right - left)
    local_y = (bottom - float(source_y)) / (bottom - top)
    try:
        label = layer.add_label(text, local_x, local_y)
        if label is None:
            return False
        _set_object_name(label, name)
        try:
            label.set_int("attach", 2)
        except Exception:
            pass
        for prop, value in {"x1": local_x, "y1": local_y, "fsize": origin_font_size(size)}.items():
            try:
                label.set_float(prop, float(value))
            except Exception:
                pass
        return True
    except Exception:
        return False


def _combine_circles(circles: list[dict[str, Any]]) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for circle in circles:
        xs.extend(circle["x"])
        ys.extend(circle["y"])
        xs.append(math.nan)
        ys.append(math.nan)
    return xs, ys


def _add_panel(op: Any, layer: Any, panel: dict[str, Any]) -> int:
    book = op.new_book(lname=f"Fig15_{panel['name']}_source_calibrated_paths")
    sheet = book[0]
    circle_x, circle_y = _combine_circles(panel["stage_circles"])
    header_circle_x, header_circle_y = _combine_circles(panel["header_circles"])
    paths = [
        ("axes", panel["axes"]["x"], panel["axes"]["y"], "black", 1.8, False),
        ("guides", panel["guides"]["x"], panel["guides"]["y"], "#ff8c3a", 0.85, True),
        ("curve", panel["curve"]["x"], panel["curve"]["y"], "#1b35ff", 2.0, False),
        ("stage_circles", circle_x, circle_y, "black", 0.8, False),
        ("header_circles", header_circle_x, header_circle_y, "black", 0.65, False),
    ]
    column = 0
    for name, xs, ys, color, width, dotted in paths:
        sheet.from_list(column, list(xs), lname=f"{name}_x", axis="X")
        sheet.from_list(column + 1, list(ys), lname=f"{name}_y", axis="Y")
        plot = layer.add_plot(sheet, colx=column, coly=column + 1, type="line")
        _set_plot_style(plot, color=color, width=width, dotted=dotted)
        column += 2

    layer.set_xlim(0.0, 1.0)
    layer.set_ylim(0.0, 1.0)
    _set_layer_frame(layer, panel["frame_percent"])
    remove_default_labels(layer)
    try:
        layer.lt_exec(axisless_layer_command())
    except Exception:
        pass
    disable_speed_mode(layer)
    return len(paths)


def build(op: Any, candidate_params: dict[str, Any]) -> dict[str, Any]:
    geometry = fig15_geometry()
    page_size_inches = (8.5, 3.35)
    page = create_hidden_graph_page(
        op,
        lname="Fig15_source_calibrated_two_layer",
        template="LINE",
    )
    page.lt_exec(
        page_dot_command(
            *page_size_inches,
            page.get_float("resx"),
            page.get_float("resy"),
        )
    )
    disable_speed_mode(page)
    left = page[0]
    right = page.add_layer()
    panels = geometry["panels"]
    plot_count = _add_panel(op, left, panels[0]) + _add_panel(op, right, panels[1])
    required_worksheet_books = [
        f"Fig15_{panel['name']}_source_calibrated_paths" for panel in panels
    ]
    worksheet_binding_inventory = [
        {
            "worksheet_name": name,
            "association_mode": "direct_worksheet_plot_binding",
            "target_layer_index": index,
            "target_plot_count": 5,
        }
        for index, name in enumerate(required_worksheet_books)
    ]

    label_inventory: list[dict[str, Any]] = []
    required_graphobject_contracts: dict[str, dict[str, Any]] = {}
    expected_names_by_layer: dict[int, list[str]] = {0: [], 1: []}
    for index, record in enumerate(geometry["labels"], start=1):
        object_name = f"fig15_label_{index:02d}"
        is_left = float(record["x"]) < 425.0 and str(record["text"]) != "(b)"
        layer_index = 0 if is_left else 1
        layer = left if is_left else right
        panel = panels[layer_index]
        source_y_adjusted = float(record["y"]) + TEXT_Y_OFFSETS.get(str(record["role"]), 0.0)
        created = _add_scale_label(
            layer,
            panel,
            object_name,
            str(record["text"]),
            float(record["x"]),
            source_y_adjusted,
            _text_size(record, candidate_params),
        )
        label_inventory.append(
            {
                **record,
                "name": object_name,
                "attach": 2,
                "layer_index": layer_index,
                "source_y_adjusted": source_y_adjusted,
                "effective_font_size": _text_size(record, candidate_params),
                "created": created,
            }
        )
        required_graphobject_contracts[object_name] = {"attach": 2}
        expected_names_by_layer[layer_index].append(object_name)

    caption_text = str(candidate_params.get("caption_text", geometry["caption"]))
    caption_created = _add_scale_label(
        left,
        panels[0],
        "fig15_caption",
        caption_text,
        153.0,
        307.0,
        _candidate_float(candidate_params.get("caption_font_size"), 9.0),
    )
    label_inventory.append(
        {
            "role": "caption",
            "name": "fig15_caption",
            "text": caption_text,
            "attach": 2,
            "layer_index": 0,
            "effective_font_size": _candidate_float(candidate_params.get("caption_font_size"), 9.0),
            "created": caption_created,
        }
    )
    required_graphobject_contracts["fig15_caption"] = {"attach": 2, "text_contains": "Fig. 15."}
    expected_names_by_layer[0].append("fig15_caption")
    axis_contract = [
        {
            "layer_index": index,
            "x.showAxes": 0,
            "y.showAxes": 0,
            "x.showLabels": 0,
            "y.showLabels": 0,
            "x.ticks": 0,
            "y.ticks": 0,
            "x.arrow.show": 0,
            "y.arrow.show": 0,
        }
        for index in range(2)
    ]
    construction_visibility = reveal_graph_page(page)
    return {
        "page_name": "Fig15_source_calibrated_two_layer",
        "expected_plot_count": plot_count,
        "expected_plot_count_by_layer": {0: 5, 1: 5},
        "route": "worksheet_backed_source_calibrated_two_layer",
        "coordinate_mode": "normalized_0_1_panel_coordinates",
        "canvas_size": geometry["canvas"],
        "page_size_inches": page_size_inches,
        "label_inventory": label_inventory,
        "required_worksheet_books": required_worksheet_books,
        "max_direct_plot_worksheet_rows": 5000,
        "worksheet_binding_inventory": worksheet_binding_inventory,
        "direct_worksheet_plot_contracts": [
            {
                "layer_index": layer_index,
                "plot_index": plot_index,
                "plot_type_code": 200,
                "x_column": chr(ord("A") + plot_index * 2),
                "y_column": chr(ord("B") + plot_index * 2),
            }
            for layer_index in range(2)
            for plot_index in range(5)
        ],
        "axis_route": "worksheet_arrowhead_paths",
        "axis_arrowhead_segment_count": sum(panel["axes"]["arrowhead_segment_count"] for panel in panels),
        "axis_contract": axis_contract,
        "required_graphobject_names_by_layer": expected_names_by_layer,
        "required_graphobject_contracts": required_graphobject_contracts,
        "expected_graphobject_count": len(required_graphobject_contracts),
        "construction_visibility": construction_visibility,
        "unexpected_legend_expected": 0,
        "reproduction_mode": geometry["provenance"],
        "text_calibration": {
            "text_scale": _candidate_float(candidate_params.get("text_scale"), 1.0),
            "text_role_scales": candidate_params.get("text_role_scales", {}),
            "caption_font_size": _candidate_float(candidate_params.get("caption_font_size"), 9.0),
        },
        "candidate_params": candidate_params,
    }
