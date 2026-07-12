from __future__ import annotations

from pathlib import Path
from typing import Any

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
from .geometry import (
    FIG12_SOURCE_FRAMES_PERCENT,
    _classify_fig12_palette_pixels,
    _fill_invalid_class_regions,
    _fig12_threshold_centered_region_values,
    fig12_panels,
)


HEIGHT = 590.0
GRAPHOBJECT_RECTANGLE_TYPE = 8
COLORBAR_COLORS = ["#fcbf6e", "#b1df89", "#c6dfec"]
FIG12_PANEL_KEYS = {"PSC": 0, "UC": 1, "TR": 2, "a": 0, "b": 1, "c": 2, "0": 0, "1": 1, "2": 2}
FIG12_DEFAULT_LABEL_SIZES = {
    "panel": 11.0,
    "contour": 8.4,
    "mechanism": 10.0,
    "colorbar_title": 10.0,
    "colorbar_tick": 8.0,
}
FIG12_DEFAULT_MATRIX_BIASES = {0: 0.0, 1: 0.0, 2: 0.0}
FIG12_DEFAULT_MATRIX_CONTRASTS = {0: 1.0, 1: 1.0, 2: 1.0}
FIG12_DEFAULT_MATRIX_REGION_VALUES: dict[int, list[float]] = {}
FIG12_MATRIX_MODES = {"source_palette_digitized", "analytic_fallback"}
FIG12_BASE_MATRIX_SHAPE = (92, 72)
FIG12_DEFAULT_MATRIX_SMOOTHING_SIGMA = 0.5
FIG12_DEFAULT_Y_MINOR_TICKS = 0
FIG12_ORIGIN_LABEL_SIZE_SCALES = {
    "panel": 2.6,
    "contour": 2.6,
    "mechanism": 2.4,
}
FIG12_AXIS_TICK_FSIZE = 26.0
FIG12_X_AXIS_TITLE_FSIZE = 28.0
FIG12_Y_AXIS_TITLE_FSIZE = 23.0
FIG12_AXIS_FONT = "Times New Roman"
FIG12_CONTOUR_LINE_COLOR = (86, 107, 68)
FIG12_CONTOUR_LINE_WIDTH = 0.05
FIG12_PATH_OVERLAY_COLOR = "#708e57"
FIG12_PATH_OVERLAY_TYPE = 34


def _page_y(source_y: float) -> float:
    return HEIGHT - float(source_y)


def _rgb(hex_color: str) -> tuple[int, int, int]:
    value = hex_color.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)


def _bounded_float(value: Any, *, default: float = 0.0, limit: float = 60.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(-limit, min(limit, number))


def _shift_bbox(
    bbox: tuple[float, float, float, float],
    *,
    dx: float = 0.0,
    dy: float = 0.0,
) -> tuple[float, float, float, float]:
    x0, y0, x1, y1 = bbox
    return (float(x0) + dx, float(y0) + dy, float(x1) + dx, float(y1) + dy)


def _fig12_colorbar_offsets(candidate_params: dict[str, Any]) -> dict[int, dict[str, float]]:
    raw = candidate_params.get("fig12_colorbar_offsets") if isinstance(candidate_params, dict) else None
    offsets = {index: {"dx": 0.0, "dy": 0.0} for index in range(3)}
    if not isinstance(raw, dict):
        return offsets
    for key, value in raw.items():
        panel_index = FIG12_PANEL_KEYS.get(str(key))
        if panel_index is None or not isinstance(value, dict):
            continue
        offsets[panel_index] = {
            "dx": _bounded_float(value.get("dx"), default=0.0, limit=80.0),
            "dy": _bounded_float(value.get("dy"), default=0.0, limit=80.0),
        }
    return offsets


def _bounded_size(value: Any, *, default: float, limit: float = 18.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return max(4.0, min(limit, number))


def _fig12_label_sizes(candidate_params: dict[str, Any]) -> dict[str, float]:
    sizes = dict(FIG12_DEFAULT_LABEL_SIZES)
    raw_absolute = candidate_params.get("fig12_label_sizes") if isinstance(candidate_params, dict) else None
    if isinstance(raw_absolute, dict):
        for role, default in FIG12_DEFAULT_LABEL_SIZES.items():
            if role in raw_absolute:
                sizes[role] = _bounded_size(raw_absolute.get(role), default=default)

    raw_offsets = candidate_params.get("fig12_label_size_offsets") if isinstance(candidate_params, dict) else None
    if isinstance(raw_offsets, dict):
        for role, default in FIG12_DEFAULT_LABEL_SIZES.items():
            if role in raw_offsets:
                offset = _bounded_float(raw_offsets.get(role), default=0.0, limit=6.0)
                sizes[role] = _bounded_size(sizes[role] + offset, default=default)
    return sizes


def _fig12_matrix_biases(candidate_params: dict[str, Any]) -> dict[int, float]:
    raw = candidate_params.get("fig12_matrix_biases") if isinstance(candidate_params, dict) else None
    biases = dict(FIG12_DEFAULT_MATRIX_BIASES)
    if not isinstance(raw, dict):
        return biases
    for key, value in raw.items():
        panel_index = FIG12_PANEL_KEYS.get(str(key))
        if panel_index is None:
            continue
        biases[panel_index] = _bounded_float(value, default=0.0, limit=6.0)
    return biases


def _fig12_matrix_contrasts(candidate_params: dict[str, Any]) -> dict[int, float]:
    raw = candidate_params.get("fig12_matrix_contrasts") if isinstance(candidate_params, dict) else None
    contrasts = dict(FIG12_DEFAULT_MATRIX_CONTRASTS)
    if not isinstance(raw, dict):
        return contrasts
    for key, value in raw.items():
        panel_index = FIG12_PANEL_KEYS.get(str(key))
        if panel_index is None:
            continue
        contrast = _bounded_float(value, default=1.0, limit=2.0)
        contrasts[panel_index] = max(0.5, contrast)
    return contrasts


def _fig12_matrix_region_values(candidate_params: dict[str, Any]) -> dict[int, list[float]]:
    raw = candidate_params.get("fig12_matrix_region_values") if isinstance(candidate_params, dict) else None
    values: dict[int, list[float]] = dict(FIG12_DEFAULT_MATRIX_REGION_VALUES)
    if not isinstance(raw, dict):
        return values
    for key, sequence in raw.items():
        panel_index = FIG12_PANEL_KEYS.get(str(key))
        if panel_index is None or not isinstance(sequence, (list, tuple)) or len(sequence) != 3:
            continue
        try:
            parsed = [float(item) for item in sequence]
        except (TypeError, ValueError):
            continue
        values[panel_index] = parsed
    return values


def _fig12_path_overlays_enabled(candidate_params: dict[str, Any]) -> bool:
    value = candidate_params.get("fig12_path_overlays") if isinstance(candidate_params, dict) else None
    return bool(value) if isinstance(value, bool) else False


def _fig12_axis_title_overlays_enabled(candidate_params: dict[str, Any]) -> bool:
    value = candidate_params.get("fig12_axis_title_overlays") if isinstance(candidate_params, dict) else None
    return bool(value) if isinstance(value, bool) else False


def _add_fig12_axis_title_overlay(
    layer: Any,
    name: str,
    text: str,
    x: float,
    y: float,
    size: float,
    *,
    rotate: float = 0.0,
) -> bool:
    """Add a page-coordinate rich-text axis title with stable post-reopen geometry."""
    try:
        label = layer.add_label(rf"\f:{FIG12_AXIS_FONT}({text})", float(x), _page_y(float(y)))
        if label is None:
            return False
        _set_object_name(label, name)
        for prop, value in {
            "attach": 2,
            "x1": float(x),
            "y1": _page_y(float(y)),
            "fsize": float(size),
            "rotate": float(rotate),
        }.items():
            try:
                label.set_float(prop, float(value))
            except Exception:
                try:
                    label.set_int(prop, int(value))
                except Exception:
                    pass
        try:
            layer.lt_exec(f"{name}.font=font({FIG12_AXIS_FONT});")
        except Exception:
            pass
        return True
    except Exception:
        return False


def _fig12_boundary_svg(
    panel_name: str,
    source_crop: str | Path,
    output_path: Path,
) -> tuple[int, int]:
    """Write source-palette class boundaries as an editable Origin SVG path."""
    import numpy as np
    from PIL import Image
    from skimage.measure import find_contours

    source_path = Path(source_crop)
    with Image.open(source_path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=float)
    width, height = rgb.shape[1], rgb.shape[0]
    left_pct, top_pct, width_pct, height_pct = FIG12_SOURCE_FRAMES_PERCENT[panel_name]
    x0 = max(0, int(round(left_pct / 100.0 * width)) + 1)
    y0 = max(0, int(round(top_pct / 100.0 * height)) + 1)
    x1 = min(width, int(round((left_pct + width_pct) / 100.0 * width)) - 1)
    y1 = min(height, int(round((top_pct + height_pct) / 100.0 * height)) - 1)
    classes, valid = _classify_fig12_palette_pixels(rgb[y0:y1 + 1, x0:x1 + 1])
    classes = _fill_invalid_class_regions(classes, valid)
    crop_height, crop_width = classes.shape
    paths: list[str] = []
    contour_count = 0
    for boundary in (0.5, 1.5):
        for contour in find_contours(classes.astype(float), boundary):
            if len(contour) < 3:
                continue
            points = [
                f"{float(column) + 0.5:.3f},{float(row) + 0.5:.3f}"
                for row, column in contour
            ]
            paths.append("M " + " L ".join(points))
            contour_count += 1
    fill_colors = ("#fcbf6e", "#b1df89", "#c6dfec")
    fill_elements: list[str] = []
    for class_index, color in enumerate(fill_colors):
        polygons: list[str] = []
        # Padding closes components that touch a panel edge. Without it, SVG
        # closes an open contour by drawing a diagonal across the plot.
        mask = np.pad((classes == class_index).astype(float), 1, constant_values=0.0)
        for contour in find_contours(mask, 0.5):
            if len(contour) < 3:
                continue
            points = [
                f"{min(float(crop_width), max(0.0, float(column) - 0.5)):.3f},"
                f"{min(float(crop_height), max(0.0, float(row) - 0.5)):.3f}"
                for row, column in contour
            ]
            polygons.append("M " + " L ".join(points) + " Z")
        fill_elements.append(
            f'<path d="{" ".join(polygons)}" fill="{color}" fill-rule="evenodd" stroke="none"/>'
        )
    output_path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{crop_width}" height="{crop_height}" viewBox="0 0 {crop_width} {crop_height}">'
        + "".join(fill_elements)
        + f'<path d="{" ".join(paths)}" fill="none" stroke="{FIG12_PATH_OVERLAY_COLOR}" stroke-width="0.5"/>'
        "</svg>",
        encoding="utf-8",
    )
    return contour_count, len(paths)


def _add_fig12_path_overlay(
    layer: Any,
    panel: dict[str, Any],
    panel_index: int,
    source_crop: str | Path,
    expected_names: list[str],
    required_graphobject_contracts: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    import tempfile

    name = f"fig12_boundary_{['a', 'b', 'c'][panel_index]}"
    with tempfile.TemporaryDirectory(prefix="originplot_fig12_") as temp_dir:
        svg_path = Path(temp_dir) / f"boundary_{panel_index}.svg"
        contour_count, path_count = _fig12_boundary_svg(panel["name"], source_crop, svg_path)
        layer.lt_exec(f'draw -paths {name} "{svg_path.as_posix()}";')
        objects = [item for item in layer.obj.GraphObjects if str(item.GetName()).upper() == name.upper()]
        if not objects:
            raise RuntimeError(f"Fig12 boundary path object was not created: {name}")
        obj = objects[-1]
    left_pct, top_pct, width_pct, height_pct = FIG12_SOURCE_FRAMES_PERCENT[panel["name"]]
    # The SVG crop already excludes the one-pixel frame border. Keep the
    # imported object on the exact source panel frame so Origin's scaling does
    # not introduce a second artificial inset.
    left = left_pct / 100.0 * 805.0
    top = top_pct / 100.0 * HEIGHT
    width = width_pct / 100.0 * 805.0
    height = height_pct / 100.0 * HEIGHT
    try:
        obj.SetX(left + width / 2.0)
        obj.SetY(HEIGHT - (top + height / 2.0))
        obj.SetDX(width)
        obj.SetDY(height)
    except Exception as exc:
        raise RuntimeError(f"Fig12 boundary path coordinate binding failed: {exc}") from exc
    expected_names.append(name)
    required_graphobject_contracts[name] = {
        "object_type": FIG12_PATH_OVERLAY_TYPE,
        "geometry": {
            "x": left + width / 2.0,
            "y": HEIGHT - (top + height / 2.0),
            "dx": width,
            "dy": height,
            "tolerance": 1.5,
        },
    }
    return {
        "name": name,
        "panel": panel["name"],
        "object_type": FIG12_PATH_OVERLAY_TYPE,
        "contour_count": contour_count,
        "path_count": path_count,
        "page_bbox": [left, top, left + width, top + height],
        # The SVG is an intermediate import asset; keep the route portable.
        "svg_asset": "transient_unique_import.svg",
        "svg_asset_retained": False,
        "editable": True,
        "filled_source_regions": True,
    }


def _fig12_data_to_page(panel: dict[str, Any], x: float, y: float) -> tuple[float, float]:
    import math

    left_pct, top_pct, width_pct, height_pct = FIG12_SOURCE_FRAMES_PERCENT[panel["name"]]
    left = left_pct / 100.0 * 805.0
    top = top_pct / 100.0 * HEIGHT
    width = width_pct / 100.0 * 805.0
    height = height_pct / 100.0 * HEIGHT
    x_fraction = (float(x) - float(panel["xlim"][0])) / (
        float(panel["xlim"][1]) - float(panel["xlim"][0])
    )
    y_fraction = (
        math.log10(float(y)) - math.log10(float(panel["ylim"][0]))
    ) / (
        math.log10(float(panel["ylim"][1])) - math.log10(float(panel["ylim"][0]))
    )
    source_y = top + (1.0 - y_fraction) * height
    return left + x_fraction * width, HEIGHT - source_y


def _fig12_panel_layout_offsets(candidate_params: dict[str, Any]) -> dict[int, dict[str, float]]:
    raw = candidate_params.get("fig12_panel_layout_offsets") if isinstance(candidate_params, dict) else None
    offsets = {index: {"dx": 0.0, "dy": 0.0} for index in range(3)}
    if not isinstance(raw, dict):
        return offsets
    for key, value in raw.items():
        panel_index = FIG12_PANEL_KEYS.get(str(key))
        if panel_index is None or not isinstance(value, dict):
            continue
        offsets[panel_index] = {
            "dx": _bounded_float(value.get("dx"), default=0.0, limit=15.0),
            "dy": _bounded_float(value.get("dy"), default=0.0, limit=15.0),
        }
    return offsets


def _fig12_matrix_mode(candidate_params: dict[str, Any]) -> str:
    raw = candidate_params.get("fig12_matrix_mode") if isinstance(candidate_params, dict) else None
    value = str(raw or "source_palette_digitized")
    return value if value in FIG12_MATRIX_MODES else "source_palette_digitized"


def _fig12_matrix_resolution(candidate_params: dict[str, Any]) -> tuple[int, int, float]:
    raw = (
        candidate_params.get("fig12_matrix_resolution_scale")
        if isinstance(candidate_params, dict)
        else None
    )
    scale = _bounded_float(raw, default=0.5, limit=0.5)
    if scale < 0.35:
        scale = 0.35
    base_nx, base_ny = FIG12_BASE_MATRIX_SHAPE
    nx = max(32, min(46, int(round(base_nx * scale))))
    ny = max(25, min(36, int(round(base_ny * scale))))
    return nx, ny, scale


def _fig12_matrix_smoothing_sigma(candidate_params: dict[str, Any]) -> float:
    raw = (
        candidate_params.get("fig12_matrix_smoothing_sigma")
        if isinstance(candidate_params, dict)
        else None
    )
    return max(
        0.0,
        _bounded_float(
            raw,
            default=FIG12_DEFAULT_MATRIX_SMOOTHING_SIGMA,
            limit=8.0,
        ),
    )


def _fig12_y_minor_ticks(candidate_params: dict[str, Any]) -> int:
    raw = candidate_params.get("fig12_y_minor_ticks") if isinstance(candidate_params, dict) else None
    try:
        value = int(round(float(raw)))
    except (TypeError, ValueError):
        value = FIG12_DEFAULT_Y_MINOR_TICKS
    return max(0, min(8, value))


def _apply_matrix_bias(
    matrix: Any,
    levels: list[float],
    bias: float,
    contrast: float = 1.0,
) -> Any:
    if abs(float(bias)) < 1e-9 and abs(float(contrast) - 1.0) < 1e-9:
        return matrix
    import numpy as np

    values = np.asarray(matrix, dtype=float)
    center = (float(levels[1]) + float(levels[2])) / 2.0
    adjusted = center + (values - center) * float(contrast) + float(bias)
    return np.clip(adjusted, min(levels), max(levels))


def _apply_matrix_region_values(matrix: Any, levels: list[float], targets: list[float] | None) -> Any:
    if targets is None:
        return matrix
    import numpy as np

    high, middle, low = map(float, targets)
    if not (levels[0] <= low < levels[1] < middle < levels[2] < high <= levels[3]):
        raise ValueError("Fig12 matrix region values must preserve low/middle/high contour classes")
    source_high, source_middle, source_low = _fig12_threshold_centered_region_values(levels)
    values = np.asarray(matrix, dtype=float)
    remapped = np.interp(
        values,
        [source_low, source_middle, source_high],
        [low, middle, high],
    )
    return np.clip(remapped, min(levels), max(levels))


def _set_layer_frame(layer: Any, frame: tuple[float, float, float, float]) -> None:
    left, top, width, height = frame
    command = page_percent_layer_command(frame)
    layer.lt_exec(command)
    for prop, value in {"left": left, "top": top, "width": width, "height": height}.items():
        try:
            layer.set_float(prop, value)
        except Exception:
            pass


def _offset_layer_frame(
    frame: tuple[float, float, float, float],
    offset: dict[str, float],
) -> tuple[float, float, float, float]:
    left, top, width, height = frame
    return (
        float(left) + float(offset.get("dx", 0.0)),
        float(top) + float(offset.get("dy", 0.0)),
        float(width),
        float(height),
    )


def _apply_three_region_palette(layer: Any) -> None:
    commands = [
        "legend -r;",
        "layer.cmap.linkpal=0; layer.cmap.type=0; layer.cmap.numMinorLevels=0; layer.cmap.colorMixMode=0;",
        "layer.cmap.numMajorLevels=3; layer.cmap.numColors=3;",
        "layer.cmap.setLevels(1);",
        "layer.cmap.color1=color(198,223,236); layer.cmap.color2=color(177,223,137); layer.cmap.color3=color(252,191,110);",
        "layer.cmap.colorBelow=color(198,223,236); layer.cmap.colorAbove=color(252,191,110);",
        "layer.cmap.showLabels(3); layer.cmap.updateScale();",
    ]
    for command in commands:
        try:
            layer.lt_exec(command)
        except Exception:
            pass


def _apply_contour_line_style(layer: Any) -> None:
    red, green, blue = FIG12_CONTOUR_LINE_COLOR
    width = FIG12_CONTOUR_LINE_WIDTH
    layer.lt_exec(
        f"layer.cmap.lineColor1=color({red},{green},{blue}); "
        f"layer.cmap.lineColor2=color({red},{green},{blue}); "
        f"layer.cmap.lineColor3=color({red},{green},{blue}); "
        f"layer.cmap.lineWidth1={width:g}; "
        f"layer.cmap.lineWidth2={width:g}; "
        f"layer.cmap.lineWidth3={width:g}; "
        "layer.cmap.showLines(1); layer.cmap.showLabels(3); layer.cmap.updateScale();"
    )


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


def _add_native_graphobject(layer: Any, object_type: int, name: str) -> Any | None:
    try:
        obj = layer.obj.GraphObjects.Add(object_type)
        if obj is None:
            return None
        obj.SetName(name)
        obj.SetNumProp("attach", 2)
        return obj
    except Exception:
        return None


def _set_page_rectangle_geometry(obj: Any, bbox: tuple[float, float, float, float]) -> None:
    x0, y0, x1, y1 = bbox
    lower = _page_y(y1)
    upper = _page_y(y0)
    obj.SetX((float(x0) + float(x1)) / 2.0)
    obj.SetY((lower + upper) / 2.0)
    obj.SetDX(float(x1) - float(x0))
    obj.SetDY(upper - lower)


def _draw_page_rectangle(
    layer: Any,
    name: str,
    bbox: tuple[float, float, float, float],
    color: str,
) -> dict[str, Any]:
    red, green, blue = _rgb(color)
    obj = _add_native_graphobject(layer, GRAPHOBJECT_RECTANGLE_TYPE, name)
    if obj is None:
        raise RuntimeError(
            "E401_GRAPHOBJECT_READBACK_UNVERIFIED: Origin GraphObjects.Add "
            f"is required for editable Fig12 colorbar rectangles ({name})"
        )
    _set_page_rectangle_geometry(obj, bbox)
    for prop, value in {"transparency": 0, "lineStyle": 0, "lineWidth": 0.7}.items():
        try:
            obj.SetNumProp(prop, value)
        except Exception:
            pass
    layer.lt_exec(
        f"{name}.fillColor=color({red},{green},{blue}); "
        f"{name}.color=color(0,0,0); {name}.lineWidth=0.7;"
    )
    x0, y0, x1, y1 = bbox
    return {
        "attach": 2,
        "geometry": {
            "x": (float(x0) + float(x1)) / 2.0,
            "y": HEIGHT - (float(y0) + float(y1)) / 2.0,
            "dx": float(x1) - float(x0),
            "dy": float(y1) - float(y0),
            "tolerance": 0.75,
        },
    }


def _add_scale_label(
    layer: Any,
    name: str,
    text: str,
    x: float,
    y: float,
    size: float,
    *,
    role: str,
    boxed: bool = False,
    page_sized: bool = False,
) -> bool:
    try:
        display_text = rf"\b({text})" if boxed else text
        label = layer.add_label(display_text, x, y)
        if label is None:
            return False
        _set_object_name(label, name)
        try:
            label.set_int("attach", 2)
        except Exception:
            pass
        origin_size = origin_font_size(size) if page_sized else max(
            5.0,
            min(48.0, float(size) * FIG12_ORIGIN_LABEL_SIZE_SCALES.get(role, 1.0)),
        )
        for prop, value in {"x1": x, "y1": y, "fsize": origin_size}.items():
            try:
                label.set_float(prop, float(value))
            except Exception:
                pass
        if boxed:
            try:
                label.set_int("fontWeight", 700)
            except Exception:
                pass
            for prop in ["frame", "fill"]:
                try:
                    label.set_int(prop, 1)
                except Exception:
                    pass
            for command in [
                f"{name}.frame=1; {name}.fill=1;",
                f"{name}.fillColor=color(255,255,255); {name}.color=color(0,0,0);",
            ]:
                try:
                    layer.lt_exec(command)
                except Exception:
                    pass
        return True
    except Exception:
        return False


def _add_page_label(layer: Any, name: str, text: str, x: float, y: float, size: float) -> bool:
    try:
        label = layer.add_label(text, x, _page_y(y))
        if label is None:
            return False
        _set_object_name(label, name)
        try:
            label.set_int("attach", 2)
        except Exception:
            pass
        for prop, value in {"x1": x, "y1": _page_y(y), "fsize": origin_font_size(size)}.items():
            try:
                label.set_float(prop, float(value))
            except Exception:
                pass
        return True
    except Exception:
        return False


def _add_colorbar_overlay(
    layer: Any,
    panel: dict[str, Any],
    panel_index: int,
    bbox: tuple[float, float, float, float],
    label_sizes: dict[str, float],
    required_graphobject_contracts: dict[str, dict[str, Any]],
    expected_names: list[str],
) -> dict[str, Any]:
    x0, y0, x1, y1 = bbox
    segment_height = (y1 - y0) / 3.0
    levels = [f"{value:.2f}" for value in panel["levels"]]
    panel_key = ["a", "b", "c"][panel_index]
    records: list[dict[str, Any]] = []
    for index, color in enumerate(COLORBAR_COLORS):
        name = f"fig12_cb_{panel_key}_b{index + 1}"
        top = y0 + index * segment_height
        bottom = y0 + (index + 1) * segment_height
        contract = _draw_page_rectangle(layer, name, (x0, top, x1, bottom), color)
        required_graphobject_contracts[name] = contract
        expected_names.append(name)
        records.append({"name": name, "bbox": (x0, top, x1, bottom), "color": color})

    title_name = f"fig12_cb_{panel_key}_ttl"
    _add_page_label(layer, title_name, "lnZ", x0 + 5.0, y0 - 18.0, label_sizes["colorbar_title"])
    required_graphobject_contracts[title_name] = {"attach": 2, "text_contains": "lnZ"}
    expected_names.append(title_name)

    for index, value in enumerate(reversed(levels)):
        y = y0 + index * segment_height
        label_name = f"fig12_cb_{panel_key}_k{index + 1}"
        _add_page_label(layer, label_name, value, x1 + 10.0, y + 4.0, label_sizes["colorbar_tick"])
        required_graphobject_contracts[label_name] = {"attach": 2, "text_contains": value}
        expected_names.append(label_name)

    return {
        "panel": panel["name"],
        "panel_index": panel_index,
        "bbox": bbox,
        "box_records": records,
        "title_object_name": title_name,
        "tick_values": list(reversed(levels)),
    }


def build(op: Any, candidate_params: dict[str, Any]) -> dict[str, Any]:
    matrix_mode = _fig12_matrix_mode(candidate_params)
    matrix_nx, matrix_ny, matrix_resolution_scale = _fig12_matrix_resolution(candidate_params)
    matrix_smoothing_sigma = _fig12_matrix_smoothing_sigma(candidate_params)
    y_minor_ticks = _fig12_y_minor_ticks(candidate_params)
    matrix_source_crop = None if matrix_mode == "analytic_fallback" else (
        candidate_params.get("_runtime_source_crop") or candidate_params.get("source_crop")
    )
    panels = fig12_panels(
        matrix_source_crop,
        nx=matrix_nx,
        ny=matrix_ny,
        smoothing_sigma=matrix_smoothing_sigma,
    )
    colorbar_offsets = _fig12_colorbar_offsets(candidate_params)
    label_sizes = _fig12_label_sizes(candidate_params)
    matrix_biases = _fig12_matrix_biases(candidate_params)
    matrix_contrasts = _fig12_matrix_contrasts(candidate_params)
    matrix_region_values = _fig12_matrix_region_values(candidate_params)
    path_overlays_enabled = _fig12_path_overlays_enabled(candidate_params)
    axis_title_overlays_enabled = _fig12_axis_title_overlays_enabled(candidate_params)
    panel_layout_offsets = _fig12_panel_layout_offsets(candidate_params)
    canvas_size = (805, 590)
    page_size_inches = (8.05, 5.9)
    page = create_hidden_graph_page(
        op,
        lname="Fig12_source_calibrated_three_panel_contour",
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
    layers = [page[0], page.add_layer(), page.add_layer()]
    panel_inventory: list[dict[str, Any]] = []
    required_worksheet_books: list[str] = []
    worksheet_binding_inventory: list[dict[str, Any]] = []
    label_inventory: list[dict[str, Any]] = []
    pending_overlay_labels: list[dict[str, Any]] = []
    path_overlay_inventory: list[dict[str, Any]] = []
    required_graphobject_contracts: dict[str, dict[str, Any]] = {}
    expected_names_by_layer: dict[int, list[str]] = {0: [], 1: [], 2: [], 3: []}
    label_index = 0

    for index, (panel, layer) in enumerate(zip(panels, layers)):
        matrix_values = _apply_matrix_region_values(
            panel["matrix"], panel["levels"], matrix_region_values.get(index)
        )
        matrix_values = _apply_matrix_bias(
            matrix_values, panel["levels"], matrix_biases[index], matrix_contrasts[index]
        )
        worksheet_name = f"Fig12_{panel['name']}_worksheet_data"
        worksheet_book = op.new_book("w", lname=worksheet_name)
        worksheet_sheet = worksheet_book[0]
        import numpy as np
        x_axis = np.linspace(panel["xlim"][0], panel["xlim"][1], matrix_values.shape[1])
        y_axis = np.geomspace(panel["ylim"][0], panel["ylim"][1], matrix_values.shape[0])
        xx, yy = np.meshgrid(x_axis, y_axis)
        z_values = matrix_values
        worksheet_sheet.from_list(0, xx.ravel().tolist(), lname="Temperature", axis="X")
        worksheet_sheet.from_list(1, yy.ravel().tolist(), lname="Strain Rate", axis="Y")
        worksheet_sheet.from_list(2, z_values.ravel().tolist(), lname="lnZ", axis="Z")
        worksheet_sheet.cols_axis("XYZ", 0, 2, repeat=False)
        required_worksheet_books.append(worksheet_name)
        worksheet_binding_inventory.append(
            {
                "worksheet_name": worksheet_name,
                "association_mode": "direct_worksheet_xyz_plot_binding",
                "target_layer_index": index,
                "target_plot_type": 243,
                "columns": {"x": "A", "y": "B", "z": "C"},
                "matrix_shape": list(matrix_values.shape),
                "xymap": panel["xymap"],
            }
        )
        plot = layer.add_plot(f"{worksheet_sheet.lt_range(False)}!(1,2,3)", type=243)
        layer.rescale()
        disable_speed_mode(layer)
        try:
            plot.zlevels = {"minors": 0, "levels": panel["levels"]}
        except Exception:
            pass
        layer.set_xlim(*panel["xlim"])
        layer.set_ylim(*panel["ylim"])
        layout_percent = _offset_layer_frame(panel["layout_percent"], panel_layout_offsets[index])
        _set_layer_frame(layer, layout_percent)
        remove_default_labels(layer)
        _apply_three_region_palette(layer)
        try:
            layer.lt_exec(
                "layer.y.type=2; layer.x.from=250; layer.x.to=400; "
                f"layer.y.minorTicks={y_minor_ticks}; "
                "label -xb \"Temperature/\u2103\"; "
                "label -yl \"Strain rate/s\\+(-1)\"; "
                "yl.rotate=90; "
                f"layer.x.label.font=font({FIG12_AXIS_FONT}); "
                f"layer.y.label.font=font({FIG12_AXIS_FONT}); "
                f"xb.font=font({FIG12_AXIS_FONT}); yl.font=font({FIG12_AXIS_FONT}); "
                f"layer.x.label.fsize={FIG12_AXIS_TICK_FSIZE:g}; "
                f"layer.y.label.fsize={FIG12_AXIS_TICK_FSIZE:g}; "
                f"xb.fsize={FIG12_X_AXIS_TITLE_FSIZE:g}; yl.fsize={FIG12_Y_AXIS_TITLE_FSIZE:g};"
            )
            if axis_title_overlays_enabled:
                layer.lt_exec("label -r xb; label -r yl;")
        except Exception:
            pass
        _apply_three_region_palette(layer)
        # cmap.setLevels() can reset custom thresholds.  Reapply the source
        # panel levels after the final palette command so the three fills use
        # the published boundaries rather than equal-interval defaults.
        try:
            plot.zlevels = {"minors": 0, "levels": panel["levels"]}
            _apply_contour_line_style(layer)
            if path_overlays_enabled:
                layer.lt_exec("layer.cmap.showLines(0);")
        except Exception:
            pass
        try:
            layer.lt_exec("legend -r; label -r Legend;")
        except Exception:
            pass
        disable_speed_mode(layer)

        panel_x = [196.0, 203.0, 203.0][index]
        panel_y_multiplier = [1.33, 1.33, 1.18][index]
        panel_labels = [
            {
                "role": "panel",
                "text": panel["panel"],
                "x": panel_x,
                "y": panel["ylim"][1] * panel_y_multiplier,
                "size": label_sizes["panel"],
            },
            *[
                {"role": "contour", "text": text, "x": x, "y": y, "size": label_sizes["contour"]}
                for x, y, text in panel["labels"]
            ],
            *[
                {
                    "role": "mechanism",
                    "text": text,
                    "x": x,
                    "y": y,
                    "size": label_sizes["mechanism"],
                    "boxed": True,
                }
                for x, y, text in panel["mechanisms"]
            ],
        ]
        for record in panel_labels:
            label_index += 1
            object_name = f"fig12_label_{label_index:02d}"
            target_layer_index = 3 if path_overlays_enabled else index
            created = False
            if path_overlays_enabled:
                page_x, page_y = _fig12_data_to_page(panel, record["x"], record["y"])
                pending_overlay_labels.append(
                    {"panel": panel, "record": record, "name": object_name, "x": page_x, "y": page_y}
                )
            else:
                created = _add_scale_label(
                    layer,
                    object_name,
                    record["text"],
                    record["x"],
                    record["y"],
                    record["size"],
                    role=record["role"],
                    boxed=bool(record.get("boxed", False)),
                )
            label_inventory.append(
                {
                    "panel": panel["name"],
                    **record,
                    "name": object_name,
                    "attach": 2,
                    "layer_index": target_layer_index,
                    "created": created,
                }
            )
            contract: dict[str, Any] = {"attach": 2}
            if record["role"] in {"panel", "mechanism"}:
                contract["text_contains"] = record["text"]
            if not path_overlays_enabled:
                required_graphobject_contracts[object_name] = contract
                expected_names_by_layer[index].append(object_name)

        panel_inventory.append(
            {
                "name": panel["name"],
                "xymap": panel["xymap"],
                "levels": panel["levels"],
                "layout_percent": layout_percent,
                "layout_offset": panel_layout_offsets[index],
                "log_y_axis": True,
                "matrix_shape": list(panel["matrix"].shape),
                "matrix_source": panel.get("matrix_source", "analytic_fallback"),
                "matrix_bias": matrix_biases[index],
                "matrix_contrast": matrix_contrasts[index],
                "matrix_mode": matrix_mode,
                "matrix_resolution_scale": matrix_resolution_scale,
                "matrix_smoothing_sigma": panel.get("matrix_smoothing_sigma", 0.0),
            }
        )

    overlay_layer = page.add_layer()
    _set_layer_frame(overlay_layer, (0.0, 0.0, 100.0, 100.0))
    overlay_layer.set_xlim(0.0, float(canvas_size[0]))
    overlay_layer.set_ylim(0.0, float(canvas_size[1]))
    remove_default_labels(overlay_layer)
    try:
        overlay_layer.lt_exec(axisless_layer_command())
    except Exception:
        pass
    disable_speed_mode(overlay_layer)
    if path_overlays_enabled:
        if matrix_source_crop is None:
            raise ValueError("Fig12 editable path overlays require a source crop")
        for index, panel in enumerate(panels):
            path_overlay_inventory.append(
                _add_fig12_path_overlay(
                    overlay_layer,
                    panel,
                    index,
                    matrix_source_crop,
                    expected_names_by_layer[3],
                    required_graphobject_contracts,
                )
            )
        for pending in pending_overlay_labels:
            record = pending["record"]
            created = _add_scale_label(
                overlay_layer,
                pending["name"],
                record["text"],
                pending["x"],
                pending["y"],
                record["size"],
                role=record["role"],
                boxed=bool(record.get("boxed", False)),
                page_sized=True,
            )
            for inventory_record in label_inventory:
                if inventory_record["name"] == pending["name"]:
                    inventory_record["created"] = created
                    inventory_record["page_x"] = pending["x"]
                    inventory_record["page_y"] = pending["y"]
                    break
            contract = {"attach": 2}
            if record["role"] in {"panel", "mechanism"}:
                contract["text_contains"] = record["text"]
            required_graphobject_contracts[pending["name"]] = contract
            expected_names_by_layer[3].append(pending["name"])
    y_title_dx = (-44.0, -41.0, -44.0)
    y_title_dy = (60.0, 60.0, 65.0)
    if axis_title_overlays_enabled:
        for index, panel in enumerate(panels):
            left_pct, top_pct, width_pct, height_pct = FIG12_SOURCE_FRAMES_PERCENT[panel["name"]]
            left = left_pct / 100.0 * float(canvas_size[0])
            top = top_pct / 100.0 * HEIGHT
            width = width_pct / 100.0 * float(canvas_size[0])
            height = height_pct / 100.0 * HEIGHT
            axis_x_name = f"fig12_axis_overlay_x_{index + 1}"
            axis_y_name = f"fig12_axis_overlay_y_{index + 1}"
            x_ok = _add_fig12_axis_title_overlay(
                overlay_layer,
                axis_x_name,
                "Temperature/℃",
                left + 54.0,
                top + height + 20.0,
                10.0,
            )
            y_ok = _add_fig12_axis_title_overlay(
                overlay_layer,
                axis_y_name,
                "Strain rate/s\\+(-1)",
                left + y_title_dx[index],
                top + y_title_dy[index],
                10.2,
                rotate=90.0,
            )
            expected_names_by_layer[3].extend([axis_x_name, axis_y_name])
            required_graphobject_contracts[axis_x_name] = {"attach": 2, "text_contains": "Temperature"}
            required_graphobject_contracts[axis_y_name] = {"attach": 2, "text_contains": "Strain rate"}
    colorbar_bboxes = [
        (333.0, 82.0, 367.0, 188.0),
        (720.0, 82.0, 754.0, 188.0),
        (520.0, 358.0, 554.0, 470.0),
    ]
    colorbar_inventory = [
        _add_colorbar_overlay(
            overlay_layer,
            panel,
            index,
            _shift_bbox(
                colorbar_bboxes[index],
                dx=colorbar_offsets[index]["dx"],
                dy=colorbar_offsets[index]["dy"],
            ),
            label_sizes,
            required_graphobject_contracts,
            expected_names_by_layer[3],
        )
        for index, panel in enumerate(panels)
    ]

    axis_contract = [
        {
            "layer_index": index,
            "y.type": 2,
            "y_title_rotation": 0 if axis_title_overlays_enabled else 90,
            "y.minorTicks": y_minor_ticks,
        }
        for index in range(3)
    ]
    construction_visibility = reveal_graph_page(page)
    disable_speed_mode(page)
    return {
        "page_name": "Fig12_source_calibrated_three_panel_contour",
        "expected_plot_count": 3,
        "expected_plot_count_by_layer": {0: 1, 1: 1, 2: 1, 3: 0},
        "route": "worksheet_xyz_source_calibrated_three_panel_contour",
        "canvas_size": canvas_size,
        "page_size_inches": page_size_inches,
        "panel_inventory": panel_inventory,
        "required_worksheet_books": required_worksheet_books,
        "max_direct_plot_worksheet_rows": 5000,
        "declared_direct_plot_worksheet_rows": sum(int(panel["matrix"].size) for panel in panels),
        "fig12_levels_reapplied_after_palette": True,
        "fig12_contour_line_style_reapplied_after_levels": True,
        "fig12_native_contour_lines_requested_visible": not path_overlays_enabled,
        "fig12_origin_label_size_scales": dict(FIG12_ORIGIN_LABEL_SIZE_SCALES),
        "fig12_axis_tick_fsize": FIG12_AXIS_TICK_FSIZE,
        "fig12_axis_title_fsize": {
            "x": FIG12_X_AXIS_TITLE_FSIZE,
            "y": FIG12_Y_AXIS_TITLE_FSIZE,
        },
        "fig12_axis_font": FIG12_AXIS_FONT,
        "fig12_axis_title_overlays": axis_title_overlays_enabled,
        "fig12_axis_title_overlay_geometry": {
            "x": {"dx_from_panel_left": 54.0, "dy_from_panel_bottom": 20.0, "fsize": 10.0},
            "y": {
                "dx_from_panel_left": list(y_title_dx),
                "dy_from_panel_top": list(y_title_dy),
                "fsize": 10.2,
                "rotate": 90.0,
            },
        },
        "fig12_axis_title_text": {
            "x": "Temperature/\u2103",
            "y_origin_rich_text": "Strain rate/s\\+(-1)",
            "y_rendered_semantics": "Strain rate/s\u207b\u00b9",
        },
        "fig12_contour_line_color": list(FIG12_CONTOUR_LINE_COLOR),
        "fig12_contour_line_width": FIG12_CONTOUR_LINE_WIDTH,
        "worksheet_binding_inventory": worksheet_binding_inventory,
        "direct_worksheet_plot_contracts": [
            {"layer_index": index, "plot_index": 0, "plot_type_code": 243, "x_column": "A", "y_column": "B", "z_column": "C"}
            for index in range(3)
        ],
        "colorbar_inventory": colorbar_inventory,
        "fig12_colorbar_offsets": colorbar_offsets,
        "fig12_label_sizes": label_sizes,
        "fig12_matrix_biases": matrix_biases,
        "fig12_matrix_contrasts": matrix_contrasts,
        "fig12_matrix_region_values": matrix_region_values,
        "fig12_path_overlays": path_overlays_enabled,
        "path_overlay_inventory": path_overlay_inventory,
        "fig12_matrix_mode": matrix_mode,
        "fig12_matrix_resolution_scale": matrix_resolution_scale,
        "fig12_matrix_smoothing_sigma": matrix_smoothing_sigma,
        "fig12_y_minor_ticks": y_minor_ticks,
        "fig12_panel_layout_offsets": panel_layout_offsets,
        "label_inventory": label_inventory,
        "axis_contract": axis_contract,
        "required_graphobject_names_by_layer": expected_names_by_layer,
        "required_graphobject_contracts": required_graphobject_contracts,
        "expected_graphobject_count": len(required_graphobject_contracts),
        "construction_visibility": construction_visibility,
        "reproduction_mode": "reconstructed_approximate",
        "candidate_params": {
            key: value for key, value in candidate_params.items() if not str(key).startswith("_")
        },
    }
