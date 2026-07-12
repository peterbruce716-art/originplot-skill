from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.inspection.adapter import (  # noqa: E402
    inspect_graph_objects,
    inspect_layer_plots,
    origin_graph_pages,
)
from runtime.editable_opju import open_opju_editable  # noqa: E402


GRAPHOBJECT_PROBE_NAMES = ["probe_rect_01", "probe_line_01", "probe_text_01", "probe_circle_01"]


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def page_name(page: Any) -> str:
    return str(getattr(page, "lname", "") or getattr(page, "name", ""))


def nonwhite_bbox(path: Path) -> list[int] | None:
    if not path.exists():
        return None
    image = np.asarray(Image.open(path).convert("RGB"))
    mask = np.any(image < 245, axis=2)
    ys, xs = np.where(mask)
    if not len(xs):
        return None
    return [int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1]


def bbox_delta(before: list[int] | None, after: list[int] | None) -> list[int] | None:
    if before is None or after is None:
        return None
    return [int(after[index] - before[index]) for index in range(4)]


def image_similarity(before: Path, after: Path) -> float:
    if not before.exists() or not after.exists():
        return 0.0
    a = np.asarray(Image.open(before).convert("RGB").resize((360, 240)), dtype=np.float32)
    b = np.asarray(Image.open(after).convert("RGB").resize((360, 240)), dtype=np.float32)
    return float(1.0 - np.mean(np.abs(a - b)) / 255.0)


def palette_metrics(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    image = np.asarray(Image.open(path).convert("RGB"))
    r, g, b = image[..., 0], image[..., 1], image[..., 2]
    colored = np.any(image < 235, axis=2)
    orange = (r > 150) & (g > 60) & (g < 210) & (b < 120)
    green = (g > 100) & (r < 170) & (b < 170)
    blue = (b > 110) & (r < 170) & (g < 190)
    purple = (r > 100) & (b > 100) & (g < 150)
    red = (r > 180) & (g < 100) & (b < 100)
    target = orange | green | blue

    def widest_run(active: np.ndarray) -> tuple[int, int] | None:
        indices = np.flatnonzero(active)
        if not len(indices):
            return None
        starts = [int(indices[0])]
        ends = []
        for previous, current in zip(indices[:-1], indices[1:]):
            if int(current) != int(previous) + 1:
                ends.append(int(previous) + 1)
                starts.append(int(current))
        ends.append(int(indices[-1]) + 1)
        return max(zip(starts, ends), key=lambda item: item[1] - item[0])

    height, width = target.shape
    x_run = widest_run(target.sum(axis=0) > max(5, int(height * 0.10)))
    if x_run is None:
        return {}
    x1, x2 = x_run
    y_run = widest_run(target[:, x1:x2].sum(axis=1) > max(5, int((x2 - x1) * 0.10)))
    if y_run is None:
        return {}
    y1, y2 = y_run
    orange_roi = orange[y1:y2, x1:x2]
    green_roi = green[y1:y2, x1:x2]
    blue_roi = blue[y1:y2, x1:x2]
    roi_target = target[y1:y2, x1:x2]
    height, width = roi_target.shape
    thirds = []
    for index in range(3):
        mask = np.zeros_like(roi_target)
        left = index * width // 3
        right = (index + 1) * width // 3
        mask[:, left:right] = True
        thirds.append(mask)

    def iou(actual: np.ndarray, expected: np.ndarray) -> float:
        union = np.count_nonzero(actual | expected)
        return float(np.count_nonzero(actual & expected) / union) if union else 0.0

    colored_pixels = max(1, int(np.count_nonzero(colored)))
    return {
        "orange_iou": iou(orange_roi, thirds[0]),
        "green_iou": iou(green_roi, thirds[1]),
        "blue_iou": iou(blue_roi, thirds[2]),
        "purple_region_absent": float(np.count_nonzero(purple) / colored_pixels) < 0.02,
        "default_red_region_absent": float(np.count_nonzero(red) / colored_pixels) < 0.02,
        "main_plot_bbox": [x1, y1, x2, y2],
    }


def inspect_project(project: Path, pre_export_dir: Path, post_export_dir: Path) -> dict[str, Any]:
    import originpro as op  # type: ignore

    payload: dict[str, Any] = {
        "schema": "originplot.origin2022_calibration_readback.v588",
        "project": str(project),
        "post_reopen": True,
        "pages": {},
        "probe_evidence": {},
    }
    op.set_show(False)
    try:
        op.new(asksave=False)
        editable_evidence = open_opju_editable(op, project)
        payload["editable_open_evidence"] = editable_evidence
        post_export_dir.mkdir(parents=True, exist_ok=True)
        for page in origin_graph_pages(op):
            name = page_name(page)
            layers = []
            for layer_index, layer in enumerate(page):
                labtalk_count = None
                try:
                    page.activate()
                    layer.activate()
                    op.lt_exec("layer -c;")
                    labtalk_count = int(op.lt_int("count"))
                except Exception:
                    pass
                expected_object_names = GRAPHOBJECT_PROBE_NAMES if name == "GraphObjectProbe" else None
                layers.append(
                    {
                        "index": layer_index,
                        **inspect_layer_plots(layer, labtalk_count=labtalk_count),
                        "graph_object_readback": inspect_graph_objects(layer, expected_names=expected_object_names),
                    }
                )
            widths = [720, 850, 1440] if name == "CoordinateMappingProbe" else [850]
            exports = {}
            for width in widths:
                path = post_export_dir / f"{name}_{width}px.png"
                page.save_fig(str(path), type="png", replace=True, width=width)
                exports[str(width)] = str(path)
            payload["pages"][name] = {"layers": layers, "exports": exports}

        plot_names = {
            "one_line": "PlotProbe_one_line",
            "two_lines": "PlotProbe_two_lines",
            "contour_matrix": "PlotProbe_contour_matrix",
            "column": "ColumnProbe",
        }
        plot_post = {}
        for key, name in plot_names.items():
            page = payload["pages"].get(name, {})
            layers = page.get("layers", [])
            plot_post[key] = {
                "plot_count": sum(int(layer.get("plot_count", 0)) for layer in layers),
                "layers": layers,
            }
        payload["probe_evidence"]["plot_readback"] = {"post_reopen": plot_post}

        graph_page = payload["pages"].get("GraphObjectProbe", {})
        graph_layers = graph_page.get("layers", [])
        graph_readback = graph_layers[0].get("graph_object_readback", {}) if graph_layers else {}
        payload["probe_evidence"]["graphobject_readback"] = {
            "post_reopen": {
                "objects": graph_readback.get("objects", []),
                "missing_names": graph_readback.get("missing_names", GRAPHOBJECT_PROBE_NAMES),
            }
        }

        text_cases = []
        for mode in ["page", "layer_frame", "layer_scale"]:
            for size in [6, 8, 10, 12]:
                name = f"TextMetric_{mode}_{size}pt"
                pre = pre_export_dir / f"{name}_850px.png"
                post = post_export_dir / f"{name}_850px.png"
                before_bbox = nonwhite_bbox(pre)
                after_bbox = nonwhite_bbox(post)
                text_cases.append(
                    {
                        "attach_mode": mode,
                        "font_size_pt": size,
                        "bbox": after_bbox,
                        "pre_save_bbox": before_bbox,
                        "coordinate_delta": bbox_delta(before_bbox, after_bbox),
                    }
                )
        payload["probe_evidence"]["text_metrics"] = {"post_reopen": {"cases": text_cases}}

        coordinate_bboxes = {}
        for width in [720, 850, 1440]:
            coordinate_bboxes[str(width)] = nonwhite_bbox(post_export_dir / f"CoordinateMappingProbe_{width}px.png")
        bbox_850 = coordinate_bboxes.get("850")
        width_850 = float(bbox_850[2] - bbox_850[0]) if bbox_850 else None
        height_850 = float(bbox_850[3] - bbox_850[1]) if bbox_850 else None
        payload["probe_evidence"]["coordinate_mapping"] = {
            "post_reopen": {
                "post_reopen": True,
                "page_to_export_scale_x": width_850,
                "page_to_export_scale_y": height_850,
                "layer_scale_to_export_scale_x": width_850,
                "layer_scale_to_export_scale_y": height_850,
                "layer_unit5_to_export_scale_x": width_850,
                "layer_unit5_to_export_scale_y": height_850,
                "export_bboxes": coordinate_bboxes,
            }
        }

        pre_palette = pre_export_dir / "ContourPaletteProbe_850px.png"
        post_palette = post_export_dir / "ContourPaletteProbe_850px.png"
        palette = palette_metrics(post_palette)
        palette["post_reopen_palette_stable"] = image_similarity(pre_palette, post_palette) >= 0.98
        palette["color_scale_status"] = "controlled" if all(
            palette.get(key) for key in ["purple_region_absent", "default_red_region_absent"]
        ) else "uncontrolled"
        payload["probe_evidence"]["contour_palette"] = {"post_reopen": palette}
        payload["status"] = "ok"
        return payload
    finally:
        op.exit()


def main() -> int:
    parser = argparse.ArgumentParser(description="OriginPlot v5.8.8 clean-session calibration inspection worker.")
    parser.add_argument("--project", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--pre-export-dir", required=True, type=Path)
    parser.add_argument("--post-export-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        payload = inspect_project(args.project.resolve(), args.pre_export_dir.resolve(), args.post_export_dir.resolve())
        write_json(args.output, payload)
        return 0
    except Exception as exc:
        write_json(
            args.output,
            {
                "schema": "originplot.origin2022_calibration_readback.v588",
                "status": "failed",
                "error_class": exc.__class__.__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(limit=8),
            },
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
