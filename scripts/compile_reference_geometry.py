from __future__ import annotations

import argparse
import copy
import json
import math
from pathlib import Path
from typing import Any


def load_document(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise SystemExit("PyYAML is required for YAML FigureSpec files") from exc
        data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("FigureSpec root must be an object")
    return data


def _as_bbox(value: Any, label: str) -> tuple[float, float, float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise ValueError(f"{label} must be [left, top, right, bottom]")
    left, top, right, bottom = (float(v) for v in value)
    if not right > left or not bottom > top:
        raise ValueError(f"{label} must have positive width and height")
    return left, top, right, bottom


def _pairs(values: Any, label: str) -> list[tuple[float, float]]:
    if not isinstance(values, (list, tuple)) or len(values) < 2 or len(values) % 2:
        raise ValueError(f"{label} must contain an even number of numeric values")
    flat = [float(v) for v in values]
    return list(zip(flat[0::2], flat[1::2]))


def _flatten(points: list[tuple[float, float]]) -> list[float]:
    return [value for point in points for value in point]


def _normalized_point(x: float, y: float, bbox: tuple[float, float, float, float]) -> tuple[float, float]:
    left, top, right, bottom = bbox
    return (x - left) / (right - left), (bottom - y) / (bottom - top)


def _axis_value(pixel: float, start_px: float, end_px: float, limits: list[float], scale: str) -> float:
    if len(limits) < 2:
        raise ValueError("axis limits must contain at least [from, to]")
    begin, end = float(limits[0]), float(limits[1])
    if end_px == start_px:
        raise ValueError("axis pixel span cannot be zero")
    t = (pixel - start_px) / (end_px - start_px)
    scale_key = str(scale or "linear").lower()
    if scale_key in {"linear", "categorical", "category"}:
        return begin + t * (end - begin)
    if scale_key in {"log", "log10"}:
        if begin <= 0 or end <= 0:
            raise ValueError("log10 axis limits must be positive")
        return 10 ** (math.log10(begin) + t * (math.log10(end) - math.log10(begin)))
    if scale_key == "ln":
        if begin <= 0 or end <= 0:
            raise ValueError("ln axis limits must be positive")
        return math.exp(math.log(begin) + t * (math.log(end) - math.log(begin)))
    if scale_key == "log2":
        if begin <= 0 or end <= 0:
            raise ValueError("log2 axis limits must be positive")
        return 2 ** (math.log2(begin) + t * (math.log2(end) - math.log2(begin)))
    raise ValueError(f"unsupported axis scale for source geometry mapping: {scale!r}")


def _find_layer(spec: dict[str, Any], layer_id: str) -> dict[str, Any]:
    for layer in spec.get("layers", []):
        if isinstance(layer, dict) and layer.get("id") == layer_id:
            return layer
    raise ValueError(f"unknown layer for source geometry: {layer_id!r}")


def compile_source_geometry(spec: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compile annotation source-pixel coordinates into explicit Origin coordinates.

    Canonical source pixels use a top-left origin. Canonical normalized Origin coordinates
    use a bottom-left origin. Layer-scale conversion uses the panel's plot_bbox_px and
    final axis limits; therefore this compilation must happen before Origin execution and
    after final axis limits are known.
    """

    compiled = copy.deepcopy(spec)
    source_annotations = [ann for ann in compiled.get("annotations", []) if isinstance(ann, dict) and ann.get("source_geometry")]
    if not source_annotations:
        metadata = {
            "status": "skipped",
            "reason": "no source_geometry annotations",
            "compiled_annotation_count": 0,
            "mappings": [],
        }
        compiled.setdefault("_compiled", {})["reference_geometry"] = metadata
        return compiled, metadata
    reference = compiled.get("reference_geometry") or {}
    page_bbox = _as_bbox(reference.get("page_bbox_px") or [0, 0, *(reference.get("size_px") or [0, 0])], "reference_geometry.page_bbox_px")
    page = compiled.get("page") or {}
    page_size = page.get("size_mm") or []
    panels = reference.get("panels") or {}
    diagnostics: list[dict[str, Any]] = []

    for ann in compiled.get("annotations", []):
        if not isinstance(ann, dict) or not ann.get("source_geometry"):
            continue
        source_geometry = ann["source_geometry"]
        if source_geometry.get("coordinate_space") != "source_px":
            raise ValueError(f"annotation {ann.get('id')!r} source_geometry.coordinate_space must be source_px")
        points = _pairs(source_geometry.get("coordinates_px"), f"annotation {ann.get('id')!r} source coordinates")
        obj = ann.get("origin_object")
        if not isinstance(obj, dict):
            raise ValueError(f"annotation {ann.get('id')!r} requires origin_object")
        attach = obj.get("attach_to")
        units = obj.get("position_units")
        layer_id = ann.get("layer")

        if attach == "page":
            normalized = [_normalized_point(x, y, page_bbox) for x, y in points]
            if units == "page_normalized":
                result = normalized
            elif units == "mm":
                if not isinstance(page_size, (list, tuple)) or len(page_size) != 2:
                    raise ValueError("page.size_mm is required for page/mm coordinate compilation")
                result = [(nx * float(page_size[0]), ny * float(page_size[1])) for nx, ny in normalized]
            else:
                raise ValueError(f"page attachment requires page_normalized or mm, got {units!r}")
            basis = {"bbox_px": list(page_bbox)}
        elif attach == "layer_frame":
            panel = panels.get(layer_id) or {}
            frame_bbox = _as_bbox(panel.get("frame_bbox_px"), f"reference_geometry.panels.{layer_id}.frame_bbox_px")
            if units != "layer_normalized":
                raise ValueError("layer_frame source compilation currently requires layer_normalized units")
            result = [_normalized_point(x, y, frame_bbox) for x, y in points]
            basis = {"bbox_px": list(frame_bbox)}
        elif attach == "layer_scales":
            if units != "scale":
                raise ValueError("layer_scales source compilation requires scale units")
            panel = panels.get(layer_id) or {}
            plot_bbox = _as_bbox(panel.get("plot_bbox_px"), f"reference_geometry.panels.{layer_id}.plot_bbox_px")
            layer = _find_layer(compiled, str(layer_id))
            x_axis = layer.get("x") or {}
            y_axis = layer.get("y") or {}
            x_limits = x_axis.get("limits")
            y_limits = y_axis.get("limits")
            if not isinstance(x_limits, list) or not isinstance(y_limits, list):
                raise ValueError(f"layer {layer_id!r} requires fixed numeric x/y limits for source mapping")
            left, top, right, bottom = plot_bbox
            result = [
                (
                    _axis_value(x, left, right, x_limits, str(x_axis.get("scale", "linear"))),
                    _axis_value(y, bottom, top, y_limits, str(y_axis.get("scale", "linear"))),
                )
                for x, y in points
            ]
            basis = {"plot_bbox_px": list(plot_bbox), "x_limits": x_limits[:2], "y_limits": y_limits[:2]}
        else:
            raise ValueError(f"unsupported attachment for source compilation: {attach!r}")

        obj["coordinates"] = _flatten(result)
        obj["compiled_from_source_px"] = True
        diagnostics.append(
            {
                "annotation_id": ann.get("id"),
                "object_name": obj.get("name"),
                "attach_to": attach,
                "position_units": units,
                "source_coordinates_px": source_geometry.get("coordinates_px"),
                "compiled_coordinates": obj["coordinates"],
                "basis": basis,
            }
        )

    metadata = {
        "status": "ok",
        "compiled_annotation_count": len(diagnostics),
        "coordinate_convention": {
            "source_px": "top_left_origin",
            "page_normalized": "bottom_left_origin",
            "layer_normalized": "bottom_left_origin",
        },
        "mappings": diagnostics,
    }
    compiled.setdefault("_compiled", {})["reference_geometry"] = metadata
    return compiled, metadata


def dump_document(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix.lower() == ".json":
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return
    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise SystemExit("PyYAML is required to write YAML FigureSpec files") from exc
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile source-pixel geometry into explicit Origin coordinates.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--diagnostics", type=Path)
    args = parser.parse_args()
    try:
        compiled, diagnostics = compile_source_geometry(load_document(args.spec))
    except Exception as exc:
        payload = {"status": "fail", "error_class": exc.__class__.__name__, "message": str(exc)}
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 2
    dump_document(args.out, compiled)
    if args.diagnostics:
        args.diagnostics.parent.mkdir(parents=True, exist_ok=True)
        args.diagnostics.write_text(json.dumps(diagnostics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(diagnostics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
