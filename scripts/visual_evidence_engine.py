from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any


def load_rgb(path: Path):
    from PIL import Image

    return Image.open(path).convert("RGB")


def crop_norm(image, bbox: list[float]):
    x1, y1, x2, y2 = bbox
    return image.crop((round(x1 * image.width), round(y1 * image.height), round(x2 * image.width), round(y2 * image.height)))


def nonwhite_mask(image, threshold: int = 245) -> set[tuple[int, int]]:
    pixels = image.load()
    pts = set()
    for y in range(image.height):
        for x in range(image.width):
            r, g, b = pixels[x, y]
            if r < threshold or g < threshold or b < threshold:
                pts.add((x, y))
    return pts


def nonwhite_bbox(image, threshold: int = 245) -> tuple[int, int, int, int] | None:
    pts = nonwhite_mask(image, threshold)
    if not pts:
        return None
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs) + 1, max(ys) + 1


def preserve_aspect_register(source, export):
    from PIL import Image

    deviations = []
    source_ratio = source.width / max(1, source.height)
    export_ratio = export.width / max(1, export.height)
    ratio_delta = abs(source_ratio - export_ratio) / max(source_ratio, 1e-9)
    if ratio_delta > 0.025:
        deviations.append({"category": "geometry", "code": "PAGE_ASPECT_RATIO_MISMATCH", "expected": source_ratio, "actual": export_ratio})
    scale = min(source.width / max(1, export.width), source.height / max(1, export.height))
    size = (max(1, round(export.width * scale)), max(1, round(export.height * scale)))
    resized = export.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", source.size, "white")
    canvas.paste(resized, ((source.width - size[0]) // 2, (source.height - size[1]) // 2))
    return canvas, deviations


def diff_metrics(source, export) -> dict[str, float]:
    sb = source.tobytes()
    eb = export.tobytes()
    total = max(1, len(sb))
    abs_sum = 0
    sq_sum = 0
    for sv, ev in zip(sb, eb):
        d = int(sv) - int(ev)
        abs_sum += abs(d)
        sq_sum += d * d
    return {"mae_0_1": abs_sum / total / 255.0, "rmse_0_1": math.sqrt(sq_sum / total) / 255.0}


def weighted_ssim(source, export) -> float:
    xs = list(source.convert("L").tobytes())
    ys = list(export.convert("L").tobytes())
    fg = nonwhite_mask(source) | nonwhite_mask(export)
    weights = []
    width = source.width
    for i in range(len(xs)):
        x = i % width
        y = i // width
        weights.append(0.8 if (x, y) in fg else 0.2)
    wsum = max(1e-9, sum(weights))
    xvals = [v / 255.0 for v in xs]
    yvals = [v / 255.0 for v in ys]
    mux = sum(w * v for w, v in zip(weights, xvals)) / wsum
    muy = sum(w * v for w, v in zip(weights, yvals)) / wsum
    vx = sum(w * (v - mux) ** 2 for w, v in zip(weights, xvals)) / wsum
    vy = sum(w * (v - muy) ** 2 for w, v in zip(weights, yvals)) / wsum
    cov = sum(w * (x - mux) * (y - muy) for w, x, y in zip(weights, xvals, yvals)) / wsum
    c1 = 0.01 ** 2
    c2 = 0.03 ** 2
    return max(0.0, min(1.0, ((2 * mux * muy + c1) * (2 * cov + c2)) / ((mux * mux + muy * muy + c1) * (vx + vy + c2))))


def edge_mask(image, threshold: int = 32) -> set[tuple[int, int]]:
    gray = image.convert("L")
    pix = gray.load()
    edges = set()
    for y in range(1, gray.height - 1):
        for x in range(1, gray.width - 1):
            if abs(int(pix[x + 1, y]) - int(pix[x - 1, y])) + abs(int(pix[x, y + 1]) - int(pix[x, y - 1])) >= threshold:
                edges.add((x, y))
    return edges


def dilate(points: set[tuple[int, int]], radius: int) -> set[tuple[int, int]]:
    out = set()
    for x, y in points:
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy <= radius * radius:
                    out.add((x + dx, y + dy))
    return out


def edge_f1(source, export, tolerance_px: int = 2) -> float:
    se = edge_mask(source)
    ee = edge_mask(export)
    if not se and not ee:
        return 1.0
    if not se or not ee:
        return 0.0
    se_d = dilate(se, tolerance_px)
    ee_d = dilate(ee, tolerance_px)
    precision = len(ee & se_d) / max(1, len(ee))
    recall = len(se & ee_d) / max(1, len(se))
    return 0.0 if precision + recall <= 0 else 2 * precision * recall / (precision + recall)


def bbox_delta(source, export) -> float:
    sb = nonwhite_bbox(source)
    eb = nonwhite_bbox(export)
    if sb is None and eb is None:
        return 0.0
    if sb is None or eb is None:
        return 1.0
    return max(abs(a - b) for a, b in zip(sb, eb)) / max(source.width, source.height, 1)


def compare_region(source, export, thresholds: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    metrics = diff_metrics(source, export)
    ssim = weighted_ssim(source, export)
    edge = edge_f1(source, export, int(thresholds.get("edge_tolerance_px", 2)))
    bbox = bbox_delta(source, export)
    score = max(0.0, min(1.0, ssim * 0.40 + edge * 0.30 + (1.0 - metrics["mae_0_1"]) * 0.20 + (1.0 - bbox) * 0.10))
    deviations = []
    if ssim < float(thresholds.get("min_ssim", 0.80)):
        deviations.append({"category": "visual", "code": "SSIM_BELOW_THRESHOLD", "expected": thresholds.get("min_ssim", 0.80), "actual": ssim})
    if edge < float(thresholds.get("min_edge_f1", 0.65)):
        deviations.append({"category": "visual", "code": "EDGE_F1_BELOW_THRESHOLD", "expected": thresholds.get("min_edge_f1", 0.65), "actual": edge})
    if metrics["mae_0_1"] > float(thresholds.get("max_mae", 0.12)):
        deviations.append({"category": "visual", "code": "MAE_ABOVE_THRESHOLD", "expected": thresholds.get("max_mae", 0.12), "actual": metrics["mae_0_1"]})
    if bbox > float(thresholds.get("max_bbox_delta", 0.02)):
        deviations.append({"category": "geometry", "code": "BBOX_DELTA_ABOVE_THRESHOLD", "expected": thresholds.get("max_bbox_delta", 0.02), "actual": bbox})
    return {"score": score, "ssim": ssim, "edge_f1": edge, "bbox_delta": bbox, **metrics}, deviations


def write_artifacts(source, registered, out_dir: Path) -> dict[str, str]:
    from PIL import Image, ImageChops, ImageDraw

    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "registered_export": out_dir / "registered_export.png",
        "absolute_diff": out_dir / "absolute_diff.png",
        "edge_overlay": out_dir / "edge_overlay.png",
        "alpha_overlay": out_dir / "alpha_overlay.png",
        "comparison_board": out_dir / "comparison_board.png",
    }
    registered.save(paths["registered_export"])
    ImageChops.difference(source, registered).save(paths["absolute_diff"])
    Image.blend(source, registered, 0.45).save(paths["alpha_overlay"])
    canvas = Image.new("RGB", source.size, "white")
    draw = ImageDraw.Draw(canvas)
    for x, y in edge_mask(source):
        draw.point((x, y), fill=(0, 150, 0))
    for x, y in edge_mask(registered):
        draw.point((x, y), fill=(210, 0, 0))
    canvas.save(paths["edge_overlay"])
    board = Image.new("RGB", (source.width * 2 + 24, source.height + 70), "white")
    bdraw = ImageDraw.Draw(board)
    bdraw.text((8, 8), "source crop", fill=(0, 0, 0))
    bdraw.text((source.width + 20, 8), "Origin post-reopen export", fill=(0, 0, 0))
    board.paste(source, (8, 38))
    board.paste(registered, (source.width + 20, 38))
    board.save(paths["comparison_board"])
    return {key: value.name for key, value in paths.items()}


def evaluate(source_path: Path, export_path: Path, out_dir: Path, thresholds: dict[str, Any] | None = None, rois: list[dict[str, Any]] | None = None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    thresholds = thresholds or {}
    rois = rois or []
    page_thresholds = thresholds.get("page") if isinstance(thresholds.get("page"), dict) else thresholds
    source = load_rgb(source_path)
    export = load_rgb(export_path)
    registered, deviations = preserve_aspect_register(source, export)
    page_metrics, page_devs = compare_region(source, registered, {**page_thresholds, "max_bbox_delta": thresholds.get("max_bbox_delta", page_thresholds.get("max_bbox_delta", 0.02))})
    deviations.extend(page_devs)
    roi_results = []
    panel_thresholds = thresholds.get("panels") if isinstance(thresholds.get("panels"), dict) else page_thresholds
    for roi in rois:
        bbox = roi.get("source_bbox_norm") or roi.get("bbox")
        if not bbox:
            continue
        sm = crop_norm(source, list(map(float, bbox)))
        em = crop_norm(registered, list(map(float, bbox)))
        metrics, roi_devs = compare_region(sm, em, panel_thresholds)
        roi_results.append({"id": roi.get("id"), "role": roi.get("role"), **metrics, "status": "pass" if not roi_devs else "failed"})
        for dev in roi_devs:
            dev["roi_id"] = roi.get("id")
        deviations.extend(roi_devs)
    artifacts = write_artifacts(source, registered, out_dir)
    visual = {
        "schema": "originplot.visual_evidence.v2",
        "status": "pass" if not deviations else "failed",
        "score": page_metrics["score"],
        **page_metrics,
        "roi_results": roi_results,
        "artifacts": artifacts,
    }
    return visual, deviations


def main() -> int:
    parser = argparse.ArgumentParser(description="Run v5.5 visual evidence comparison with ROI support.")
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--thresholds-json", type=Path)
    parser.add_argument("--rois-json", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    thresholds = json.loads(args.thresholds_json.read_text(encoding="utf-8-sig")) if args.thresholds_json else {}
    rois = json.loads(args.rois_json.read_text(encoding="utf-8-sig")) if args.rois_json else []
    visual, deviations = evaluate(args.source, args.export, args.out_dir, thresholds, rois)
    payload = {"visual": visual, "deviations": deviations}
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if visual["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
