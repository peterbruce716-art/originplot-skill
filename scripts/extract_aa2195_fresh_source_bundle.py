from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import cv2
import fitz
import numpy as np
from PIL import Image, ImageDraw


SCHEMA = "originplot.aa2195_fresh_source_bundle.v1"
FIGURES = ("fig3", "fig12", "fig14", "fig15", "fig16")
PDF_CLIPS = {
    "fig3": {"page": 5, "rect": (95.0, 48.3333333333, 510.0, 348.3333333333), "scale": 3.0, "size": (1245, 900)},
    "fig12": {"page": 10, "rect": (90.0, 432.5, 492.5, 727.5), "scale": 2.0, "size": (805, 590)},
    "fig14": {"page": 12, "rect": (35.0, 50.0, 301.6666666667, 265.0), "scale": 3.0, "size": (800, 645)},
    "fig15": {"page": 12, "rect": (92.5, 357.5, 517.5, 525.0), "scale": 2.0, "size": (850, 335)},
    "fig16": {"page": 12, "rect": (120.0, 542.5, 480.0, 730.0), "scale": 2.0, "size": (720, 375)},
}
FIG3_COLORS = {
    "250": (27, 158, 119),
    "300": (217, 95, 2),
    "350": (117, 112, 179),
    "400": (231, 41, 138),
}
FIG3_PANELS = {
    "a": {"axis": (137.08, 56.31, 295.66, 184.56), "ymax": 225.0, "strain_rate": "0.01", "panel": "(a)", "frame_percent": (10.2, 2.6, 38.2, 42.7), "modes": ("PSC", "UC", "TR")},
    "b": {"axis": (336.83, 55.98, 495.55, 184.10), "ymax": 225.0, "strain_rate": "0.1", "panel": "(b)", "frame_percent": (58.4, 2.6, 38.2, 42.7), "modes": ("PSC", "UC", "TR")},
    "c": {"axis": (137.08, 211.36, 295.66, 339.61), "ymax": 250.0, "strain_rate": "1", "panel": "(c)", "frame_percent": (10.2, 54.3, 38.2, 42.6), "modes": ("PSC", "UC", "TR")},
    "d": {"axis": (336.47, 211.30, 495.20, 339.71), "ymax": 250.0, "strain_rate": "10", "panel": "(d)", "frame_percent": (58.4, 54.3, 38.2, 42.6), "modes": ("PSC", "UC")},
}
FIG14_COLORS = {
    "PSC": np.asarray((239, 75, 75), dtype=float),
    "UC": np.asarray((38, 117, 216), dtype=float),
    "TR": np.asarray((53, 166, 107), dtype=float),
}
FIG14_SYMBOLS = {"PSC": 1, "UC": 2, "TR": 3}
FIG14_TEMPERATURES = (250.0, 300.0, 350.0, 400.0)
FIG3_POINTS_PER_CURVE = 181


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_digest(payload: Any) -> str:
    return _sha256_bytes(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    )


def _render_crop(document: fitz.Document, figure: str, output: Path) -> dict[str, Any]:
    config = PDF_CLIPS[figure]
    page = document[int(config["page"]) - 1]
    rect = fitz.Rect(*config["rect"])
    scale = float(config["scale"])
    pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect, alpha=False)
    expected_size = tuple(config["size"])
    if (pixmap.width, pixmap.height) != expected_size:
        raise RuntimeError(
            f"{figure} PDF crop changed size: expected {expected_size}, got {(pixmap.width, pixmap.height)}"
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    pixmap.save(output)
    if figure == "fig12":
        with Image.open(output) as image:
            canonical = image.convert("RGB")
        ImageDraw.Draw(canonical).rectangle((0, 0, 805, 40), fill="white")
        canonical.save(output)
    return {
        "page_one_based": int(config["page"]),
        "pdf_clip_points": [float(value) for value in config["rect"]],
        "render_scale": scale,
        "canvas_size": list(expected_size),
        "canonicalization": "blank_top_paper_text_band_0_0_805_40" if figure == "fig12" else "none",
    }


def _rgb255(value: Any) -> tuple[int, int, int] | None:
    if not value or len(value) != 3:
        return None
    return tuple(int(round(float(channel) * 255.0)) for channel in value)


def _flatten_drawing(drawing: dict[str, Any], samples_per_curve: int = 12) -> np.ndarray:
    points: list[tuple[float, float]] = []
    for item in drawing.get("items", []):
        command = item[0]
        if command == "l" and len(item) >= 3:
            for point in item[1:3]:
                points.append((float(point.x), float(point.y)))
        elif command == "c" and len(item) >= 5:
            p0, p1, p2, p3 = item[1:5]
            for t in np.linspace(0.0, 1.0, samples_per_curve, endpoint=True):
                omt = 1.0 - float(t)
                x = omt**3 * p0.x + 3.0 * omt**2 * t * p1.x + 3.0 * omt * t**2 * p2.x + t**3 * p3.x
                y = omt**3 * p0.y + 3.0 * omt**2 * t * p1.y + 3.0 * omt * t**2 * p2.y + t**3 * p3.y
                points.append((float(x), float(y)))
        elif command == "re" and len(item) >= 2:
            rect = item[1]
            points.extend(
                [(float(rect.x0), float(rect.y0)), (float(rect.x1), float(rect.y0)), (float(rect.x1), float(rect.y1)), (float(rect.x0), float(rect.y1))]
            )
    return np.asarray(points, dtype=float)


def _split_fig3_curve_groups(drawings: list[dict[str, Any]], axis: tuple[float, float, float, float]) -> list[list[dict[str, Any]]]:
    left, top, right, bottom = axis
    data_right = left + (0.9 / 1.1) * (right - left)
    selected: list[dict[str, Any]] = []
    for drawing in drawings:
        rect = drawing["rect"]
        width = float(rect.x1 - rect.x0)
        if rect.x0 < left - 1.0 or rect.x1 > data_right + 2.0:
            continue
        if rect.y0 < top - 1.0 or rect.y1 > bottom + 1.0:
            continue
        if rect.y1 < top + 0.16 * (bottom - top):
            continue
        if width < 0.3:
            continue
        selected.append(drawing)
    groups: list[list[dict[str, Any]]] = []
    previous_x = math.inf
    previous_width = 0.0
    for drawing in selected:
        rect = drawing["rect"]
        width = float(rect.x1 - rect.x0)
        starts_new = not groups or rect.x0 < previous_x - 2.0 or previous_width > 20.0
        if starts_new:
            groups.append([])
        groups[-1].append(drawing)
        previous_x = float(rect.x0)
        previous_width = width
    data_width = data_right - left
    return [
        group
        for group in groups
        if group
        and max(item["rect"].x1 for item in group)
        - min(item["rect"].x0 for item in group)
        >= 0.45 * data_width
    ]


def _drawing_group_centerline(
    group: list[dict[str, Any]],
    axis: tuple[float, float, float, float],
    *,
    ymax: float,
) -> dict[str, list[float]]:
    left, top, right, bottom = axis
    arrays = [_flatten_drawing(drawing) for drawing in group]
    points = np.vstack([item for item in arrays if item.size])
    valid = (
        (points[:, 0] >= left - 0.5)
        & (points[:, 0] <= right + 0.5)
        & (points[:, 1] >= top - 0.5)
        & (points[:, 1] <= bottom + 0.5)
    )
    points = points[valid]
    if len(points) < 8:
        raise RuntimeError("Fig3 source path did not contain enough curve points")
    bin_width = 0.20
    bins = np.round((points[:, 0] - left) / bin_width).astype(int)
    unique_bins = np.unique(bins)
    source_x = np.asarray([np.median(points[bins == value, 0]) for value in unique_bins], dtype=float)
    source_y = np.asarray([np.median(points[bins == value, 1]) for value in unique_bins], dtype=float)
    order = np.argsort(source_x)
    source_x, source_y = source_x[order], source_y[order]
    strain = np.linspace(0.0, 0.9, FIG3_POINTS_PER_CURVE)
    target_pdf_x = left + strain / 1.1 * (right - left)
    curve_pdf_y = np.interp(target_pdf_x, source_x, source_y)
    stress = np.clip((bottom - curve_pdf_y) / (bottom - top) * float(ymax), 0.0, float(ymax))
    stress[0] = 0.0
    return {
        "x": [round(float(value), 6) for value in strain],
        "y": [round(float(value), 6) for value in stress],
    }


def _extract_fig3_data(document: fitz.Document) -> dict[str, Any]:
    page = document[PDF_CLIPS["fig3"]["page"] - 1]
    drawings = page.get_drawings()
    panels: list[dict[str, Any]] = []
    for panel_name, config in FIG3_PANELS.items():
        axis = tuple(float(value) for value in config["axis"])
        panel_series: dict[str, dict[str, dict[str, list[float]]]] = {}
        for temperature, rgb in FIG3_COLORS.items():
            colored = [drawing for drawing in drawings if _rgb255(drawing.get("fill")) == rgb]
            groups = _split_fig3_curve_groups(colored, axis)
            expected_modes = tuple(config["modes"])
            if len(groups) != len(expected_modes):
                raise RuntimeError(
                    f"Fig3 panel {panel_name} temperature {temperature} expected {len(expected_modes)} source paths, got {len(groups)}"
                )
            panel_series[temperature] = {
                mode: _drawing_group_centerline(group, axis, ymax=float(config["ymax"]))
                for mode, group in zip(expected_modes, groups)
            }
        panels.append(
            {
                "name": panel_name,
                "panel": config["panel"],
                "strain_rate": config["strain_rate"],
                "ymax": float(config["ymax"]),
                "frame_percent": [float(value) for value in config["frame_percent"]],
                "series": panel_series,
            }
        )
    return {
        "method": "fresh_pdf_vector_path_centerline_digitization",
        "page_one_based": 5,
        "points_per_curve": FIG3_POINTS_PER_CURVE,
        "panels": panels,
    }


def _color_mask(rgb: np.ndarray, target: np.ndarray, tolerance: float) -> np.ndarray:
    return np.linalg.norm(rgb.astype(float) - target.reshape(1, 1, 3), axis=2) <= float(tolerance)


def _fig14_marker_center(mask: np.ndarray, x: int, predicted_y: float | None) -> float:
    x0, x1 = max(0, x - 12), min(mask.shape[1], x + 13)
    row_counts = mask[:, x0:x1].sum(axis=1).astype(float)
    candidate_rows = np.flatnonzero(row_counts >= max(3.0, row_counts.max() * 0.45))
    if not len(candidate_rows):
        raise RuntimeError(f"Fig14 marker was not found near x={x}")
    if predicted_y is not None:
        candidate_rows = candidate_rows[np.abs(candidate_rows - predicted_y) <= 130]
    if not len(candidate_rows):
        raise RuntimeError(f"Fig14 marker search lost continuity near x={x}")
    groups = np.split(candidate_rows, np.flatnonzero(np.diff(candidate_rows) > 3) + 1)
    centers = [float(np.average(group, weights=row_counts[group])) for group in groups]
    if predicted_y is None:
        selected = int(np.argmax(centers))
    else:
        selected = int(np.argmin(np.abs(np.asarray(centers) - predicted_y)))
    group = groups[selected]
    return float(np.average(group, weights=row_counts[group]))


def _fig14_error_extent(rgb: np.ndarray, x: int, marker_y: float) -> tuple[float, float]:
    black = np.max(rgb, axis=2) < 105
    y0, y1 = max(0, int(round(marker_y)) - 55), min(rgb.shape[0], int(round(marker_y)) + 56)
    x0, x1 = max(0, x - 12), min(rgb.shape[1], x + 13)
    local = np.ascontiguousarray(black[y0:y1, x0:x1].astype(np.uint8))
    count, _, stats, _ = cv2.connectedComponentsWithStats(local, connectivity=8)
    center_x = x - x0
    candidates: list[tuple[float, float, float]] = []
    for label in range(1, count):
        component_x, component_y, width, height, area = (int(value) for value in stats[label])
        component_right = component_x + width - 1
        if area < 2 or component_right < center_x - 3 or component_x > center_x + 3:
            continue
        top = float(y0 + component_y)
        bottom = float(y0 + component_y + height - 1)
        distance = max(top - marker_y, marker_y - bottom, 0.0)
        candidates.append((distance, top, bottom))

    touching = [item for item in candidates if item[0] == 0.0]
    if touching:
        return min(item[1] for item in touching), max(item[2] for item in touching)

    # A filled marker can split the vertical error bar into an upper and lower
    # component. Select only the nearest component on each side of this marker;
    # the other series at the same x coordinate must not extend this interval.
    upper = [item for item in candidates if item[2] < marker_y]
    lower = [item for item in candidates if item[1] > marker_y]
    selected: list[tuple[float, float, float]] = []
    if upper:
        selected.append(min(upper, key=lambda item: (item[0], -item[2])))
    if lower:
        selected.append(min(lower, key=lambda item: (item[0], item[1])))
    selected = [item for item in selected if item[0] <= 12.0]
    if not selected:
        raise RuntimeError(f"Fig14 error bar was not found near x={x}")
    return min(item[1] for item in selected), max(item[2] for item in selected)


def _fig14_error_magnitude(marker_y: float, error_top: float, error_bottom: float, axis_height: float) -> float:
    pixel_extent = max(abs(marker_y - error_top), abs(error_bottom - marker_y))
    return pixel_extent / axis_height * 0.4


def _extract_fig14_data(source_crop: Path) -> dict[str, Any]:
    with Image.open(source_crop) as image:
        rgb = np.asarray(image.convert("RGB"))
    axis = (113.0, 29.0, 753.0, 544.0)
    left, top, right, bottom = axis
    series: dict[str, Any] = {}
    for mode, target in FIG14_COLORS.items():
        mask = _color_mask(rgb, target, 55.0)
        values: list[float] = []
        errors: list[float] = []
        predicted_y: float | None = None
        for temperature in FIG14_TEMPERATURES:
            x = int(round(left + (temperature - 230.0) / (420.0 - 230.0) * (right - left)))
            marker_y = _fig14_marker_center(mask, x, predicted_y)
            err_top, err_bottom = _fig14_error_extent(rgb, x, marker_y)
            value = (bottom - marker_y) / (bottom - top) * 0.4
            error = _fig14_error_magnitude(marker_y, err_top, err_bottom, bottom - top)
            values.append(round(float(value), 6))
            errors.append(round(float(error), 6))
            predicted_y = marker_y
        series[mode] = {
            "y": values,
            "err": errors,
            "color": "#%02x%02x%02x" % tuple(int(value) for value in target),
            "symbol": FIG14_SYMBOLS[mode],
        }
    return {
        "method": "fresh_source_crop_color_marker_and_component_errorbar_digitization",
        "temperature": list(FIG14_TEMPERATURES),
        "axis_source_pixels": list(axis),
        "series": series,
    }


def _trace_colored_curve(
    rgb: np.ndarray,
    axis: tuple[float, float, float, float],
    *,
    samples: int = 91,
) -> dict[str, list[float]]:
    left, top, right, bottom = axis
    blue = (rgb[:, :, 2] > 175) & (rgb[:, :, 2] > rgb[:, :, 0] * 1.8) & (rgb[:, :, 2] > rgb[:, :, 1] * 1.5)
    normalized_x = np.linspace(0.0, 1.0, samples)
    target_x = left + normalized_x * (right - left)
    raw_y = np.full(samples, np.nan, dtype=float)
    for index, x in enumerate(target_x):
        column = int(round(float(x)))
        ys = np.flatnonzero(blue[max(0, int(top) - 3): min(rgb.shape[0], int(bottom) + 4), max(0, column - 2): min(rgb.shape[1], column + 3)].any(axis=1))
        if len(ys):
            raw_y[index] = float(np.median(ys + max(0, int(top) - 3)))
    valid = np.flatnonzero(np.isfinite(raw_y))
    if len(valid) < samples // 2:
        raise RuntimeError("Fig15 blue curve digitization found too few source pixels")
    first, last = int(valid.min()), int(valid.max())
    retained = np.arange(first, last + 1)
    raw_y = np.interp(retained, valid, raw_y[valid])
    normalized_x = normalized_x[retained]
    normalized_y = np.clip((bottom - raw_y) / (bottom - top), 0.0, 1.0)
    return {
        "x": [round(float(value), 6) for value in normalized_x],
        "y": [round(float(value), 6) for value in normalized_y],
        "method": "fresh_source_crop_blue_centerline",
    }


def _extract_fig15_data(source_crop: Path) -> dict[str, Any]:
    with Image.open(source_crop) as image:
        rgb = np.asarray(image.convert("RGB"))
    panels = {
        "PSC": {"axis": (60.0, 25.0, 400.0, 273.0)},
        "UC_TR": {"axis": (471.0, 25.0, 809.0, 273.0)},
    }
    for record in panels.values():
        record["curve"] = _trace_colored_curve(rgb, tuple(record["axis"]))
    return {
        "method": "fresh_source_crop_curve_digitization",
        "panels": panels,
    }


def _component_boxes(mask: np.ndarray, expected: int) -> list[list[int]]:
    count, _, stats, _ = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    boxes: list[list[int]] = []
    for index in range(1, count):
        x, y, width, height, area = [int(value) for value in stats[index]]
        if area < 120 or width < 10 or height < 8:
            continue
        if y < round(mask.shape[0] * 0.18):
            continue
        boxes.append([x, y, x + width, y + height])
    boxes.sort(key=lambda item: (item[0], item[1]))
    if len(boxes) != expected:
        raise RuntimeError(f"Fig16 expected {expected} colored bar regions, got {len(boxes)}")
    return boxes


def _extract_fig16_data(source_crop: Path) -> dict[str, Any]:
    with Image.open(source_crop) as image:
        rgb = np.asarray(image.convert("RGB"))
    targets = {
        "WH": np.asarray((255, 152, 48), dtype=float),
        "DRV": np.asarray((0, 239, 155), dtype=float),
        "DRX": np.asarray((194, 139, 237), dtype=float),
    }
    bars: dict[str, list[list[int]]] = {}
    colors: dict[str, str] = {}
    for family, target in targets.items():
        mask = _color_mask(rgb, target, 45.0)
        boxes = _component_boxes(mask, 7)
        bars[family] = boxes
        pixels = rgb[mask]
        median = np.median(pixels, axis=0).astype(int)
        colors[family] = "#%02x%02x%02x" % tuple(int(value) for value in median)
    return {
        "method": "fresh_source_crop_connected_component_bar_digitization",
        "bars": bars,
        "colors": colors,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract a fresh AA2195 five-figure source and data bundle from the paper PDF.")
    parser.add_argument("--source-pdf", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    source_pdf = args.source_pdf.resolve()
    output_dir = args.output_dir.resolve()
    json_out = args.json_out.resolve() if args.json_out else output_dir / "source_bundle.json"
    if not source_pdf.is_file():
        raise FileNotFoundError(source_pdf)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("E126_STALE_OUTPUT_ROOT: fresh source bundle output directory must be empty")
    output_dir.mkdir(parents=True, exist_ok=True)

    document = fitz.open(source_pdf)
    if document.page_count < 12:
        raise RuntimeError("AA2195 source PDF must contain at least 12 pages")
    figures: dict[str, Any] = {}
    crop_paths: dict[str, Path] = {}
    for figure in FIGURES:
        filename = "fig12_source_canonical.png" if figure == "fig12" else f"{figure}_source.png"
        crop_path = output_dir / filename
        crop_paths[figure] = crop_path
        extraction = _render_crop(document, figure, crop_path)
        figures[figure] = {
            "source_crop": filename,
            "source_crop_sha256": _sha256_file(crop_path),
            "source_crop_size_bytes": crop_path.stat().st_size,
            "extraction": extraction,
        }

    data_by_figure = {
        "fig3": _extract_fig3_data(document),
        "fig12": {"method": "fresh_source_crop_palette_classification_at_builder_runtime"},
        "fig14": _extract_fig14_data(crop_paths["fig14"]),
        "fig15": _extract_fig15_data(crop_paths["fig15"]),
        "fig16": _extract_fig16_data(crop_paths["fig16"]),
    }
    for figure, data in data_by_figure.items():
        figures[figure]["data"] = data
        figures[figure]["data_sha256"] = _stable_digest(data)

    payload = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fresh_extraction": True,
        "source_pdf": {
            "filename": source_pdf.name,
            "sha256": _sha256_file(source_pdf),
            "size_bytes": source_pdf.stat().st_size,
            "page_count": document.page_count,
        },
        "figures": figures,
    }
    payload["bundle_data_sha256"] = _stable_digest(
        {
            figure: {
                "source_crop_sha256": figures[figure]["source_crop_sha256"],
                "data_sha256": figures[figure]["data_sha256"],
            }
            for figure in FIGURES
        }
    )
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "json_out": str(json_out), "bundle_data_sha256": payload["bundle_data_sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
