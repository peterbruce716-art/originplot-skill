from __future__ import annotations

import argparse
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
from builders.aa2195.geometry import _fig12_source_matrix, fig12_panels
from scripts.rank_fig12_matrix_candidates import (
    _boundary_f1,
    _source_panel_classes,
    _tolerant_boundary_f1,
    classify_contour_regions,
    reconstruct_source_grid,
)


TRANSFORMS = {
    "identity": lambda values: values,
    "flip_x": np.fliplr,
    "flip_y": np.flipud,
    "flip_xy": lambda values: np.flipud(np.fliplr(values)),
}


def _panel_value(mapping: Any, name: str, default: float) -> float:
    if not isinstance(mapping, dict):
        return float(default)
    aliases = {"PSC": ("PSC", "a", "0"), "UC": ("UC", "b", "1"), "TR": ("TR", "c", "2")}
    for key in aliases[name]:
        if key in mapping:
            return float(mapping[key])
    return float(default)


def _area_fractions(classes: np.ndarray, valid: np.ndarray) -> list[float]:
    denominator = max(1, int(np.count_nonzero(valid)))
    return [float(np.count_nonzero((classes == index) & valid) / denominator) for index in range(3)]


def contour_level_hypotheses(
    published_levels: list[float],
    matrix: np.ndarray,
) -> dict[str, list[float]]:
    if len(published_levels) != 4:
        raise ValueError("Fig12 contour calibration requires four published levels")

    def thirds(low: float, high: float) -> list[float]:
        step = (high - low) / 3.0
        return [low, low + step, low + 2.0 * step, high]

    values = np.asarray(matrix, dtype=float)
    return {
        "published_nonuniform": [float(value) for value in published_levels],
        "equal_published_range": thirds(float(published_levels[0]), float(published_levels[-1])),
        "equal_data_range": thirds(float(np.nanmin(values)), float(np.nanmax(values))),
    }


def compare_panel_response(
    predicted: np.ndarray,
    actual: np.ndarray,
    valid: np.ndarray,
    *,
    boundary_tolerance_px: int = 2,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    actual_fractions = _area_fractions(actual, valid)
    for name, transform in TRANSFORMS.items():
        transformed = transform(np.asarray(predicted, dtype=int))
        predicted_fractions = _area_fractions(transformed, valid)
        records.append(
            {
                "transform": name,
                "class_accuracy": float(np.mean(transformed[valid] == actual[valid])),
                "boundary_f1": _boundary_f1(actual, transformed, valid),
                "tolerant_boundary_f1": _tolerant_boundary_f1(
                    actual,
                    transformed,
                    valid,
                    tolerance_px=boundary_tolerance_px,
                ),
                "predicted_area_fractions": predicted_fractions,
                "actual_area_fractions": actual_fractions,
                "area_fraction_l1": float(
                    np.abs(np.asarray(predicted_fractions) - np.asarray(actual_fractions)).sum()
                ),
            }
        )
    records.sort(
        key=lambda item: (
            item["class_accuracy"],
            item["tolerant_boundary_f1"],
            -item["area_fraction_l1"],
        ),
        reverse=True,
    )
    return records


def calibrate_origin_export(
    candidate_path: Path,
    origin_export: Path,
    *,
    nx: int,
    ny: int,
    boundary_tolerance_px: int = 2,
) -> dict[str, Any]:
    candidate = json.loads(candidate_path.read_text(encoding="utf-8-sig"))
    source_crop = Path(candidate["source_crop"])
    smoothing = float(candidate.get("fig12_matrix_smoothing_sigma", 0.0))
    biases = candidate.get("fig12_matrix_biases", {})
    contrasts = candidate.get("fig12_matrix_contrasts", {})
    with Image.open(origin_export) as image:
        actual_rgb = np.asarray(image.convert("RGB"), dtype=float)

    panels: dict[str, Any] = {}
    for panel in fig12_panels():
        name = panel["name"]
        matrix = _fig12_source_matrix(
            name,
            panel["levels"],
            source_crop,
            nx=nx,
            ny=ny,
            smoothing_sigma=smoothing,
        )
        adjusted = _apply_matrix_bias(
            matrix,
            panel["levels"],
            _panel_value(biases, name, 0.0),
            _panel_value(contrasts, name, 1.0),
        )
        actual_classes, actual_valid = _source_panel_classes(actual_rgb, name)
        reconstructed = reconstruct_source_grid(
            adjusted,
            width=actual_classes.shape[1],
            height=actual_classes.shape[0],
        )
        hypothesis_records = []
        for hypothesis, levels in contour_level_hypotheses(panel["levels"], adjusted).items():
            predicted_classes = classify_contour_regions(reconstructed, levels)
            comparisons = compare_panel_response(
                predicted_classes,
                actual_classes,
                actual_valid,
                boundary_tolerance_px=boundary_tolerance_px,
            )
            hypothesis_records.append(
                {
                    "hypothesis": hypothesis,
                    "levels": levels,
                    "best_comparison": comparisons[0],
                    "comparisons": comparisons,
                }
            )
        hypothesis_records.sort(
            key=lambda item: (
                item["best_comparison"]["class_accuracy"],
                item["best_comparison"]["tolerant_boundary_f1"],
                -item["best_comparison"]["area_fraction_l1"],
            ),
            reverse=True,
        )
        panels[name] = {
            "best_hypothesis": hypothesis_records[0]["hypothesis"],
            "best_transform": hypothesis_records[0]["best_comparison"]["transform"],
            "hypotheses": hypothesis_records,
        }

    return {
        "schema": "originplot.fig12_origin_response_calibration.v1",
        "candidate": str(candidate_path.resolve()),
        "origin_export": str(origin_export.resolve()),
        "matrix_shape": [ny, nx],
        "boundary_tolerance_px": int(boundary_tolerance_px),
        "interpretation": "diagnostic_historical_export_only_not_promotion_evidence",
        "panels": panels,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare a Fig12 candidate's offline matrix response with an existing Origin export."
    )
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--origin-export", required=True, type=Path)
    parser.add_argument("--nx", required=True, type=int)
    parser.add_argument("--ny", required=True, type=int)
    parser.add_argument("--boundary-tolerance-px", type=int, default=2)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = calibrate_origin_export(
        args.candidate,
        args.origin_export,
        nx=max(2, args.nx),
        ny=max(2, args.ny),
        boundary_tolerance_px=max(0, args.boundary_tolerance_px),
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
