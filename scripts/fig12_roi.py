from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw


FIG12_ROIS = {
    "schema": "originplot.fig12_roi_definition.v2",
    "coordinate_system": "canonical_source_crop_pixels_805x590",
    "registration": "global_content_bbox_translation_reported_not_applied_to_hide_layout_error",
    "regions": [
        {"name": "PSC_plot", "bbox": [98, 53, 323, 270], "kind": "plot"},
        {"name": "PSC_colorbar", "bbox": [329, 62, 388, 205], "kind": "colorbar"},
        {"name": "UC_plot", "bbox": [488, 53, 715, 270], "kind": "plot"},
        {"name": "UC_colorbar", "bbox": [716, 62, 775, 205], "kind": "colorbar"},
        {"name": "TR_plot", "bbox": [284, 321, 510, 546], "kind": "plot"},
        {"name": "TR_colorbar", "bbox": [516, 338, 575, 489], "kind": "colorbar"},
        {
            "name": "axis_titles", "kind": "text",
            "boxes": [
                [135, 276, 287, 318], [35, 92, 72, 238],
                [524, 276, 680, 318], [424, 92, 461, 238],
                [322, 548, 480, 590], [220, 365, 260, 526],
            ],
        },
        {
            "name": "mechanism_labels", "kind": "text",
            "boxes": [
                [147, 137, 207, 181], [221, 195, 315, 241], [224, 57, 292, 105],
                [536, 137, 596, 181], [611, 195, 705, 241], [619, 57, 687, 105],
                [294, 337, 354, 389], [331, 414, 427, 469], [436, 473, 509, 530],
            ],
        },
        {
            "name": "contour_labels", "kind": "text",
            "boxes": [
                [98, 84, 133, 105], [124, 62, 166, 83], [225, 59, 269, 80],
                [174, 103, 219, 123], [211, 190, 255, 211], [235, 232, 276, 252],
                [487, 61, 526, 81], [526, 94, 570, 115], [559, 75, 604, 95],
                [609, 70, 653, 91], [630, 109, 676, 130], [674, 247, 715, 268],
                [352, 352, 398, 375], [371, 407, 418, 432], [439, 456, 486, 480],
            ],
        },
    ],
}

PALETTE = np.asarray([(252, 191, 110), (177, 223, 137), (198, 223, 236)], dtype=float)


def _mask(array: np.ndarray, kind: str = "layout") -> np.ndarray:
    if kind == "text":
        return np.max(array, axis=2) < 165
    return np.any(array < 245, axis=2)


def _bbox(mask: np.ndarray) -> list[int] | None:
    if not np.any(mask):
        return None
    y, x = np.where(mask)
    return [int(x.min()), int(y.min()), int(x.max()) + 1, int(y.max()) + 1]


def _edge(mask: np.ndarray) -> np.ndarray:
    return np.logical_or(np.diff(mask, axis=0, prepend=mask[:1]), np.diff(mask, axis=1, prepend=mask[:, :1]))


def _dilate(mask: np.ndarray, radius: int = 2) -> np.ndarray:
    padded = np.pad(mask, radius, mode="constant")
    result = np.zeros_like(mask)
    height, width = mask.shape
    for dy in range(2 * radius + 1):
        for dx in range(2 * radius + 1):
            result |= padded[dy:dy + height, dx:dx + width]
    return result


def _boundary_f1(source_edge: np.ndarray, actual_edge: np.ndarray, tolerance: int = 2) -> float:
    if not source_edge.any() and not actual_edge.any():
        return 1.0
    if not source_edge.any() or not actual_edge.any():
        return 0.0
    precision = float(np.logical_and(actual_edge, _dilate(source_edge, tolerance)).sum() / actual_edge.sum())
    recall = float(np.logical_and(source_edge, _dilate(actual_edge, tolerance)).sum() / source_edge.sum())
    return 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0


def _directed_chamfer(first: np.ndarray, second: np.ndarray) -> float:
    first_points = np.argwhere(first)
    second_points = np.argwhere(second)
    if not len(first_points) and not len(second_points):
        return 0.0
    if not len(first_points) or not len(second_points):
        return 999.0
    minima: list[np.ndarray] = []
    for start in range(0, len(first_points), 256):
        delta = first_points[start:start + 256, None, :] - second_points[None, :, :]
        minima.append(np.sqrt(np.square(delta).sum(axis=2)).min(axis=1))
    return float(np.concatenate(minima).mean())


def _palette_metrics(source: np.ndarray, actual: np.ndarray) -> dict[str, Any]:
    source_distance = np.linalg.norm(source[..., None, :].astype(float) - PALETTE, axis=-1)
    actual_distance = np.linalg.norm(actual[..., None, :].astype(float) - PALETTE, axis=-1)
    source_class = source_distance.argmin(axis=-1)
    actual_class = actual_distance.argmin(axis=-1)
    source_valid = source_distance.min(axis=-1) <= 30.0
    actual_valid = actual_distance.min(axis=-1) <= 30.0
    records = []
    for index, name in enumerate(("orange", "green", "blue")):
        sm = source_valid & (source_class == index)
        am = actual_valid & (actual_class == index)
        union = np.logical_or(sm, am).sum()
        records.append({
            "region": name,
            "iou": float(np.logical_and(sm, am).sum() / union) if union else 1.0,
            "area_ratio": float(am.sum() / sm.sum()) if sm.any() else (1.0 if not am.any() else 999.0),
        })
    return {
        "color_region_iou": float(np.mean([item["iou"] for item in records])),
        "region_area_ratio": float(actual_valid.sum() / source_valid.sum()) if source_valid.any() else 1.0,
        "color_regions": records,
    }


def _metrics(source: np.ndarray, actual: np.ndarray, *, kind: str = "layout") -> dict[str, Any]:
    sm, am = _mask(source, kind), _mask(actual, kind)
    sb, ab = _bbox(sm), _bbox(am)
    if sb and ab:
        sc = ((sb[0] + sb[2]) / 2, (sb[1] + sb[3]) / 2)
        ac = ((ab[0] + ab[2]) / 2, (ab[1] + ab[3]) / 2)
        center = float(np.hypot(ac[0] - sc[0], ac[1] - sc[1]))
        width_error = float((ab[2] - ab[0]) - (sb[2] - sb[0]))
        height_error = float((ab[3] - ab[1]) - (sb[3] - sb[1]))
    else:
        center, width_error, height_error = 999.0, 999.0, 999.0
    se, ae = _edge(sm), _edge(am)
    union = np.logical_or(se, ae).sum()
    alignment = float(np.logical_and(se, ae).sum() / union) if union else 1.0
    content_union = np.logical_or(sm, am).sum()
    chamfer = (_directed_chamfer(se, ae) + _directed_chamfer(ae, se)) / 2.0
    return {
        "source_bbox": sb,
        "actual_bbox": ab,
        "bbox_center_error_px": center,
        "bbox_width_error_px": width_error,
        "bbox_height_error_px": height_error,
        "source_content_occupancy": float(sm.mean()),
        "actual_content_occupancy": float(am.mean()),
        "edge_alignment": alignment,
        "boundary_f1": _boundary_f1(se, ae),
        "chamfer_distance_px": chamfer,
        "content_iou": float(np.logical_and(sm, am).sum() / content_union) if content_union else 1.0,
        "source_nonwhite_ratio": float(sm.mean()),
        "actual_nonwhite_ratio": float(am.mean()),
        "edge_density_delta": float(abs(se.mean() - ae.mean())),
        "collision_overlap": float(np.logical_and(sm, am).mean()),
        "out_of_bounds": False,
        **_palette_metrics(source, actual),
    }


def _aggregate_metrics(
    source: np.ndarray,
    actual: np.ndarray,
    boxes: list[list[int]],
    *,
    kind: str,
) -> dict[str, Any]:
    components = []
    weights = []
    for bbox in boxes:
        x0, y0, x1, y1 = bbox
        components.append({
            "bbox": bbox,
            "metrics": _metrics(source[y0:y1, x0:x1], actual[y0:y1, x0:x1], kind=kind),
        })
        weights.append((x1 - x0) * (y1 - y0))
    numeric_keys = (
        "bbox_center_error_px", "bbox_width_error_px", "bbox_height_error_px",
        "source_content_occupancy", "actual_content_occupancy", "edge_alignment",
        "boundary_f1", "chamfer_distance_px", "content_iou", "edge_density_delta",
        "collision_overlap", "color_region_iou", "region_area_ratio",
    )
    aggregate = {
        key: float(np.average([item["metrics"][key] for item in components], weights=weights))
        for key in numeric_keys
    }
    aggregate.update({"source_bbox": None, "actual_bbox": None, "out_of_bounds": False, "components": components})
    return aggregate


def evaluate_fig12_rois(source_path: Path, actual_path: Path, overlay_path: Path) -> dict[str, Any]:
    source_image = Image.open(source_path).convert("RGB")
    actual_image = Image.open(actual_path).convert("RGB")
    if source_image.size != (805, 590) or actual_image.size != source_image.size:
        raise ValueError("Fig12 ROI evaluation requires matching 805x590 canonical crops")
    source, actual = np.asarray(source_image), np.asarray(actual_image)
    overlay = actual_image.copy()
    draw = ImageDraw.Draw(overlay)
    records = []
    for region in FIG12_ROIS["regions"]:
        boxes = region.get("boxes", [region.get("bbox")])
        if not boxes or any(box is None for box in boxes):
            raise ValueError(f"Fig12 ROI {region['name']} has no measurable boxes")
        if any(not (0 <= box[0] < box[2] <= 805 and 0 <= box[1] < box[3] <= 590) for box in boxes):
            raise ValueError(f"Fig12 ROI {region['name']} is outside the canonical crop")
        if len(boxes) == 1:
            x0, y0, x1, y1 = boxes[0]
            metrics = _metrics(source[y0:y1, x0:x1], actual[y0:y1, x0:x1], kind=region["kind"])
        else:
            metrics = _aggregate_metrics(source, actual, boxes, kind=region["kind"])
        records.append({**region, "status": "measured", "metrics": metrics})
        for bbox in boxes:
            draw.rectangle(bbox, outline=(255, 0, 0), width=1)
    Path(overlay_path).parent.mkdir(parents=True, exist_ok=True)
    overlay.save(overlay_path)
    return {
        "schema": "originplot.fig12_roi_metrics.v1",
        "roi_definition": FIG12_ROIS,
        "registration_shift": {"dx_px": 0.0, "dy_px": 0.0, "applied": False},
        "regions": records,
        "overlay_debug_only": Path(overlay_path).name,
        "deferred_metrics": [],
    }
