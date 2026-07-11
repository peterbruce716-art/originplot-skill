from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import numpy as np


FIGURE_CANVAS = {
    "fig12": (805, 590),
    "fig15": (850, 335),
    "fig16": (720, 375),
}

PROVENANCE = "reconstructed_approximate"
FIG12_SOURCE_FRAMES_PERCENT = {
    "PSC": (12.2, 9.0, 27.8, 36.5),
    "UC": (60.7, 9.0, 27.8, 36.5),
    "TR": (35.4, 54.5, 27.8, 37.5),
}
FIG12_SOURCE_PALETTE = np.asarray(
    [(252, 191, 110), (177, 223, 137), (198, 223, 236)],
    dtype=float,
)
FIG12_SOURCE_PALETTE_MAX_DISTANCE = 25.0


def _gaussian2d(x: np.ndarray, y: np.ndarray, x0: float, y0: float, sx: float, sy: float) -> np.ndarray:
    return np.exp(-(((x - x0) / sx) ** 2 + ((y - y0) / sy) ** 2))


def _sigmoid(value: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-value))


def _fig12_rate_axis(name: str, ny: int) -> np.ndarray:
    max_rate = 1.0 if name == "TR" else 10.0
    # Fig12 is rendered on a logarithmic Y axis and the native Worksheet XYZ
    # route writes these same coordinates.  Keeping the sampled matrix rows on
    # the identical geometric grid prevents a second, unintended log warp.
    return np.geomspace(0.01, max_rate, ny)


def _classify_fig12_palette_pixels(
    pixels: np.ndarray,
    *,
    max_distance: float = FIG12_SOURCE_PALETTE_MAX_DISTANCE,
) -> tuple[np.ndarray, np.ndarray]:
    pixel_array = np.asarray(pixels, dtype=float)
    if pixel_array.ndim < 2 or pixel_array.shape[-1] != 3:
        raise ValueError("pixels must end with an RGB dimension")
    distances = np.linalg.norm(
        pixel_array[..., None, :] - FIG12_SOURCE_PALETTE,
        axis=-1,
    )
    return np.argmin(distances, axis=-1), np.min(distances, axis=-1) <= max_distance


def _fig12_matrix(name: str, levels: list[float], nx: int = 95, ny: int = 75) -> np.ndarray:
    x = np.linspace(250.0, 400.0, nx)
    log_rate = np.log10(_fig12_rate_axis(name, ny))
    xx, ll = np.meshgrid(x, log_rate)

    if name == "PSC":
        zz = 42.8 * np.ones_like(xx)
        zz -= 11.4 * _gaussian2d(xx, ll, 356, 0.73, 29, 0.22)
        zz -= 4.6 * _gaussian2d(xx, ll, 365, -1.24, 27, 0.48)
        zz -= 3.4 * _sigmoid((xx - 333) / 10.5) * _sigmoid((-0.62 - ll) / 0.18)
        zz += 1.0 * _gaussian2d(xx, ll, 272, 0.72, 28, 0.23)
        zz += 1.7 * _gaussian2d(xx, ll, 305, -0.08, 70, 0.55)
        zz += 2.0 * _gaussian2d(xx, ll, 397, -0.12, 24, 0.34)
    elif name == "UC":
        zz = 45.8 * np.ones_like(xx)
        zz -= 9.2 * _gaussian2d(xx, ll, 324, 0.72, 46, 0.22)
        zz -= 7.0 * _gaussian2d(xx, ll, 376, 0.83, 24, 0.20)
        zz -= 7.4 * _sigmoid((xx - 313) / 13.0) * _sigmoid((-0.55 - ll) / 0.24)
        zz += 1.4 * _gaussian2d(xx, ll, 270, 0.52, 34, 0.36)
        zz += 1.6 * _gaussian2d(xx, ll, 382, 0.10, 23, 0.24)
    else:
        zz = 55.2 * np.ones_like(xx)
        zz += 7.6 * _sigmoid((286 - xx) / 14.0)
        zz += 2.8 * _gaussian2d(xx, ll, 302, 0.22, 36, 0.42)
        zz -= 7.3 * _sigmoid((xx - 371) / 11.0) * _sigmoid((-0.78 - ll) / 0.22)
        zz -= 3.0 * _gaussian2d(xx, ll, 389, -1.12, 21, 0.36)

    # Origin 2022 maps the imported numpy matrix to the contour x direction
    # opposite to the array's column order in this builder route.
    return np.fliplr(np.clip(zz, min(levels), max(levels)))


def _fig12_source_matrix(
    name: str,
    levels: list[float],
    source_crop: str | Path,
    nx: int = 95,
    ny: int = 75,
    smoothing_sigma: float = 0.0,
) -> np.ndarray:
    from PIL import Image

    source_path = Path(source_crop)
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    with Image.open(source_path) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=float)
    height, width = rgb.shape[:2]
    left_pct, top_pct, width_pct, height_pct = FIG12_SOURCE_FRAMES_PERCENT[name]
    left = left_pct / 100.0 * width
    top = top_pct / 100.0 * height
    right = (left_pct + width_pct) / 100.0 * width
    bottom = (top_pct + height_pct) / 100.0 * height
    x0 = max(0, int(round(left)) + 1)
    y0 = max(0, int(round(top)) + 1)
    x1 = min(width, int(round(right)) - 1)
    y1 = min(height, int(round(bottom)) - 1)
    crop = rgb[y0:y1 + 1, x0:x1 + 1]
    classes, valid = _classify_fig12_palette_pixels(crop)
    filled_classes = _fill_invalid_class_regions(classes, valid)

    region_values = np.asarray(
        [
            (levels[2] + levels[3]) / 2.0,
            (levels[1] + levels[2]) / 2.0,
            (levels[0] + levels[1]) / 2.0,
        ]
    )
    # Preserve the source topology before reducing the Worksheet grid.  The
    # previous route classified only the final low-resolution grid, so thin
    # bands and junctions disappeared before Origin ever received the data.
    # Smooth at source-pixel scale, then sample at the requested logarithmic
    # rate coordinates.  Only the sampled matrix is written to the Worksheet.
    source_sigma = float(smoothing_sigma) * max(
        crop.shape[0] / max(ny, 1), crop.shape[1] / max(nx, 1)
    )
    source_values = _smooth_categorical_region_values(
        filled_classes,
        region_values,
        sigma=source_sigma,
    )
    rate_axis = _fig12_rate_axis(name, ny)
    log_low = math.log10(float(rate_axis[0]))
    log_high = math.log10(float(rate_axis[-1]))
    sample_x = np.linspace(0.0, crop.shape[1] - 1.0, nx)
    sample_y = (
        (log_high - np.log10(rate_axis)) / (log_high - log_low) * (crop.shape[0] - 1)
    )
    if float(smoothing_sigma) <= 0.0:
        sample_rows = np.rint(sample_y).astype(int)
        sample_columns = np.rint(sample_x).astype(int)
        return region_values[filled_classes[np.ix_(sample_rows, sample_columns)]]
    # Separable linear interpolation keeps the grid rectangular for native
    # XYZ contour plotting while retaining sub-pixel boundary locations.
    across_x = np.vstack([
        np.interp(sample_x, np.arange(source_values.shape[1]), row)
        for row in source_values
    ])
    sampled = np.vstack([
        np.interp(sample_y, np.arange(across_x.shape[0]), across_x[:, column])
        for column in range(across_x.shape[1])
    ]).T
    return sampled


def _fill_invalid_class_regions(classes: np.ndarray, valid: np.ndarray) -> np.ndarray:
    class_array = np.asarray(classes, dtype=int)
    valid_array = np.asarray(valid, dtype=bool)
    if class_array.shape != valid_array.shape or class_array.ndim != 2:
        raise ValueError("classes and valid must be equally shaped 2D arrays")
    if valid_array.all():
        return class_array.copy()
    if not valid_array.any():
        return np.zeros_like(class_array)

    height, width = class_array.shape
    unreachable = height + width + 1
    best_distance = np.full(class_array.shape, unreachable, dtype=int)
    filled = class_array.copy()
    best_distance[valid_array] = 0

    # Horizontal candidates win equal-distance ties, which keeps text masks
    # inside the surrounding contour band instead of spreading across bands.
    for row in range(height):
        last = -1
        for column in range(width):
            if valid_array[row, column]:
                last = column
            elif last >= 0:
                best_distance[row, column] = column - last
                filled[row, column] = class_array[row, last]
        last = width
        for column in range(width - 1, -1, -1):
            if valid_array[row, column]:
                last = column
            elif last < width and last - column < best_distance[row, column]:
                best_distance[row, column] = last - column
                filled[row, column] = class_array[row, last]

    for column in range(width):
        last = -1
        for row in range(height):
            if valid_array[row, column]:
                last = row
            elif last >= 0 and row - last < best_distance[row, column]:
                best_distance[row, column] = row - last
                filled[row, column] = class_array[last, column]
        last = height
        for row in range(height - 1, -1, -1):
            if valid_array[row, column]:
                last = row
            elif last < height and last - row < best_distance[row, column]:
                best_distance[row, column] = last - row
                filled[row, column] = class_array[last, column]

    return filled


def _smooth_categorical_region_values(
    classes: np.ndarray,
    region_values: np.ndarray,
    *,
    sigma: float,
) -> np.ndarray:
    sigma = max(0.0, float(sigma))
    values = np.asarray(region_values, dtype=float)
    if sigma <= 1e-9:
        return values[np.asarray(classes, dtype=int)]

    radius = max(1, int(math.ceil(3.0 * sigma)))
    offsets = np.arange(-radius, radius + 1, dtype=float)
    kernel = np.exp(-0.5 * (offsets / sigma) ** 2)
    kernel /= kernel.sum()

    class_array = np.asarray(classes, dtype=int)
    weights = np.stack(
        [(class_array == index).astype(float) for index in range(len(values))],
        axis=2,
    )
    for axis in (0, 1):
        pad = [(0, 0)] * weights.ndim
        pad[axis] = (radius, radius)
        padded = np.pad(weights, pad, mode="edge")
        weights = np.apply_along_axis(
            lambda row: np.convolve(row, kernel, mode="valid"),
            axis,
            padded,
        )
    weights /= np.maximum(weights.sum(axis=2, keepdims=True), 1e-12)
    return np.tensordot(weights, values, axes=([2], [0]))


def fig12_panels(
    source_crop: str | Path | None = None,
    nx: int = 95,
    ny: int = 75,
    smoothing_sigma: float = 0.0,
) -> list[dict[str, Any]]:
    definitions = [
        {
            "name": "PSC",
            "panel": "(a)",
            "ylim": (0.01, 10.0),
            "levels": [27.90, 35.55, 41.08, 54.00],
            "layout_percent": (12.2, 9.0, 27.8, 36.5),
            "labels": [(271, 6.2, "38.78"), (338, 8.1, "35.55"), (250, 3.3, "41.08"), (306, 1.84, "41.08"), (330, 0.113, "41.08"), (344, 0.03, "38.78")],
            "mechanisms": [(292, 0.44, "GF"), (348, 0.064, "GF+GR"), (348, 5.0, "GR")],
        },
        {
            "name": "UC",
            "panel": "(b)",
            "ylim": (0.01, 10.0),
            "levels": [30.20, 37.79, 45.19, 56.90],
            "layout_percent": (60.7, 9.0, 27.8, 36.5),
            "labels": [(251, 7.4, "45.19"), (279, 2.4, "45.19"), (300, 4.1, "37.79"), (334, 5.5, "37.79"), (364, 1.47, "45.19"), (377, 0.0165, "37.79"), (351, 10.6, "41.19")],
            "mechanisms": [(290, 0.43, "GF"), (343, 0.064, "GF+GR"), (355, 6.1, "GR")],
        },
        {
            "name": "TR",
            "panel": "(c)",
            "ylim": (0.01, 1.0),
            "levels": [45.70, 49.77, 60.17, 67.20],
            "layout_percent": (35.4, 54.5, 27.8, 37.5),
            "labels": [(300, 0.46, "60.17"), (312, 0.155, "54.38"), (359, 0.054, "49.77")],
            "mechanisms": [(267, 0.52, "GF"), (292, 0.096, "GF+GR"), (369, 0.030, "GR")],
        },
    ]
    source_path = Path(source_crop) if source_crop else None
    source_matrix_available = bool(source_path and source_path.is_file())
    for item in definitions:
        item.update(
            {
                "xlim": (250.0, 400.0),
                "matrix": (
                    _fig12_source_matrix(
                        item["name"],
                        item["levels"],
                        source_path,
                        nx=nx,
                        ny=ny,
                        smoothing_sigma=smoothing_sigma,
                    )
                    if source_matrix_available
                    else _fig12_matrix(item["name"], item["levels"], nx=nx, ny=ny)
                ),
                "matrix_source": (
                    "source_palette_digitized" if source_matrix_available else "analytic_fallback"
                ),
                "matrix_smoothing_sigma": float(smoothing_sigma) if source_matrix_available else 0.0,
                "xymap": (250.0, 400.0, item["ylim"][0], item["ylim"][1]),
                "provenance": PROVENANCE,
            }
        )
    return definitions


def _normalize_axis_x(x: float, axis_bounds: tuple[float, float, float, float]) -> float:
    left, _, right, _ = axis_bounds
    return (float(x) - left) / (right - left)


def _normalize_axis_y(y: float, axis_bounds: tuple[float, float, float, float]) -> float:
    _, top, _, bottom = axis_bounds
    return (bottom - float(y)) / (bottom - top)


def _segments_to_path(
    segments: list[tuple[float, float, float, float]],
    axis_bounds: tuple[float, float, float, float],
) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for x1, y1, x2, y2 in segments:
        xs.extend([_normalize_axis_x(x1, axis_bounds), _normalize_axis_x(x2, axis_bounds), math.nan])
        ys.extend([_normalize_axis_y(y1, axis_bounds), _normalize_axis_y(y2, axis_bounds), math.nan])
    return xs, ys


def _circle_path(
    center_x: float,
    center_y: float,
    radius: float,
    axis_bounds: tuple[float, float, float, float],
) -> tuple[list[float], list[float]]:
    theta = np.linspace(0.0, 2.0 * np.pi, 50)
    xs = [_normalize_axis_x(center_x + radius * math.cos(value), axis_bounds) for value in theta]
    ys = [_normalize_axis_y(center_y + radius * math.sin(value), axis_bounds) for value in theta]
    return xs, ys


def _fig15_panel(name: str) -> dict[str, Any]:
    if name == "PSC":
        axis_bounds = (60.0, 25.0, 400.0, 273.0)
        axes = [
            (67, 266, 400, 266), (67, 266, 67, 25),
            (400, 266, 389, 259), (400, 266, 389, 273),
            (67, 25, 61, 38), (67, 25, 73, 38),
        ]
        guides = [(90, 266, 90, 123), (112, 266, 112, 73), (274, 266, 274, 101), (67, 73, 274, 73), (67, 101, 274, 101), (67, 123, 112, 123)]
        centers = [(101, 174, "1"), (198, 174, "2"), (329, 174, "3")]
        header_centers = [(248, 42, "1"), (248, 62, "2"), (248, 82, "3")]
        curve_points = [(67.0, 263.5), (69.0, 254.0), (88.0, 113.5), (96.0, 85.0), (99.0, 79.5), (104.0, 75.0), (110.0, 72.5), (119.0, 73.5), (151.0, 88.5), (162.0, 92.5), (176.0, 95.5), (193.0, 97.5), (271.0, 100.5), (371.0, 99.5)]
    else:
        axis_bounds = (471.0, 25.0, 809.0, 273.0)
        axes = [
            (478, 266, 809, 266), (478, 266, 478, 25),
            (809, 266, 798, 259), (809, 266, 798, 273),
            (478, 25, 472, 38), (478, 25, 484, 38),
        ]
        guides = [(497, 266, 497, 113), (611, 266, 611, 82), (478, 82, 611, 82), (478, 113, 497, 113)]
        centers = [(558, 174, "1"), (686, 174, "2")]
        header_centers = [(657, 42, "1"), (657, 62, "2")]
        curve_points = [(478.0, 259.0), (497.0, 118.5), (499.0, 111.5), (508.0, 104.0), (522.0, 97.0), (543.0, 89.5), (559.0, 85.5), (582.0, 82.5), (645.0, 80.5), (784.0, 81.5)]

    left, top, right, bottom = axis_bounds
    canvas_width, canvas_height = FIGURE_CANVAS["fig15"]
    frame_percent = (
        left / canvas_width * 100.0,
        top / canvas_height * 100.0,
        (right - left) / canvas_width * 100.0,
        (bottom - top) / canvas_height * 100.0,
    )
    axis_x, axis_y = _segments_to_path(axes, axis_bounds)
    guide_x, guide_y = _segments_to_path(guides, axis_bounds)

    def circles(records: list[tuple[float, float, str]], radius: float) -> list[dict[str, Any]]:
        result = []
        for cx, cy, text in records:
            circle_x, circle_y = _circle_path(cx, cy, radius, axis_bounds)
            result.append(
                {
                    "x": circle_x,
                    "y": circle_y,
                    "text": text,
                    "center": (_normalize_axis_x(cx, axis_bounds), _normalize_axis_y(cy, axis_bounds)),
                }
            )
        return result

    curve_x = [_normalize_axis_x(x, axis_bounds) for x, _ in curve_points]
    curve_y = [_normalize_axis_y(y, axis_bounds) for _, y in curve_points]

    return {
        "name": name,
        "frame_percent": frame_percent,
        "axes": {"x": axis_x, "y": axis_y, "arrowhead_segment_count": 4},
        "guides": {"x": guide_x, "y": guide_y},
        "curve": {"x": curve_x, "y": curve_y, "method": "digitized_source_centerline"},
        "stage_circles": circles(centers, 11.0),
        "header_circles": circles(header_centers, 7.0),
        "axis_bounds_source_pixels": axis_bounds,
        "provenance": PROVENANCE,
    }


def fig15_geometry() -> dict[str, Any]:
    labels = [
        ("panel", "(a)", 14, 39, 11), ("panel", "(b)", 404, 39, 11),
        ("title", "PSC", 196, 46, 15), ("title", "UC/TR", 582, 46, 15),
        ("axis", r"\g(e)", 367, 282, 10), ("axis", r"\g(s)", 76, 51, 10),
        ("axis", r"\g(e)", 777, 282, 10), ("axis", r"\g(s)", 487, 51, 10),
        ("stress", r"\g(s)\-(p)", 40, 77, 9), ("stress", r"\g(s)\-(s)", 40, 104, 9),
        ("stress", r"\g(s)\-(0)", 40, 126, 9), ("stress", r"\g(s)\-(s) ~ \g(s)\-(p)", 431, 85, 8),
        ("stress", r"\g(s)\-(0)", 452, 116, 9),
        ("stage", "1", 101, 174, 9), ("stage", "2", 198, 174, 9), ("stage", "3", 329, 174, 9),
        ("stage", "1", 558, 174, 9), ("stage", "2", 686, 174, 9),
        ("header_stage", "1", 248, 42, 8), ("description", "Hardening stage", 263, 42, 8),
        ("header_stage", "2", 248, 62, 8), ("description", "Softening stage", 263, 62, 8),
        ("header_stage", "3", 248, 82, 8), ("description", "Steady-state stage", 263, 82, 8),
        ("header_stage", "1", 657, 42, 8), ("description", "Hardening stage", 672, 42, 8),
        ("header_stage", "2", 657, 62, 8), ("description", "Steady-state stage", 672, 62, 8),
    ]
    return {
        "canvas": FIGURE_CANVAS["fig15"],
        "panels": [_fig15_panel("PSC"), _fig15_panel("UC_TR")],
        "labels": [{"role": role, "text": text, "x": x, "y": y, "font_size": size} for role, text, x, y, size in labels],
        "caption": "Fig. 15. Flow stress curve diagram of AA2195 for (a) PSC and (b) UC/TR tests.",
        "provenance": PROVENANCE,
    }


def fig16_geometry() -> dict[str, Any]:
    colors = {"WH": "#ff9830", "DRV": "#00ff98", "DRX": "#d098ff"}
    boxes = {
        "WH": [(24, 148, 63, 334), (116, 134, 156, 334), (208, 93, 249, 334), (318, 134, 359, 334), (409, 93, 451, 334), (517, 134, 558, 334), (608, 93, 650, 334)],
        "DRV": [(64, 202, 105, 334), (157, 174, 198, 334), (250, 161, 291, 334), (360, 229, 402, 334), (452, 202, 494, 334), (559, 242, 600, 334), (651, 215, 692, 334)],
        "DRX": [(64, 188, 105, 202), (157, 120, 198, 174), (250, 93, 291, 161), (360, 161, 402, 229), (452, 93, 494, 202), (559, 161, 600, 242), (651, 93, 692, 215)],
    }
    bars = [
        {"family": family, "bbox": bbox, "color": colors[family], "name": f"{family.lower()}_{index + 1:02d}"}
        for family, family_boxes in boxes.items()
        for index, bbox in enumerate(family_boxes)
    ]
    group_boxes = [
        {"name": "PSC", "bbox": (13, 62, 301, 365)},
        {"name": "CP", "bbox": (308, 62, 502, 365)},
        {"name": "TR", "bbox": (510, 62, 702, 365)},
    ]
    stage_labels = [
        {"x": 65, "y": 352, "stage": "1", "relation": "H>S", "relation_x": 61, "relation_y": 128},
        {"x": 157, "y": 352, "stage": "2", "relation": "H<S", "relation_x": 148, "relation_y": 102},
        {"x": 250, "y": 352, "stage": "3", "relation": "H≈S", "relation_x": 241, "relation_y": 80},
        {"x": 360, "y": 352, "stage": "1", "relation": "H>S", "relation_x": 342, "relation_y": 120},
        {"x": 452, "y": 352, "stage": "2", "relation": "H≈S", "relation_x": 437, "relation_y": 80},
        {"x": 559, "y": 352, "stage": "1", "relation": "H>S", "relation_x": 549, "relation_y": 120},
        {"x": 650, "y": 352, "stage": "2", "relation": "H≈S", "relation_x": 632, "relation_y": 80},
    ]
    legend = [
        {"label": "WH", "bbox": (601, 0, 639, 10), "color": colors["WH"]},
        {"label": "DRV", "bbox": (601, 17, 639, 29), "color": colors["DRV"]},
        {"label": "DRX", "bbox": (601, 37, 639, 50), "color": colors["DRX"]},
    ]
    return {
        "canvas": FIGURE_CANVAS["fig16"],
        "bars": bars,
        "group_boxes": group_boxes,
        "stage_labels": stage_labels,
        "legend": legend,
        "colors": colors,
        "provenance": PROVENANCE,
    }
