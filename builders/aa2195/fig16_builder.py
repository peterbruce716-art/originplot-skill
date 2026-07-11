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
from .geometry import fig16_geometry


HEIGHT = 375.0
GRAPHOBJECT_LINE_TYPE = 4
GRAPHOBJECT_RECTANGLE_TYPE = 8
GRAPHOBJECT_ELLIPSE_TYPE = 9
RECTANGLE_LINE_WIDTH = 1.0
ELLIPSE_LINE_WIDTH = 1.0
FIG16_TUNING_KEYS = {
    "header_dx",
    "header_dy",
    "legend_dx",
    "legend_dy",
    "bar_top_dy",
    "bar_bottom_dy",
    "group_label_dx",
    "group_label_dy",
    "stage_circle_dx",
    "stage_circle_dy",
    "stage_text_dx",
    "stage_text_dy",
    "relation_text_dx",
    "relation_text_dy",
}
DEFAULT_FIG16_TUNING = {
    "bar_top_dy": -1.0,
    "bar_bottom_dy": 1.0,
    "legend_dy": 3.0,
}
FIG16_COLOR_KEYS = {"WH", "DRV", "DRX"}
FIG16_TEXT_SIZE_KEYS = {
    "header": 10.0,
    "legend": 9.5,
    "group_label": 12.0,
    "stage": 9.0,
    "relation": 10.0,
}


def _origin_y(source_y: float) -> float:
    return HEIGHT - float(source_y)


def _stack_chart_y(source_y: float) -> float:
    """Map source pixels to the shared stack-chart coordinate system."""
    return 334.0 - float(source_y)


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _valid_hex_color(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if text.startswith("#"):
        text = text[1:]
    if len(text) != 6:
        return None
    if any(char not in "0123456789abcdefABCDEF" for char in text):
        return None
    return f"#{text.lower()}"


def _bounded_float(value: Any, *, default: float = 0.0, limit: float = 8.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(-limit, min(limit, number))


def _fig16_tuning(candidate_params: dict[str, Any]) -> dict[str, float]:
    raw = candidate_params.get("fig16_tuning") if isinstance(candidate_params, dict) else None
    if not isinstance(raw, dict):
        raw = {}
    tuning: dict[str, float] = {}
    for key in FIG16_TUNING_KEYS:
        default = float(DEFAULT_FIG16_TUNING.get(key, 0.0))
        fallback = candidate_params.get(key, default) if isinstance(candidate_params, dict) else default
        tuning[key] = _bounded_float(raw.get(key, fallback), default=default)
    return tuning


def _fig16_text_sizes(candidate_params: dict[str, Any]) -> dict[str, float]:
    raw_sizes = candidate_params.get("fig16_text_sizes") if isinstance(candidate_params, dict) else None
    if not isinstance(raw_sizes, dict):
        raw_sizes = {}
    raw_offsets = candidate_params.get("fig16_text_size_offsets") if isinstance(candidate_params, dict) else None
    if not isinstance(raw_offsets, dict):
        raw_offsets = {}
    sizes: dict[str, float] = {}
    for key, default in FIG16_TEXT_SIZE_KEYS.items():
        absolute = raw_sizes.get(key)
        if absolute is None and isinstance(candidate_params, dict):
            absolute = candidate_params.get(f"{key}_font_size")
        if absolute is not None:
            sizes[key] = max(6.0, min(18.0, _bounded_float(absolute, default=default, limit=18.0)))
            continue
        offset = _bounded_float(raw_offsets.get(key), default=0.0, limit=2.0)
        sizes[key] = max(6.0, min(18.0, default + offset))
    return sizes


def _apply_fig16_color_candidate(
    geometry: dict[str, Any],
    candidate_params: dict[str, Any],
) -> dict[str, str]:
    raw = candidate_params.get("fig16_colors") if isinstance(candidate_params, dict) else None
    current = {str(key): str(value) for key, value in (geometry.get("colors") or {}).items()}
    if not isinstance(raw, dict):
        return current
    overrides: dict[str, str] = {}
    for key, value in raw.items():
        label = str(key).upper()
        color = _valid_hex_color(value)
        if label in FIG16_COLOR_KEYS and color is not None:
            overrides[label] = color
    if not overrides:
        return current
    current.update(overrides)
    geometry["colors"] = current
    for record in geometry.get("bars", []):
        family = str(record.get("family") or "").upper()
        if family in current:
            record["color"] = current[family]
    for record in geometry.get("legend", []):
        label = str(record.get("label") or "").upper()
        if label in current:
            record["color"] = current[label]
    return current


def _shift_bbox(
    bbox: tuple[int, int, int, int],
    dx: float = 0.0,
    dy: float = 0.0,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox
    return (
        int(round(x0 + dx)),
        int(round(y0 + dy)),
        int(round(x1 + dx)),
        int(round(y1 + dy)),
    )


def _shift_bar_bbox(
    bbox: tuple[int, int, int, int],
    top_dy: float = 0.0,
    bottom_dy: float = 0.0,
) -> tuple[int, int, int, int]:
    x0, y0, x1, y1 = bbox
    return (
        int(round(x0)),
        int(round(y0 + top_dy)),
        int(round(x1)),
        int(round(y1 + bottom_dy)),
    )


def _set_object_name(obj: Any, name: str) -> None:
    try:
        obj.obj.SetName(name)
        return
    except Exception:
        pass
    try:
        obj.SetName(name)
        return
    except Exception:
        pass
    try:
        obj.name = name
    except Exception:
        pass


def _add_native_graphobject(
    layer: Any,
    object_type: int,
    name: str,
) -> Any | None:
    try:
        obj = layer.obj.GraphObjects.Add(object_type)
        if obj is None:
            return None
        obj.SetName(name)
        obj.SetNumProp("attach", 2)
        return obj
    except Exception:
        return None


def _set_endpoint_geometry(
    obj: Any,
    bbox: tuple[float, float, float, float],
) -> None:
    x0, y0, x1, y1 = bbox
    for prop, value in {
        "x1": float(x0),
        "y1": _origin_y(y0),
        "x2": float(x1),
        "y2": _origin_y(y1),
    }.items():
        obj.SetNumProp(prop, value)


def _set_rectangle_geometry(
    obj: Any,
    bbox: tuple[float, float, float, float],
) -> None:
    x0, y0, x1, y1 = bbox
    lower = _origin_y(y1)
    upper = _origin_y(y0)
    obj.SetX((float(x0) + float(x1)) / 2.0)
    obj.SetY((lower + upper) / 2.0)
    obj.SetDX(float(x1) - float(x0))
    obj.SetDY(upper - lower)


def _line_geometry_contract(x1: float, y1: float, x2: float, y2: float) -> dict[str, float]:
    return {
        "x1": float(x1),
        "y1": _origin_y(y1),
        "x2": float(x2),
        "y2": _origin_y(y2),
        "tolerance": 0.75,
    }


def _draw_rectangle(layer: Any, name: str, bbox: tuple[int, int, int, int], color: str, *, dashed: bool = False, transparent: bool = False) -> None:
    red, green, blue = _rgb(color)
    fill = f"fillColor=color({red},{green},{blue}); transparency=100" if transparent else f"fillColor=color({red},{green},{blue}); transparency=0"
    line_color = f"color=color({red},{green},{blue})" if transparent else "color=color(0,0,0)"
    style = "lineStyle=2" if dashed else "lineStyle=0"
    obj = _add_native_graphobject(layer, GRAPHOBJECT_RECTANGLE_TYPE, name)
    if obj is None:
        raise RuntimeError(
            "E401_GRAPHOBJECT_READBACK_UNVERIFIED: Origin GraphObjects.Add "
            f"is required for persistent Fig16 rectangle geometry ({name})"
        )
    _set_rectangle_geometry(obj, bbox)
    for prop, value in {
        "transparency": 100 if transparent else 0,
        "lineStyle": 2 if dashed else 0,
        "lineWidth": RECTANGLE_LINE_WIDTH,
    }.items():
        try:
            obj.SetNumProp(prop, value)
        except Exception:
            pass
        layer.lt_exec(
            f"{name}.{fill}; {name}.{line_color}; "
            f"{name}.{style}; {name}.lineWidth={RECTANGLE_LINE_WIDTH};"
        )


def _draw_line(
    layer: Any,
    name: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: str = "#000000",
    dashed: bool = False,
    width: float = 1.4,
) -> None:
    red, green, blue = _rgb(color)
    line_style = 2 if dashed else 0
    obj = _add_native_graphobject(layer, GRAPHOBJECT_LINE_TYPE, name)
    if obj is not None:
        _set_endpoint_geometry(obj, (x1, y1, x2, y2))
        for prop, value in {"lineStyle": line_style, "lineWidth": width}.items():
            try:
                obj.SetNumProp(prop, value)
            except Exception:
                pass
        layer.lt_exec(
            f"{name}.color=color({red},{green},{blue}); "
            f"{name}.lineStyle={line_style}; {name}.lineWidth={width};"
        )
        return
    raise RuntimeError(
        "E401_GRAPHOBJECT_READBACK_UNVERIFIED: Origin GraphObjects.Add "
        f"is required for persistent Fig16 line geometry ({name})"
    )


def _draw_dashed_line_segments(
    layer: Any,
    prefix: str,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    color: str = "#1e62ff",
    dash: float = 4.0,
    gap: float = 3.0,
) -> list[dict[str, Any]]:
    dx = float(x2) - float(x1)
    dy = float(y2) - float(y1)
    length = (dx * dx + dy * dy) ** 0.5
    if length <= 0:
        return []
    ux = dx / length
    uy = dy / length
    records: list[dict[str, Any]] = []
    offset = 0.0
    index = 0
    while offset < length:
        segment_end = min(offset + dash, length)
        sx1 = float(x1) + ux * offset
        sy1 = float(y1) + uy * offset
        sx2 = float(x1) + ux * segment_end
        sy2 = float(y1) + uy * segment_end
        index += 1
        name = f"{prefix}_{index:02d}"
        _draw_line(layer, name, sx1, sy1, sx2, sy2, color=color, width=0.7)
        records.append(
            {
                "name": name,
                "line_geometry": _line_geometry_contract(sx1, sy1, sx2, sy2),
            }
        )
        offset += dash + gap
    return records


def _draw_dashed_frame(
    layer: Any,
    prefix: str,
    bbox: tuple[int, int, int, int],
) -> list[dict[str, Any]]:
    x0, y0, x1, y1 = bbox
    records: list[dict[str, Any]] = []
    records.extend(_draw_dashed_line_segments(layer, f"{prefix}_top", x0, y0, x1, y0))
    records.extend(_draw_dashed_line_segments(layer, f"{prefix}_right", x1, y0, x1, y1))
    records.extend(_draw_dashed_line_segments(layer, f"{prefix}_bottom", x1, y1, x0, y1))
    records.extend(_draw_dashed_line_segments(layer, f"{prefix}_left", x0, y1, x0, y0))
    return records


def _draw_ellipse(
    layer: Any,
    name: str,
    bbox: tuple[int, int, int, int],
    color: str,
    *,
    transparent: bool = False,
) -> None:
    red, green, blue = _rgb(color)
    obj = _add_native_graphobject(layer, GRAPHOBJECT_ELLIPSE_TYPE, name)
    if obj is not None:
        _set_rectangle_geometry(obj, bbox)
        for prop, value in {
            "transparency": 100 if transparent else 0,
            "lineWidth": ELLIPSE_LINE_WIDTH,
        }.items():
            try:
                obj.SetNumProp(prop, value)
            except Exception:
                pass
        layer.lt_exec(
            f"{name}.color=color({red},{green},{blue}); "
            f"{name}.fillColor=color(255,255,255); "
            f"{name}.transparency={100 if transparent else 0}; {name}.lineWidth={ELLIPSE_LINE_WIDTH};"
        )
        return
    raise RuntimeError(
        "E401_GRAPHOBJECT_READBACK_UNVERIFIED: Origin GraphObjects.Add "
        f"is required for persistent Fig16 ellipse geometry ({name})"
    )


def _add_text(layer: Any, name: str, text: str, x: float, y: float, size: float, *, bold: bool = False) -> None:
    weight = 700 if bold else 400
    label = layer.add_label(text, x, _origin_y(y))
    if label is None:
        raise RuntimeError(f"Origin failed to create Fig16 text object: {name}")
    _set_object_name(label, name)
    try:
        label.set_int("attach", 2)
    except Exception:
        pass
    for prop, value in {
        "x1": float(x),
        "y1": _origin_y(y),
        "fsize": origin_font_size(size),
    }.items():
        try:
            label.set_float(prop, float(value))
        except Exception:
            pass
    try:
        label.set_int("fontWeight", weight)
    except Exception:
        try:
            label.set_float("fontWeight", float(weight))
        except Exception:
            pass


def _build_graphobject_legacy(op: Any, candidate_params: dict[str, Any]) -> dict[str, Any]:
    geometry = fig16_geometry()
    effective_colors = _apply_fig16_color_candidate(geometry, candidate_params)
    tuning = _fig16_tuning(candidate_params)
    text_sizes = _fig16_text_sizes(candidate_params)
    page_size_inches = (7.2, 3.75)
    page = create_hidden_graph_page(
        op,
        lname="Fig16_source_calibrated_graphobjects",
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
    layer = page[0]
    layer.lt_exec(page_percent_layer_command((0.0, 0.0, 100.0, 100.0)))
    disable_speed_mode(layer)
    layer.set_xlim(0.0, 720.0)
    layer.set_ylim(0.0, 375.0)
    remove_default_labels(layer)
    try:
        layer.lt_exec(axisless_layer_command())
    except Exception:
        pass
    required_graphobject_contracts: dict[str, dict[str, Any]] = {}
    expected_names_by_layer: dict[int, list[str]] = {0: []}

    def require_object(
        name: str,
        *,
        text_contains: str | None = None,
        geometry_bbox: tuple[float, float, float, float] | None = None,
        line_geometry: dict[str, float] | None = None,
    ) -> None:
        contract: dict[str, Any] = {"attach": 2}
        if text_contains:
            contract["text_contains"] = text_contains
        if geometry_bbox is not None:
            x0, y0, x1, y1 = geometry_bbox
            contract["geometry"] = {
                "x": (float(x0) + float(x1)) / 2.0,
                "y": HEIGHT - (float(y0) + float(y1)) / 2.0,
                "dx": float(x1) - float(x0),
                "dy": float(y1) - float(y0),
                "tolerance": 0.75,
            }
        if line_geometry is not None:
            contract["line_geometry"] = line_geometry
        required_graphobject_contracts[name] = contract
        expected_names_by_layer[0].append(name)

    bar_inventory: list[dict[str, Any]] = []
    for record in geometry["bars"]:
        object_name = f"fig16_bar_{record['name']}"
        bar_bbox = _shift_bar_bbox(record["bbox"], tuning["bar_top_dy"], tuning["bar_bottom_dy"])
        _draw_rectangle(layer, object_name, bar_bbox, record["color"])
        require_object(object_name, geometry_bbox=bar_bbox)
        bar_inventory.append({**record, "bbox": bar_bbox, "object_name": object_name})

    group_inventory: list[dict[str, Any]] = []
    for record in geometry["group_boxes"]:
        object_name = f"fig16_f_{record['name'].lower()}"
        frame_segments = _draw_dashed_frame(layer, object_name, record["bbox"])
        for segment in frame_segments:
            require_object(segment["name"], line_geometry=segment["line_geometry"])
        x0, _, x1, y1 = record["bbox"]
        baseline_name = f"fig16_baseline_{record['name'].lower()}"
        label_name = f"fig16_group_label_{record['name'].lower()}"
        _draw_line(layer, baseline_name, x0 + 5, y1 - 31, x1 - 6, y1 - 31)
        _add_text(
            layer,
            label_name,
            record["name"],
            x0 + 8 + tuning["group_label_dx"],
            65 + tuning["group_label_dy"],
            text_sizes["group_label"],
            bold=True,
        )
        require_object(baseline_name)
        require_object(label_name, text_contains=record["name"])
        group_inventory.append(
            {
                **record,
                "frame_route": "graphobject_segmented_dashed_line_frame",
                "frame_segment_prefix": object_name,
                "frame_segment_count": len(frame_segments),
                "frame_segment_names": [segment["name"] for segment in frame_segments],
                "baseline_object_name": baseline_name,
                "label_object_name": label_name,
            }
        )

    _add_text(
        layer,
        "fig16_header_h",
        "H: Hardening level",
        18 + tuning["header_dx"],
        13 + tuning["header_dy"],
        text_sizes["header"],
    )
    _add_text(
        layer,
        "fig16_header_s",
        "S: Softening level",
        18 + tuning["header_dx"],
        33 + tuning["header_dy"],
        text_sizes["header"],
    )
    require_object("fig16_header_h", text_contains="H: Hardening level")
    require_object("fig16_header_s", text_contains="S: Softening level")

    legend_inventory: list[dict[str, Any]] = []
    for index, record in enumerate(geometry["legend"], start=1):
        box_name = f"fig16_legend_box_{index:02d}"
        text_name = f"fig16_legend_text_{index:02d}"
        legend_bbox = _shift_bbox(record["bbox"], tuning["legend_dx"], tuning["legend_dy"])
        _draw_rectangle(layer, box_name, legend_bbox, record["color"])
        _add_text(layer, text_name, record["label"], legend_bbox[2] + 8, legend_bbox[1] + 9, text_sizes["legend"])
        require_object(box_name, geometry_bbox=legend_bbox)
        require_object(text_name, text_contains=record["label"])
        legend_inventory.append({**record, "bbox": legend_bbox, "box_object_name": box_name, "text_object_name": text_name})

    stage_inventory: list[dict[str, Any]] = []
    for index, record in enumerate(geometry["stage_labels"], start=1):
        radius = 9.0
        circle_name = f"fig16_stage_circle_{index:02d}"
        stage_text_name = f"fig16_stage_text_{index:02d}"
        relation_text_name = f"fig16_relation_text_{index:02d}"
        circle_bbox = (
            int(record["x"] + tuning["stage_circle_dx"] - radius),
            int(record["y"] + tuning["stage_circle_dy"] - radius),
            int(record["x"] + tuning["stage_circle_dx"] + radius),
            int(record["y"] + tuning["stage_circle_dy"] + radius),
        )
        _draw_ellipse(
            layer,
            circle_name,
            circle_bbox,
            "#505050",
            transparent=False,
        )
        _add_text(
            layer,
            stage_text_name,
            record["stage"],
            record["x"] - 2 + tuning["stage_text_dx"],
            record["y"] - 9 + tuning["stage_text_dy"],
            text_sizes["stage"],
        )
        _add_text(
            layer,
            relation_text_name,
            record["relation"],
            record["relation_x"] - 14 + tuning["relation_text_dx"],
            record["relation_y"] - 13 + tuning["relation_text_dy"],
            text_sizes["relation"],
        )
        require_object(circle_name, geometry_bbox=circle_bbox)
        require_object(stage_text_name, text_contains=record["stage"])
        require_object(relation_text_name, text_contains=record["relation"])
        stage_inventory.append(
            {
                **record,
                "circle_object_name": circle_name,
                "stage_text_object_name": stage_text_name,
                "relation_text_object_name": relation_text_name,
            }
        )

    axis_contract = [
        {
            "layer_index": 0,
            "x.showAxes": 0,
            "y.showAxes": 0,
            "x.showLabels": 0,
            "y.showLabels": 0,
            "x.ticks": 0,
            "y.ticks": 0,
            "x.arrow.show": 0,
            "y.arrow.show": 0,
        }
    ]
    worksheet_name = "Fig16_graphobject_geometry_data"
    worksheet_book = op.new_book("w", lname=worksheet_name)
    worksheet_sheet = worksheet_book[0]
    object_names = list(required_graphobject_contracts)
    roles: list[str] = []
    xs: list[object] = []
    ys: list[object] = []
    dxs: list[object] = []
    dys: list[object] = []
    text_values: list[str] = []
    for object_name in object_names:
        contract = required_graphobject_contracts[object_name]
        geometry_contract = contract.get("geometry", {})
        line_contract = contract.get("line_geometry", {})
        if geometry_contract:
            roles.append("geometry")
            xs.append(geometry_contract.get("x", ""))
            ys.append(geometry_contract.get("y", ""))
            dxs.append(geometry_contract.get("dx", ""))
            dys.append(geometry_contract.get("dy", ""))
        elif line_contract:
            roles.append("line")
            xs.append(line_contract.get("x1", ""))
            ys.append(line_contract.get("y1", ""))
            dxs.append(line_contract.get("x2", ""))
            dys.append(line_contract.get("y2", ""))
        else:
            roles.append("text_or_semantic_object")
            xs.append("")
            ys.append("")
            dxs.append("")
            dys.append("")
        text_values.append(str(contract.get("text_contains", "")))
    for column, (values, lname) in enumerate(
        [
            (object_names, "object_name"),
            (roles, "object_role"),
            (xs, "x_or_x1"),
            (ys, "y_or_y1"),
            (dxs, "dx_or_x2"),
            (dys, "dy_or_y2"),
            (text_values, "text_contains"),
        ]
    ):
        worksheet_sheet.from_list(column, values, lname=lname)
    construction_visibility = reveal_graph_page(page)
    return {
        "page_name": "Fig16_source_calibrated_graphobjects",
        "expected_plot_count": 0,
        "expected_plot_count_by_layer": {0: 0},
        "expected_graphobject_count": len(required_graphobject_contracts),
        "route": "graphobject_source_calibrated_semantic_schematic",
        "rectangle_geometry_route": "originext_setx_sety_setdx_setdy",
        "group_frame_route": "graphobject_segmented_dashed_line_frame",
        "ellipse_geometry_route": "originext_setx_sety_setdx_setdy",
        "canvas_size": geometry["canvas"],
        "page_size_inches": page_size_inches,
        "bar_inventory": bar_inventory,
        "group_inventory": group_inventory,
        "stage_inventory": stage_inventory,
        "legend_inventory": legend_inventory,
        "required_worksheet_books": [worksheet_name],
        "max_direct_plot_worksheet_rows": 5000,
        "worksheet_binding_inventory": [
            {
                "worksheet_name": worksheet_name,
                "association_mode": "named_graphobject_contract",
                "key_column": "object_name",
                "target_layer_index": 0,
                "target_object_count": len(object_names),
            }
        ],
        "fig16_tuning": tuning,
        "fig16_colors": effective_colors,
        "fig16_text_sizes": text_sizes,
        "required_graphobject_names_by_layer": expected_names_by_layer,
        "required_graphobject_contracts": required_graphobject_contracts,
        "axis_contract": axis_contract,
        "construction_visibility": construction_visibility,
        "reproduction_mode": geometry["provenance"],
        "candidate_params": candidate_params,
    }


def _append_path(xs: list[float], ys: list[float], points: list[tuple[float, float]]) -> None:
    for x, y in points:
        xs.append(float(x))
        ys.append(_origin_y(float(y)))
    xs.append(math.nan)
    ys.append(math.nan)


def _append_chart_path(xs: list[float], ys: list[float], points: list[tuple[float, float]]) -> None:
    for x, y in points:
        xs.append(float(x))
        ys.append(float(y))
    xs.append(math.nan)
    ys.append(math.nan)


def _append_dashed_source_segment(
    xs: list[float],
    ys: list[float],
    start: tuple[float, float],
    end: tuple[float, float],
) -> None:
    dx = float(end[0]) - float(start[0])
    dy = float(end[1]) - float(start[1])
    length = math.hypot(dx, dy)
    if length <= 0.0:
        return
    ux, uy = dx / length, dy / length
    offset = 0.0
    while offset < length:
        stop = min(offset + 4.0, length)
        _append_chart_path(xs, ys, [
            (float(start[0]) + ux * offset, _stack_chart_y(float(start[1]) + uy * offset)),
            (float(start[0]) + ux * stop, _stack_chart_y(float(start[1]) + uy * stop)),
        ])
        offset += 7.0


def _style_native_plot(plot: Any, color: str, width: float, dotted: bool = False) -> None:
    try:
        plot.color = color
    except Exception:
        try:
            plot.set_str("color", color)
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
                plot.set_int(prop, 2)
            except Exception:
                pass


def _fig16_column_gap(candidate_params: dict[str, Any]) -> float | None:
    raw = candidate_params.get("fig16_column_gap_percent") if isinstance(candidate_params, dict) else None
    if raw is None:
        return None
    try:
        return max(0.0, min(100.0, float(raw)))
    except (TypeError, ValueError):
        return None


def _fig16_group_frame_width(candidate_params: dict[str, Any]) -> float:
    raw = candidate_params.get("fig16_group_frame_width") if isinstance(candidate_params, dict) else None
    if raw is None:
        return 0.5
    try:
        return max(0.25, min(2.0, float(raw)))
    except (TypeError, ValueError):
        return 0.5


def _style_float_column(plot: Any, color: str, gap_percent: float | None = None) -> None:
    red, green, blue = _rgb(color)
    _style_native_plot(plot, color, 1.0)
    commands = [f"-pfb color({red},{green},{blue})", "-pbc color(0,0,0)"]
    if gap_percent is not None:
        commands.extend([f"-vg {gap_percent:g}", "-vw 1"])
    try:
        plot.set_cmd(*commands)
    except Exception:
        pass


def build(op: Any, candidate_params: dict[str, Any]) -> dict[str, Any]:
    """Build Fig16 from the verified GID399/STACKCOLUMN native plot family."""
    geometry = fig16_geometry()
    effective_colors = _apply_fig16_color_candidate(geometry, candidate_params)
    tuning = _fig16_tuning(candidate_params)
    text_sizes = _fig16_text_sizes(candidate_params)
    column_gap_percent = _fig16_column_gap(candidate_params)
    group_frame_width = _fig16_group_frame_width(candidate_params)
    page_size_inches = (7.2, 3.75)
    page = create_hidden_graph_page(op, lname="Fig16_gid399_native_stackcolumn", template="STACKCOLUMN")
    page.lt_exec(page_dot_command(*page_size_inches, page.get_float("resx"), page.get_float("resy")))
    disable_speed_mode(page)
    layer = page[0]
    layer.lt_exec(page_percent_layer_command((0.0, 0.0, 100.0, 100.0)))
    layer.set_xlim(0.0, 720.0)
    layer.set_ylim(-40.0, 335.0)
    remove_default_labels(layer)
    try:
        layer.lt_exec(axisless_layer_command())
    except Exception:
        pass
    overlay = page.add_layer()
    overlay.lt_exec(page_percent_layer_command((0.0, 0.0, 100.0, 100.0)))
    overlay.set_xlim(0.0, 720.0)
    overlay.set_ylim(-41.0, 334.0)
    remove_default_labels(overlay)
    try:
        overlay.lt_exec(axisless_layer_command())
    except Exception:
        pass

    worksheet_name = "Fig16_gid399_stack_data"
    sheet = op.new_book("w", lname=worksheet_name)[0]
    bar_inventory: list[dict[str, Any]] = []
    direct_contracts: list[dict[str, Any]] = []
    bars_by_name = {str(record["name"]): record for record in geometry["bars"]}
    x_values: list[float] = []
    wh_values: list[float] = []
    drv_values: list[float] = []
    drx_values: list[float] = []
    # Stage-local calibration is required because Origin's stacked-column
    # centering differs by slot after grouping. CP1 moves left while TR1 moves
    # right; applying one global correction would worsen one of the two.
    s_slot_x_offsets = (0.5, -1.5, -2.5, -1.0, -1.5, -0.5, -2.5)
    for stage_index in range(1, 8):
        wh = bars_by_name[f"wh_{stage_index:02d}"]
        drv = bars_by_name[f"drv_{stage_index:02d}"]
        drx = bars_by_name[f"drx_{stage_index:02d}"]
        wh_box = _shift_bar_bbox(wh["bbox"], tuning["bar_top_dy"], tuning["bar_bottom_dy"])
        drv_box = _shift_bar_bbox(drv["bbox"], tuning["bar_top_dy"], tuning["bar_bottom_dy"])
        drx_box = _shift_bar_bbox(drx["bbox"], tuning["bar_top_dy"], tuning["bar_bottom_dy"])
        x_values.extend([
            (wh_box[0] + wh_box[2]) / 2.0,
            (drv_box[0] + drv_box[2]) / 2.0 + s_slot_x_offsets[stage_index - 1],
        ])
        wh_values.extend([float(wh_box[3] - wh_box[1]), 0.0])
        drv_values.extend([0.0, float(drv_box[3] - drv_box[1])])
        drx_values.extend([0.0, max(0.0, float(drx_box[3] - drx_box[1]) - 2.0)])
        bar_inventory.extend([
            {**wh, "bbox": wh_box, "worksheet_family": "WH"},
            {**drv, "bbox": drv_box, "worksheet_family": "DRV"},
            {**drx, "bbox": drx_box, "worksheet_family": "DRX"},
        ])
    sheet.from_list(0, x_values, lname="H_S_slot_x", axis="X")
    sheet.from_list(1, wh_values, lname="WH", axis="Y")
    sheet.from_list(2, drv_values, lname="DRV", axis="Y")
    sheet.from_list(3, drx_values, lname="DRX", axis="Y")
    sheet.cols_axis("XYYY", 0, 3, repeat=False)
    stack_plots: list[tuple[Any, str]] = []
    for plot_index, (column, family) in enumerate(((1, "WH"), (2, "DRV"), (3, "DRX"))):
        plot = layer.add_plot(sheet, colx=0, coly=column, type=213)
        _style_float_column(plot, effective_colors[family], column_gap_percent)
        stack_plots.append((plot, family))
        direct_contracts.append({
            "layer_index": 0, "plot_index": plot_index, "plot_type_code": 213,
            "x_column": "A", "y_column": chr(ord("A") + column),
        })
    # STACKCOLUMN supplies the native plot family; grouping activates its
    # cumulative stack semantics after the three Worksheet plots are added.
    layer.group(True, 0, 2)
    # Grouping applies Origin's increment list, so restore the source palette
    # after the group exists rather than relying on pre-group plot colors.
    for plot, family in stack_plots:
        _style_float_column(plot, effective_colors[family], column_gap_percent)
    column = 4

    frame_x: list[float] = []
    frame_y: list[float] = []
    group_inventory: list[dict[str, Any]] = []
    for record in geometry["group_boxes"]:
        x0, y0, x1, y1 = record["bbox"]
        for start, end in (
            ((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)),
            ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0)),
        ):
            _append_dashed_source_segment(frame_x, frame_y, start, end)
        group_inventory.append({
            **record,
            "frame_route": "worksheet_xy_path",
            "baseline_route": "native_column_bottom_edges_no_extra_baseline",
        })

    circle_x: list[float] = []
    circle_y: list[float] = []
    stage_inventory: list[dict[str, Any]] = []
    for record in geometry["stage_labels"]:
        cx = float(record["x"]) + tuning["stage_circle_dx"]
        cy = float(record["y"]) + tuning["stage_circle_dy"]
        points = [
            (cx + 9.0 * math.cos(2.0 * math.pi * step / 48.0), _stack_chart_y(cy + 9.0 * math.sin(2.0 * math.pi * step / 48.0)))
            for step in range(49)
        ]
        _append_chart_path(circle_x, circle_y, points)
        stage_inventory.append({**record, "circle_route": "worksheet_xy_path"})

    for name, xs, ys, color, width, dotted in (
        ("group_frames", frame_x, frame_y, "#3030d0", group_frame_width, True),
        ("stage_circles", circle_x, circle_y, "#505050", 1.0, False),
    ):
        x_col, y_col = column, column + 1
        sheet.from_list(x_col, xs, lname=f"{name}_x", axis="X")
        sheet.from_list(y_col, ys, lname=f"{name}_y", axis="Y")
        plot = overlay.add_plot(sheet, colx=x_col, coly=y_col, type="line")
        _style_native_plot(plot, color, width, dotted=dotted)
        direct_contracts.append({
            "layer_index": 1, "plot_index": len(direct_contracts) - 3, "plot_type_code": 200,
            "x_column": chr(ord("A") + x_col), "y_column": chr(ord("A") + y_col),
        })
        column += 2

    legend_inventory: list[dict[str, Any]] = []
    legend_layers: list[Any] = []
    # Isolate each swatch in a micro-layer. A native column supplies the true
    # area fill; a Worksheet-backed closed XY path supplies all four border
    # edges independently of column clipping and adjacency.
    for legend_index, record in enumerate(geometry["legend"], start=2):
        bbox = _shift_bbox(record["bbox"], tuning["legend_dx"], tuning["legend_dy"])
        fill_x0, fill_y0, fill_x1, fill_y1 = (
            max(1, bbox[0] - 3),
            max(1, bbox[1] - 2),
            min(719, bbox[2] + 3),
            min(374, bbox[3] + 2),
        )
        x_col, y_col = column, column + 1
        sheet.from_list(x_col, [0.0], lname=f"legend_{record['label']}_x", axis="X")
        sheet.from_list(y_col, [1.0], lname=f"legend_{record['label']}_fill", axis="Y")
        legend_layer = page.add_layer()
        layout_percent = (
            100.0 * fill_x0 / geometry["canvas"][0],
            100.0 * fill_y0 / geometry["canvas"][1],
            100.0 * (fill_x1 - fill_x0) / geometry["canvas"][0],
            100.0 * (fill_y1 - fill_y0) / geometry["canvas"][1],
        )
        legend_layer.lt_exec(page_percent_layer_command(layout_percent))
        remove_default_labels(legend_layer)
        try:
            legend_layer.lt_exec(axisless_layer_command())
        except Exception:
            pass
        plot = legend_layer.add_plot(sheet, colx=x_col, coly=y_col, type=203)
        _style_float_column(plot, str(record["color"]), 0.0)
        legend_layer.set_xlim(-0.5, 0.5)
        legend_layer.set_ylim(0.0, 1.0)
        legend_layer.lt_exec("layer.x.from=-0.5; layer.x.to=0.5; layer.y.from=0; layer.y.to=1;")
        border_x_col, border_y_col = x_col + 2, y_col + 2
        sheet.from_list(
            border_x_col,
            [-0.49, 0.49, 0.49, -0.49, -0.49],
            lname=f"legend_{record['label']}_border_x",
            axis="X",
        )
        sheet.from_list(
            border_y_col,
            [0.01, 0.01, 0.99, 0.99, 0.01],
            lname=f"legend_{record['label']}_border_y",
            axis="Y",
        )
        border_plot = legend_layer.add_plot(
            sheet, colx=border_x_col, coly=border_y_col, type="line"
        )
        _style_native_plot(border_plot, "#000000", 1.0)
        disable_speed_mode(legend_layer)
        legend_layers.append(legend_layer)
        direct_contracts.append({
            "layer_index": legend_index,
            "plot_index": 0,
            "plot_type_code": 203,
            "x_column": chr(ord("A") + x_col),
            "y_column": chr(ord("A") + y_col),
        })
        direct_contracts.append({
            "layer_index": legend_index,
            "plot_index": 1,
            "plot_type_code": 200,
            "x_column": chr(ord("A") + border_x_col),
            "y_column": chr(ord("A") + border_y_col),
        })
        column += 4
        legend_inventory.append({
            **record,
            "bbox": bbox,
            "fill_bbox": (fill_x0, fill_y0, fill_x1, fill_y1),
            "layout_percent": layout_percent,
            "layer_index": legend_index,
            "swatch_route": "isolated_native_column_fill_with_closed_xy_border",
        })

    required_graphobject_contracts: dict[str, dict[str, Any]] = {}
    expected_names: list[str] = []
    def add_text_contract(name: str, text: str, x: float, y: float, size: float, bold: bool = False) -> None:
        rich_text = f"\\f:Times New Roman({text})"
        label = overlay.add_label(rich_text, x, _stack_chart_y(y))
        if label is None:
            raise RuntimeError(f"Origin failed to create Fig16 text object: {name}")
        _set_object_name(label, name)
        try:
            label.set_int("attach", 2)
            label.set_float("x1", float(x))
            label.set_float("y1", _stack_chart_y(y))
            label.set_float("fsize", origin_font_size(size))
            label.set_int("fontWeight", 700 if bold else 400)
        except Exception:
            pass
        required_graphobject_contracts[name] = {"attach": 2, "text_contains": text}
        expected_names.append(name)

    add_text_contract("fig16_header_h", "H: Hardening level", 18 + tuning["header_dx"], 8 + tuning["header_dy"], text_sizes["header"])
    add_text_contract("fig16_header_s", "S: Softening level", 18 + tuning["header_dx"], 28 + tuning["header_dy"], text_sizes["header"])
    for record in geometry["group_boxes"]:
        add_text_contract(f"fig16_group_label_{record['name'].lower()}", record["name"], record["bbox"][0] + 8 + tuning["group_label_dx"], 65 + tuning["group_label_dy"], text_sizes["group_label"], True)
    for index, record in enumerate(geometry["legend"], start=1):
        bbox = _shift_bbox(record["bbox"], tuning["legend_dx"], tuning["legend_dy"])
        add_text_contract(f"fig16_legend_text_{index:02d}", record["label"], bbox[2] + 5, bbox[1] - 6, text_sizes["legend"])
    for index, record in enumerate(geometry["stage_labels"], start=1):
        # Origin's exported Times New Roman glyphs have digit-specific side
        # bearings. These offsets center the reopened glyph bbox, not merely
        # the label anchor, inside the 19 px circle outline.
        digit_dx = {"1": 0.0, "2": 0.0, "3": 0.5}.get(str(record["stage"]), 0.0)
        add_text_contract(
            f"fig16_stage_text_{index:02d}",
            record["stage"],
            record["x"] - 4 + digit_dx + tuning["stage_text_dx"],
            record["y"] - 9.5 + tuning["stage_text_dy"],
            text_sizes["stage"],
        )
        add_text_contract(f"fig16_relation_text_{index:02d}", record["relation"], record["relation_x"] - 14 + tuning["relation_text_dx"], record["relation_y"] - 13 + tuning["relation_text_dy"], text_sizes["relation"])

    axis_contract = [{
        "layer_index": 0, "x.showAxes": 0, "y.showAxes": 0, "x.showLabels": 0,
        "y.showLabels": 0, "x.ticks": 0, "y.ticks": 0, "x.arrow.show": 0, "y.arrow.show": 0,
    }]
    layer.lt_exec("label -r Legend;")
    overlay.set_xlim(0.0, 720.0)
    overlay.set_ylim(-41.0, 334.0)
    overlay.activate()
    overlay.lt_exec("layer.x.from=0; layer.x.to=720; layer.y.from=-41; layer.y.to=334;")
    disable_speed_mode(layer)
    disable_speed_mode(overlay)
    construction_visibility = reveal_graph_page(page)
    return {
        "page_name": "Fig16_gid399_native_stackcolumn",
        "expected_plot_count": 11,
        "expected_plot_count_by_layer": {0: 3, 1: 2, 2: 2, 3: 2, 4: 2},
        "expected_graphobject_count": len(required_graphobject_contracts),
        "route": "gid399_stackcolumn_213_with_gid1652_layout",
        "canvas_size": geometry["canvas"], "page_size_inches": page_size_inches,
        "bar_inventory": bar_inventory, "group_inventory": group_inventory,
        "stage_inventory": stage_inventory, "legend_inventory": legend_inventory,
        "required_worksheet_books": [worksheet_name],
        "worksheet_binding_inventory": [{
            "worksheet_name": worksheet_name, "association_mode": "direct_worksheet_plot_binding",
            "target_layer_index": 0, "target_plot_count": 3,
        }],
        "direct_worksheet_plot_contracts": direct_contracts,
        "official_template_selection": {
            "selected_primary": "GID399",
            "selected_primary_sha256": "a4b3ba55ebe2d195e6ca4b15afb1745619ea23469bedbb60490b976aa9f097b6",
            "selected_primary_plot_type": 213,
            "selected_primary_reopened_rows": 32,
            "layout_reference": "GID1652",
            "layout_reference_sha256": "6ca5fd0602eaa6dd8a50731a2c8e40408cc62c54737b89583b5c114c80d5f1c9",
            "local_instantiation_template": "STACKCOLUMN.otp",
            "selection_reason": "GID399 supplies verified native stacked-column semantics and direct Worksheet bindings; GID1652 supplies the faceted PSC/CP/TR layout reference.",
        },
        "fig16_tuning": tuning, "fig16_colors": effective_colors, "fig16_text_sizes": text_sizes,
        "fig16_column_gap_percent": column_gap_percent,
        "fig16_group_frame_width": group_frame_width,
        "fig16_text_font_route": "origin_rich_text_times_new_roman_parenthesized",
        "fig16_stage_glyph_centering": {
            "anchor_x_base": -4.0,
            "digit_dx": {"1": 0.0, "2": 0.0, "3": 0.5},
            "anchor_y_base": -9.5,
            "calibration_basis": "post_reopen_exported_glyph_bbox_to_circle_outline_center",
        },
        "fig16_native_stack_calibration": {
            "layer_y_limits": [-40.0, 335.0],
            "official_gid399_column_line_width": 1.0,
            "drx_height_correction": -2.0,
            "s_slot_x_offsets": list(s_slot_x_offsets),
            "header_source_y_correction": -5.0,
            "psc_relation_source_y_corrections": [-8.0, -17.0],
            "stage_centers_source_calibrated": [[65, 352], [157, 352], [250, 352], [360, 352], [452, 352], [559, 352], [650, 352]],
        },
        "required_graphobject_names_by_layer": {1: expected_names},
        "required_graphobject_contracts": required_graphobject_contracts,
        "axis_contract": [
            axis_contract[0],
            {**axis_contract[0], "layer_index": 1},
            *[{**axis_contract[0], "layer_index": index} for index in range(2, 5)],
        ],
        "construction_visibility": construction_visibility,
        "reproduction_mode": geometry["provenance"], "candidate_params": candidate_params,
    }
