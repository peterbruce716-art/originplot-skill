from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

SKILL_ROOT = Path(__file__).resolve().parents[1]
if str(SKILL_ROOT) not in sys.path:
    sys.path.insert(0, str(SKILL_ROOT))

from builders.aa2195.fig12_builder import _apply_matrix_bias
from builders.aa2195.geometry import (
    FIG12_SOURCE_FRAMES_PERCENT,
    _classify_fig12_palette_pixels,
    _fig12_source_matrix,
    _fill_invalid_class_regions,
    fig12_panels,
)


def reconstruct_source_grid(matrix: np.ndarray, *, width: int, height: int) -> np.ndarray:
    """Interpolate a low-row native XYZ matrix back onto its source-pixel grid."""
    values = np.asarray(matrix, dtype=float)
    if values.ndim != 2 or min(values.shape) < 2:
        raise ValueError("matrix must be a 2D array with at least two rows and columns")
    if width < 2 or height < 2:
        raise ValueError("target width and height must be at least two")
    source_x = np.arange(values.shape[1], dtype=float)
    target_x = np.linspace(0.0, values.shape[1] - 1.0, width)
    across_x = np.vstack([np.interp(target_x, source_x, row) for row in values])
    source_y = np.arange(values.shape[0], dtype=float)
    # Matrix row zero is the lowest rate, while source-image row zero is the highest rate.
    target_y = np.linspace(values.shape[0] - 1.0, 0.0, height)
    return np.vstack(
        [np.interp(target_y, source_y, across_x[:, column]) for column in range(width)]
    ).T


def classify_contour_regions(values: np.ndarray, levels: list[float]) -> np.ndarray:
    if len(levels) != 4:
        raise ValueError("Fig12 contour classification requires four ordered levels")
    array = np.asarray(values, dtype=float)
    return np.where(array >= levels[2], 0, np.where(array >= levels[1], 1, 2)).astype(int)


def _boundary_mask(classes: np.ndarray) -> np.ndarray:
    values = np.asarray(classes, dtype=int)
    boundary = np.zeros(values.shape, dtype=bool)
    boundary[:, 1:] |= values[:, 1:] != values[:, :-1]
    boundary[:, :-1] |= values[:, 1:] != values[:, :-1]
    boundary[1:, :] |= values[1:, :] != values[:-1, :]
    boundary[:-1, :] |= values[1:, :] != values[:-1, :]
    return boundary


def _boundary_f1(expected: np.ndarray, actual: np.ndarray, valid: np.ndarray) -> float:
    expected_edge = _boundary_mask(expected) & valid
    actual_edge = _boundary_mask(actual) & valid
    true_positive = int(np.count_nonzero(expected_edge & actual_edge))
    predicted = int(np.count_nonzero(actual_edge))
    relevant = int(np.count_nonzero(expected_edge))
    precision = true_positive / predicted if predicted else 0.0
    recall = true_positive / relevant if relevant else 0.0
    return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def _dilate_mask(mask: np.ndarray, radius: int) -> np.ndarray:
    values = np.asarray(mask, dtype=bool)
    radius = max(0, int(radius))
    if radius == 0:
        return values.copy()
    height, width = values.shape
    dilated = np.zeros_like(values)
    for dy in range(-radius, radius + 1):
        source_y0 = max(0, -dy)
        source_y1 = min(height, height - dy)
        target_y0 = source_y0 + dy
        target_y1 = source_y1 + dy
        for dx in range(-radius, radius + 1):
            source_x0 = max(0, -dx)
            source_x1 = min(width, width - dx)
            target_x0 = source_x0 + dx
            target_x1 = source_x1 + dx
            dilated[target_y0:target_y1, target_x0:target_x1] |= values[
                source_y0:source_y1, source_x0:source_x1
            ]
    return dilated


def _tolerant_boundary_f1(
    expected: np.ndarray,
    actual: np.ndarray,
    valid: np.ndarray,
    *,
    tolerance_px: int,
) -> float:
    expected_edge = _boundary_mask(expected) & valid
    actual_edge = _boundary_mask(actual) & valid
    predicted = int(np.count_nonzero(actual_edge))
    relevant = int(np.count_nonzero(expected_edge))
    if not predicted or not relevant:
        return 0.0
    expected_neighborhood = _dilate_mask(expected_edge, tolerance_px) & valid
    actual_neighborhood = _dilate_mask(actual_edge, tolerance_px) & valid
    precision = float(np.count_nonzero(actual_edge & expected_neighborhood)) / predicted
    recall = float(np.count_nonzero(expected_edge & actual_neighborhood)) / relevant
    return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def _source_panel_classes(
    rgb: np.ndarray,
    panel_name: str,
) -> tuple[np.ndarray, np.ndarray]:
    height, width = rgb.shape[:2]
    left_pct, top_pct, width_pct, height_pct = FIG12_SOURCE_FRAMES_PERCENT[panel_name]
    x0 = max(0, int(round(left_pct / 100.0 * width)) + 1)
    y0 = max(0, int(round(top_pct / 100.0 * height)) + 1)
    x1 = min(width, int(round((left_pct + width_pct) / 100.0 * width)) - 1)
    y1 = min(height, int(round((top_pct + height_pct) / 100.0 * height)) - 1)
    classes, valid = _classify_fig12_palette_pixels(rgb[y0 : y1 + 1, x0 : x1 + 1])
    return _fill_invalid_class_regions(classes, valid), valid


def rank_candidates(
    source_crop: Path,
    *,
    nx: int = 46,
    ny: int = 36,
    smoothing_values: list[float] | None = None,
    bias_values: list[float] | None = None,
    contrast_values: list[float] | None = None,
    boundary_tolerance_px: int = 2,
    top: int = 8,
) -> dict[str, Any]:
    smoothing_values = smoothing_values or [0.0, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.25, 1.75]
    bias_values = bias_values or [-2.5, -1.5, -0.75, 0.0, 0.75, 1.5, 2.5]
    contrast_values = contrast_values or [0.8, 0.9, 1.0, 1.1, 1.2]
    with Image.open(source_crop) as image:
        rgb = np.asarray(image.convert("RGB"), dtype=float)
    panel_definitions = {item["name"]: item for item in fig12_panels()}
    results: dict[str, list[dict[str, float]]] = {}
    for panel_name, panel in panel_definitions.items():
        expected, valid = _source_panel_classes(rgb, panel_name)
        ranked: list[dict[str, float]] = []
        for smoothing in smoothing_values:
            base = _fig12_source_matrix(
                panel_name,
                panel["levels"],
                source_crop,
                nx=nx,
                ny=ny,
                smoothing_sigma=smoothing,
            )
            for bias, contrast in itertools.product(bias_values, contrast_values):
                adjusted = _apply_matrix_bias(base, panel["levels"], bias, contrast)
                reconstructed = reconstruct_source_grid(
                    adjusted,
                    width=expected.shape[1],
                    height=expected.shape[0],
                )
                actual = classify_contour_regions(reconstructed, panel["levels"])
                accuracy = float(np.mean(actual[valid] == expected[valid]))
                boundary_f1 = _boundary_f1(expected, actual, valid)
                tolerant_boundary_f1 = _tolerant_boundary_f1(
                    expected,
                    actual,
                    valid,
                    tolerance_px=boundary_tolerance_px,
                )
                ranked.append(
                    {
                        "smoothing_sigma": float(smoothing),
                        "bias": float(bias),
                        "contrast": float(contrast),
                        "class_accuracy": accuracy,
                        "boundary_f1": boundary_f1,
                        "tolerant_boundary_f1": tolerant_boundary_f1,
                        "score": (
                            0.65 * accuracy
                            + 0.25 * tolerant_boundary_f1
                            + 0.10 * boundary_f1
                        ),
                    }
                )
        ranked.sort(key=lambda item: (item["score"], item["class_accuracy"]), reverse=True)
        results[panel_name] = ranked[: max(1, top)]
    return {
        "schema": "originplot.fig12_matrix_candidate_ranking.v1",
        "source_crop": str(source_crop.resolve()),
        "matrix_shape": [ny, nx],
        "direct_plot_rows": 3 * nx * ny,
        "boundary_tolerance_px": int(boundary_tolerance_px),
        "objective": (
            "0.65*palette_class_accuracy + 0.25*tolerant_boundary_f1 "
            "+ 0.10*exact_boundary_f1"
        ),
        "panels": results,
    }


def _parse_float_list(value: str) -> list[float]:
    return [float(item.strip()) for item in value.split(",") if item.strip()]


def main() -> int:
    parser = argparse.ArgumentParser(description="Rank Fig12 low-row native XYZ matrix candidates offline.")
    parser.add_argument("--source-crop", required=True, type=Path)
    parser.add_argument("--nx", type=int, default=46)
    parser.add_argument("--ny", type=int, default=36)
    parser.add_argument("--smoothing", type=_parse_float_list)
    parser.add_argument("--biases", type=_parse_float_list)
    parser.add_argument("--contrasts", type=_parse_float_list)
    parser.add_argument("--boundary-tolerance-px", type=int, default=2)
    parser.add_argument("--top", type=int, default=8)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = rank_candidates(
        args.source_crop,
        nx=args.nx,
        ny=args.ny,
        smoothing_values=args.smoothing,
        bias_values=args.biases,
        contrast_values=args.contrasts,
        boundary_tolerance_px=max(0, args.boundary_tolerance_px),
        top=args.top,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
