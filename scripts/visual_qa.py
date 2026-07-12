from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image
from skimage.metrics import structural_similarity


def _content_bbox(array: np.ndarray) -> list[int] | None:
    mask = np.any(array < 245, axis=2)
    if not np.any(mask):
        return None
    ys, xs = np.where(mask)
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def _pad_white(array: np.ndarray, width: int, height: int) -> np.ndarray:
    result = np.full((height, width, 3), 255, dtype=np.uint8)
    result[: array.shape[0], : array.shape[1]] = array
    return result


def _edge_mask(array: np.ndarray) -> np.ndarray:
    gray = np.mean(array.astype(np.float32) / 255.0, axis=2)
    gx = np.abs(np.diff(gray, axis=1, prepend=gray[:, :1]))
    gy = np.abs(np.diff(gray, axis=0, prepend=gray[:1, :]))
    return np.clip(gx + gy, 0.0, 1.0)


def _layout_score(source_bbox: list[int] | None, actual_bbox: list[int] | None, width: int, height: int) -> float:
    if source_bbox is None and actual_bbox is None:
        return 1.0
    if source_bbox is None or actual_bbox is None:
        return 0.0
    scale = np.array([width, height, width, height], dtype=np.float64)
    error = float(np.mean(np.abs(np.asarray(source_bbox) - np.asarray(actual_bbox)) / scale))
    return max(0.0, 1.0 - 4.0 * error)


def _registration_shift(source_bbox: list[int] | None, actual_bbox: list[int] | None) -> dict[str, float]:
    if source_bbox is None or actual_bbox is None:
        return {"dx_px": 0.0, "dy_px": 0.0}
    source_center = ((source_bbox[0] + source_bbox[2]) / 2.0, (source_bbox[1] + source_bbox[3]) / 2.0)
    actual_center = ((actual_bbox[0] + actual_bbox[2]) / 2.0, (actual_bbox[1] + actual_bbox[3]) / 2.0)
    return {
        "dx_px": float(actual_center[0] - source_center[0]),
        "dy_px": float(actual_center[1] - source_center[1]),
    }


def _save_comparisons(source: np.ndarray, actual: np.ndarray, comparison_dir: Path) -> dict[str, str]:
    comparison_dir.mkdir(parents=True, exist_ok=True)
    src = source.astype(np.float32) / 255.0
    act = actual.astype(np.float32) / 255.0
    diff = np.abs(src - act)
    overlay = 0.5 * src + 0.5 * act
    edge_diff = np.abs(_edge_mask(source) - _edge_mask(actual))
    outputs = {
        "source_common": comparison_dir / "source_common.png",
        "render_common": comparison_dir / "render_common.png",
        "difference": comparison_dir / "difference.png",
        "overlay_50": comparison_dir / "overlay_50.png",
        "edge_difference": comparison_dir / "edge_difference.png",
    }
    Image.fromarray(source).save(outputs["source_common"])
    Image.fromarray(actual).save(outputs["render_common"])
    Image.fromarray(np.uint8(np.clip(diff * 255.0, 0, 255))).save(outputs["difference"])
    Image.fromarray(np.uint8(np.clip(overlay * 255.0, 0, 255))).save(outputs["overlay_50"])
    Image.fromarray(np.uint8(np.clip(edge_diff * 255.0, 0, 255))).save(outputs["edge_difference"])
    return {key: str(path) for key, path in outputs.items()}


def score_visual(
    source_path: Path,
    actual_path: Path,
    *,
    comparison_dir: Path,
    thresholds: dict[str, float] | None = None,
) -> dict[str, Any]:
    source_image = Image.open(source_path).convert("RGB")
    actual_image = Image.open(actual_path).convert("RGB")
    source_array = np.asarray(source_image, dtype=np.uint8)
    actual_array = np.asarray(actual_image, dtype=np.uint8)
    width = max(source_image.width, actual_image.width)
    height = max(source_image.height, actual_image.height)
    source = _pad_white(source_array, width, height)
    actual = _pad_white(actual_array, width, height)

    src = source.astype(np.float32) / 255.0
    act = actual.astype(np.float32) / 255.0
    difference = src - act
    source_bbox = _content_bbox(source)
    actual_bbox = _content_bbox(actual)
    source_edge = _edge_mask(source)
    actual_edge = _edge_mask(actual)
    edge_mae = float(np.mean(np.abs(source_edge - actual_edge)))
    source_nonwhite = float(np.mean(np.any(source < 245, axis=2)))
    actual_nonwhite = float(np.mean(np.any(actual < 245, axis=2)))
    cyan_mask = (
        (actual_array[:, :, 0] < 100)
        & (actual_array[:, :, 1] > 180)
        & (actual_array[:, :, 2] > 200)
        & (np.abs(actual_array[:, :, 1].astype(np.int16) - actual_array[:, :, 2].astype(np.int16)) < 70)
    )
    demo_cyan_ratio = float(np.mean(cyan_mask))
    canvas_match = source_image.size == actual_image.size
    layout = _layout_score(source_bbox, actual_bbox, width, height)
    color_delta = float(np.mean(np.abs(np.mean(src, axis=(0, 1)) - np.mean(act, axis=(0, 1)))))
    ssim = float(structural_similarity(src, act, channel_axis=2, data_range=1.0))
    configured = thresholds or {}
    blocking_reasons: list[str] = []
    error_codes: list[str] = []
    if not canvas_match:
        blocking_reasons.append("canvas_size_mismatch")
    if demo_cyan_ratio > float(configured.get("demo_cyan_ratio_max", 0.0005)):
        blocking_reasons.append("demo_cyan_markings")
        error_codes.append("E122_ORIGIN_DEMO_EXPORT_BLOCKED")
    mae = float(np.mean(np.abs(difference)))
    if "mae_max" in configured and mae > float(configured["mae_max"]):
        blocking_reasons.append("mae_above_threshold")
    if "layout_min" in configured and layout < float(configured["layout_min"]):
        blocking_reasons.append("layout_below_threshold")

    return {
        "schema": "originplot.visual_qa.v589",
        "source": str(source_path),
        "actual": str(actual_path),
        "source_width": source_image.width,
        "source_height": source_image.height,
        "actual_width": actual_image.width,
        "actual_height": actual_image.height,
        "canvas_size_match": canvas_match,
        "mae_0_1": mae,
        "rmse_0_1": float(np.sqrt(np.mean(difference * difference))),
        "ssim_score": ssim,
        "layout_score": layout,
        "edge_score": max(0.0, 1.0 - 5.0 * edge_mae),
        "edge_mae_0_1": edge_mae,
        "color_score": max(0.0, 1.0 - 10.0 * color_delta),
        "color_mean_delta_0_1": color_delta,
        "source_content_bbox": source_bbox,
        "actual_content_bbox": actual_bbox,
        "registration_shift": _registration_shift(source_bbox, actual_bbox),
        "source_nonwhite_ratio": source_nonwhite,
        "actual_nonwhite_ratio": actual_nonwhite,
        "nonwhite_delta": abs(source_nonwhite - actual_nonwhite),
        "demo_cyan_ratio": demo_cyan_ratio,
        "environment_blocked": "E122_ORIGIN_DEMO_EXPORT_BLOCKED" in error_codes,
        "error_codes": error_codes,
        "blocking_reasons": blocking_reasons,
        "pass_eligible": not blocking_reasons,
        "comparison_outputs": _save_comparisons(source, actual, comparison_dir),
        "note": "source image is not resized; unequal canvases are white-padded and blocked",
    }
