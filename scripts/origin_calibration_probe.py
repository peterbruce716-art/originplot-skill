from __future__ import annotations

import argparse
import ctypes
import json
import subprocess
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from adapters.inspection.adapter import origin_graph_pages  # noqa: E402


PROBE_NAMES = [
    "coordinate_mapping",
    "text_metrics",
    "plot_readback",
    "graphobject_readback",
    "contour_palette",
]
GRAPHOBJECT_ELLIPSE_TYPE = 9

FIG15_NORMALIZED_PROBE_CANDIDATES = [
    {
        "candidate_id": "A_default_layer_unit",
        "layer_geometry_route": "default_layer_unit",
        "x_range": [0.0, 1.0],
        "y_range": [0.0, 1.0],
        "expected_visible_artifacts": ["one_blue_line"],
    },
    {
        "candidate_id": "B_unit1_percent_box",
        "layer_geometry_route": "layer_unit_1_percent_box",
        "left_top_width_height": [2.0, 8.0, 45.0, 78.0],
        "x_range": [0.0, 1.0],
        "y_range": [0.0, 1.0],
        "expected_visible_artifacts": ["one_blue_line"],
    },
    {
        "candidate_id": "C_set_float_percent_box_no_unit_override",
        "layer_geometry_route": "set_float_percent_box_no_unit_override",
        "left_top_width_height": [2.0, 8.0, 45.0, 78.0],
        "x_range": [0.0, 1.0],
        "y_range": [0.0, 1.0],
        "expected_visible_artifacts": ["one_blue_line"],
    },
]

FIG12_CONTOUR_PALETTE_PROBE_CANDIDATES = [
    {"candidate_id": "custom_pal", "route": "custom .pal", "matrix_values": [0, 1, 2]},
    {"candidate_id": "categorical_contour", "route": "categorical contour", "matrix_values": [0, 1, 2]},
    {"candidate_id": "level_fill_color", "route": "level fill color", "matrix_values": [0, 1, 2]},
    {"candidate_id": "controlled_color_scale", "route": "controlled color scale", "matrix_values": [0, 1, 2]},
]


def is_admin() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def planned_probe_manifest() -> dict[str, Any]:
    return {
        "schema": "originplot.origin2022_calibration_probe.v588",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "post_reopen_required": True,
        "probes": {
            "coordinate_mapping": {
                "purpose": "Measure page/layer/export coordinate scale instead of assuming source pixels equal Origin units.",
                "cases": [
                    "page_percent_rect_10x10",
                    "page_unit_rect_100x100",
                    "layer_scale_rect_0_2x0_2",
                    "layer_unit5_rect_100x100",
                ],
                "export_widths_px": [720, 850, 1440],
                "required_output_keys": [
                    "page_to_export_scale_x",
                    "page_to_export_scale_y",
                    "layer_scale_to_export_scale_x",
                    "layer_scale_to_export_scale_y",
                    "layer_unit5_to_export_scale_x",
                    "layer_unit5_to_export_scale_y",
                ],
            },
            "text_metrics": {
                "purpose": "Find a verified Origin 2022 text attach/font-size route before enabling figure labels.",
                "attach_modes": ["page", "layer_scale", "layer_frame"],
                "font_sizes_pt": [6, 8, 10, 12],
                "required_output_keys": [
                    "glyph_bbox_width_px",
                    "glyph_bbox_height_px",
                    "baseline_position_px",
                    "pre_reopen_post_reopen_delta_px",
                ],
            },
            "plot_readback": {
                "purpose": "Find the Origin 2022 API path that enumerates line, contour, and column plots after reopen.",
                "plot_families": ["one_line", "two_lines", "contour_matrix", "column"],
                "expected_post_reopen_counts": {
                    "one_line": 1,
                    "two_lines": 2,
                    "contour_matrix": 1,
                    "column": 1,
                },
                "required_output_keys": ["plot_count", "plot_type", "data_binding", "style_properties"],
            },
            "graphobject_readback": {
                "purpose": "Verify drawing object enumeration and properties after OPJU save/reopen.",
                "object_families": ["rectangle", "line", "text", "circle"],
                "expected_object_names": [
                    "probe_rect_01",
                    "probe_line_01",
                    "probe_text_01",
                    "probe_circle_01",
                ],
                "required_output_keys": ["object_count", "attach", "x1", "y1", "x2", "y2", "color", "fill", "text"],
            },
            "contour_palette": {
                "purpose": "Prove a deterministic three-color categorical contour/palette route for Fig12.",
                "matrix_values": [0, 1, 2],
                "routes": ["custom_pal", "categorical_contour", "level_fill_color", "controlled_color_scale"],
                "required_output_keys": [
                    "orange_iou",
                    "green_iou",
                    "blue_iou",
                    "purple_region_absent",
                    "default_red_region_absent",
                    "color_scale_status",
                    "post_reopen_palette_stable",
                ],
            },
        },
        "figure_specific_probe_plan": {
            "fig15_normalized_single_curve": {
                "purpose": "Find an Origin 2022 normalized 0..1 route that survives save/reopen/export before using it in Fig15.",
                "candidates": FIG15_NORMALIZED_PROBE_CANDIDATES,
                "required_gates": [
                    "post_reopen_export_nonblank",
                    "line_bbox_detected",
                    "unexpected_legend_count_zero",
                    "unexpected_axis_title_count_zero",
                ],
            },
            "fig12_three_region_palette": {
                "purpose": "Prove deterministic AA2195 orange/green/blue categorical fill and controlled colorbar before Fig12 palette claims.",
                "candidates": FIG12_CONTOUR_PALETTE_PROBE_CANDIDATES,
                "required_gates": [
                    "orange_region_iou_reported",
                    "green_region_iou_reported",
                    "blue_region_iou_reported",
                    "purple_region_absent",
                    "default_colorbar_removed_or_controlled",
                ],
            },
        },
    }


def _probe_result(name: str, *, verified: bool, status: str, **extra: Any) -> dict[str, Any]:
    payload = {"name": name, "verified": bool(verified), "status": status}
    payload.update(extra)
    return payload


def evaluate_probe_gate(name: str, evidence: dict[str, Any]) -> dict[str, Any]:
    post = evidence.get("post_reopen")
    if not isinstance(post, dict) or not post:
        return _probe_result(
            name,
            verified=False,
            status="post_reopen_evidence_missing",
            error_code="E526_POST_REOPEN_EVIDENCE_REQUIRED",
        )
    if name == "plot_readback":
        expected = planned_probe_manifest()["probes"][name]["expected_post_reopen_counts"]
        actual = {key: int((post.get(key) or {}).get("plot_count", -1)) for key in expected}
        verified = all(actual[key] == value if key in {"one_line", "two_lines"} else actual[key] >= value for key, value in expected.items())
        return _probe_result(
            name,
            verified=verified,
            status="verified" if verified else "count_mismatch",
            expected_counts=expected,
            actual_counts=actual,
            error_code=None if verified else "E400_STRUCTURE_MISMATCH",
        )
    if name == "graphobject_readback":
        expected_names = planned_probe_manifest()["probes"][name]["expected_object_names"]
        found_names = [str(item.get("name")) for item in post.get("objects", []) if isinstance(item, dict)]
        found_normalized = {item.lower() for item in found_names}
        missing = [item for item in expected_names if item.lower() not in found_normalized]
        return _probe_result(
            name,
            verified=not missing,
            status="verified" if not missing else "named_objects_missing",
            expected_object_names=expected_names,
            found_object_names=found_names,
            missing_object_names=missing,
            error_code=None if not missing else "E401_GRAPHOBJECT_READBACK_UNVERIFIED",
        )
    if name == "text_metrics":
        expected_cases = 4 * 3
        cases = post.get("cases", [])
        verified = (
            isinstance(cases, list)
            and len(cases) == expected_cases
            and all(item.get("bbox") and item.get("coordinate_delta") is not None for item in cases if isinstance(item, dict))
        )
        return _probe_result(
            name,
            verified=verified,
            status="verified" if verified else "text_cases_incomplete",
            expected_case_count=expected_cases,
            actual_case_count=len(cases) if isinstance(cases, list) else 0,
            error_code=None if verified else "E522_TEXT_METRICS_PROBE_REQUIRED",
        )
    if name == "contour_palette":
        verified = all(
            [
                float(post.get("orange_iou", 0.0)) > 0.5,
                float(post.get("green_iou", 0.0)) > 0.5,
                float(post.get("blue_iou", 0.0)) > 0.5,
                post.get("purple_region_absent") is True,
                post.get("default_red_region_absent") is True,
                post.get("post_reopen_palette_stable") is True,
                post.get("color_scale_status") in {"controlled", "removed"},
            ]
        )
        return _probe_result(
            name,
            verified=verified,
            status="verified" if verified else "palette_gate_failed",
            metrics=post,
            error_code=None if verified else "E523_CONTOUR_PALETTE_PROBE_REQUIRED",
        )
    if name == "coordinate_mapping":
        required = planned_probe_manifest()["probes"][name]["required_output_keys"]
        verified = all(post.get(key) is not None for key in required) and post.get("post_reopen") is True
        return _probe_result(
            name,
            verified=verified,
            status="verified" if verified else "coordinate_mapping_incomplete",
            measurements=post,
            error_code=None if verified else "E521_FULL_COORDINATE_PROBE_REQUIRED",
        )
    return _probe_result(name, verified=False, status="unknown_probe", error_code="E100_SCHEMA_INVALID")


def _gate_result(probe_results: list[dict[str, Any]]) -> dict[str, Any]:
    by_name = {item["name"]: bool(item.get("verified")) for item in probe_results}
    return {
        "coordinate_mapping_verified": by_name.get("coordinate_mapping", False),
        "text_metrics_verified": by_name.get("text_metrics", False),
        "plot_readback_verified": by_name.get("plot_readback", False),
        "graphobject_readback_verified": by_name.get("graphobject_readback", False),
        "contour_palette_verified": by_name.get("contour_palette", False),
        "pass_eligible": all(by_name.get(name, False) for name in PROBE_NAMES),
    }


def run_dry_probe(output: Path) -> dict[str, Any]:
    payload = planned_probe_manifest()
    probe_results = [
        _probe_result(name, verified=False, status="dry_run_not_verified", error_code="E521_LIVE_PROBE_REQUIRED")
        for name in PROBE_NAMES
    ]
    payload["mode"] = "dry_run"
    payload["status"] = "planned_not_verified"
    payload["python_is_admin"] = is_admin()
    payload["live_origin_required_for_pass"] = True
    payload["probe_results"] = probe_results
    payload["gate_result"] = _gate_result(probe_results)
    _write_json(output, payload)
    return payload


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


def add_named_ellipse(layer: Any, name: str, x1: float, y1: float, x2: float, y2: float) -> bool:
    try:
        obj = layer.obj.GraphObjects.Add(GRAPHOBJECT_ELLIPSE_TYPE)
        if obj is None:
            return False
        obj.SetName(name)
        for prop, value in {
            "attach": 2,
            "x1": float(x1),
            "y1": float(y1),
            "x2": float(x2),
            "y2": float(y2),
            "color": 0,
            "fillColor": 0,
            "transparency": 100,
        }.items():
            obj.SetNumProp(prop, value)
        return True
    except Exception:
        return False


def _add_line_page(op: Any, name: str, line_count: int) -> None:
    book = op.new_book(lname=f"{name}_data")
    sheet = book[0]
    x = [0.0, 0.25, 0.5, 0.75, 1.0]
    sheet.from_list(0, x, lname="x", axis="X")
    for index in range(line_count):
        y = [value * (index + 1) + 0.1 * index for value in x]
        sheet.from_list(index + 1, y, lname=f"y{index + 1}", axis="Y")
    page = op.new_graph(lname=name, template="LINE")
    layer = page[0]
    for index in range(line_count):
        layer.add_plot(sheet, colx=0, coly=index + 1, type="line")
    layer.rescale()


def _add_column_page(op: Any) -> None:
    book = op.new_book(lname="ColumnProbe_data")
    sheet = book[0]
    sheet.from_list(0, [1, 2, 3, 4], lname="x", axis="X")
    sheet.from_list(1, [2.0, 4.0, 3.0, 5.0], lname="y", axis="Y")
    page = op.new_graph(lname="ColumnProbe", template="COLUMN")
    page[0].add_plot(sheet, colx=0, coly=1, type="column")
    page[0].rescale()


def three_region_matrix(rows: int = 48, band_width: int = 24):
    import numpy as np

    row = np.repeat(np.array([0.0, 1.0, 2.0]), int(band_width))
    return np.tile(row, (int(rows), 1))


def apply_three_region_palette(layer: Any, colors: list[int]) -> None:
    orange, green, blue = [int(value) for value in colors]
    commands = [
        "colorbar -r;",
        "legend -r;",
        "layer.cmap.linkpal=0; layer.cmap.type=0; layer.cmap.numMinorLevels=0; layer.cmap.colorMixMode=0;",
        "layer.cmap.zMin=-0.5; layer.cmap.zMax=2.5;",
        "layer.cmap.numMajorLevels=3; layer.cmap.numColors=3;",
        "layer.cmap.setLevels(1);",
        f"layer.cmap.color1={orange}; layer.cmap.color2={green}; layer.cmap.color3={blue};",
        f"layer.cmap.colorBelow={orange}; layer.cmap.colorAbove={blue};",
        "layer.cmap.showLines(3); layer.cmap.showLabels(3);",
        "layer.cmap.updateScale();",
    ]
    for command in commands:
        layer.lt_exec(command)


def _add_contour_page(op: Any, name: str, *, three_region: bool = False) -> None:
    import numpy as np

    book = op.new_book("m", lname=f"{name}_data")
    sheet = book[0]
    values = three_region_matrix() if three_region else np.tile(np.array([0.0, 1.0, 2.0]), (18, 6))
    sheet.from_np(values)
    page = op.new_graph(lname=name, template="CONTOUR")
    plot = page[0].add_mplot(sheet, z=0, type="contour")
    if three_region:
        colors = [
            int(op.lt_int("color(247,189,114)")),
            int(op.lt_int("color(100,180,95)")),
            int(op.lt_int("color(75,130,200)")),
        ]
        apply_three_region_palette(page[0], colors)
    else:
        try:
            plot.zlevels = {"minors": 0, "levels": [0.0, 1.0, 2.0, 3.0]}
        except Exception:
            pass
    page[0].rescale()


def _add_graphobject_page(op: Any) -> None:
    page = op.new_graph(lname="GraphObjectProbe", template="LINE")
    layer = page[0]
    layer.set_xlim(0, 1)
    layer.set_ylim(0, 1)
    commands = [
        "draw -n probe_rect_01 -b; probe_rect_01.attach=2; probe_rect_01.x1=0.08; probe_rect_01.y1=0.85; probe_rect_01.x2=0.32; probe_rect_01.y2=0.60; probe_rect_01.fillColor=color(255,165,0);",
        "draw -n probe_line_01 -l; probe_line_01.attach=2; probe_line_01.x1=0.40; probe_line_01.y1=0.20; probe_line_01.x2=0.80; probe_line_01.y2=0.65;",
        "label -n probe_text_01 -a 0.12 0.42 ProbeText; probe_text_01.attach=2; probe_text_01.fsize=10;",
    ]
    for command in commands:
        layer.lt_exec(command)
    if not add_named_ellipse(layer, "probe_circle_01", 0.62, 0.62, 0.88, 0.88):
        raise RuntimeError("failed to create named ellipse GraphObject")


def _add_text_metric_pages(op: Any) -> None:
    attach_modes = {"page": 0, "layer_frame": 1, "layer_scale": 2}
    for mode, attach in attach_modes.items():
        for size in [6, 8, 10, 12]:
            page = op.new_graph(lname=f"TextMetric_{mode}_{size}pt", template="LINE")
            layer = page[0]
            layer.set_xlim(0, 1)
            layer.set_ylim(0, 1)
            label = layer.add_label(f"OriginPlot {size} pt", 0.2, 0.7)
            _set_object_name(label, f"text_{mode}_{size}pt")
            label.set_int("attach", attach)
            label.set_float("x1", 0.2)
            label.set_float("y1", 0.7)
            label.set_float("fsize", float(size))


def _add_coordinate_page(op: Any) -> None:
    page = op.new_graph(lname="CoordinateMappingProbe", template="LINE")
    layer = page[0]
    layer.set_xlim(0, 1)
    layer.set_ylim(0, 1)
    layer.lt_exec(
        "draw -n coord_page_rect -b; coord_page_rect.attach=0; coord_page_rect.x1=10; coord_page_rect.y1=10; coord_page_rect.x2=20; coord_page_rect.y2=20;"
    )
    layer.lt_exec(
        "draw -n coord_layer_rect -b; coord_layer_rect.attach=1; coord_layer_rect.x1=10; coord_layer_rect.y1=10; coord_layer_rect.x2=20; coord_layer_rect.y2=20;"
    )
    layer.lt_exec(
        "draw -n coord_scale_rect -b; coord_scale_rect.attach=2; coord_scale_rect.x1=0.2; coord_scale_rect.y1=0.8; coord_scale_rect.x2=0.4; coord_scale_rect.y2=0.6;"
    )


def _export_probe_pages(op: Any, output_dir: Path, phase: str) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    exports: dict[str, Any] = {}
    for page in origin_graph_pages(op):
        page_name = str(getattr(page, "lname", "") or getattr(page, "name", ""))
        widths = [720, 850, 1440] if page_name == "CoordinateMappingProbe" else [850]
        for width in widths:
            path = output_dir / f"{page_name}_{width}px.png"
            page.save_fig(str(path), type="png", replace=True, width=width)
            exports[f"{page_name}:{width}"] = {
                "path": str(path),
                "exists": path.exists(),
                "size_bytes": path.stat().st_size if path.exists() else 0,
                "phase": phase,
            }
    return exports


def _build_probe_project(opju: Path, pre_export_dir: Path) -> dict[str, Any]:
    import originpro as op  # type: ignore

    op.set_show(False)
    try:
        op.new(asksave=False)
        _add_coordinate_page(op)
        _add_text_metric_pages(op)
        _add_line_page(op, "PlotProbe_one_line", 1)
        _add_line_page(op, "PlotProbe_two_lines", 2)
        _add_contour_page(op, "PlotProbe_contour_matrix")
        _add_column_page(op)
        _add_graphobject_page(op)
        _add_contour_page(op, "ContourPaletteProbe", three_region=True)
        exports = _export_probe_pages(op, pre_export_dir, "pre_save")
        op.save(str(opju))
        return {
            "probe_opju": str(opju),
            "probe_opju_exists": opju.exists(),
            "probe_opju_size": opju.stat().st_size if opju.exists() else 0,
            "pre_save_exports": exports,
            "release": "op.exit()",
        }
    finally:
        op.exit()


def run_live_probe(output: Path) -> dict[str, Any]:
    payload = planned_probe_manifest()
    payload["mode"] = "live_origin_probe"
    payload["python_is_admin"] = is_admin()
    payload["artifacts"] = {}
    payload["steps"] = []
    if not payload["python_is_admin"]:
        probe_results = [
            _probe_result(name, verified=False, status="not_attempted", error_code="E120_ENVIRONMENT_MISMATCH")
            for name in PROBE_NAMES
        ]
        payload["status"] = "failed"
        payload["error_code"] = "E120_ENVIRONMENT_MISMATCH"
        payload["origin_attach_not_attempted"] = True
        payload["message"] = "Administrator Python is required before importing originpro or OriginExt."
        payload["probe_results"] = probe_results
        payload["gate_result"] = _gate_result(probe_results)
        _write_json(output, payload)
        return payload

    probe_results: list[dict[str, Any]] = []
    opju = output.with_name(output.stem + "_probe.opju").resolve()
    pre_export_dir = output.with_name(output.stem + "_pre_save").resolve()
    post_export_dir = output.with_name(output.stem + "_post_reopen").resolve()
    readback_path = output.with_name(output.stem + "_post_reopen_readback.json").resolve()
    release_status = "builder_owns_hidden_session"
    try:
        payload["steps"].append("before_import_originpro")
        _write_json(output, payload)
        payload["steps"].append("new_hidden_builder_session")
        payload["artifacts"] = _build_probe_project(opju, pre_export_dir)
        payload["steps"].append("after_import_originpro")
        payload["steps"].append("saved_probe_opju")
        release_status = "op.exit()"
        payload["steps"].append("builder_session_released")
        worker = Path(__file__).with_name("origin_calibration_inspect_worker.py")
        command = [
            sys.executable,
            str(worker),
            "--project",
            str(opju),
            "--output",
            str(readback_path),
            "--pre-export-dir",
            str(pre_export_dir),
            "--post-export-dir",
            str(post_export_dir),
        ]
        completed = subprocess.run(command, text=True, capture_output=True, timeout=180, check=False)
        payload["inspection_worker"] = {
            "command": command,
            "returncode": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:],
            "readback_path": str(readback_path),
        }
        if completed.returncode != 0 or not readback_path.exists():
            raise RuntimeError("post-reopen inspection worker failed")
        readback = json.loads(readback_path.read_text(encoding="utf-8-sig"))
        payload["steps"].append("post_reopen_readback_complete")
        payload["post_reopen_readback"] = readback
        evidence = readback.get("probe_evidence", {})
        probe_results = [evaluate_probe_gate(name, evidence.get(name, {})) for name in PROBE_NAMES]
        payload["status"] = "ok" if all(item["verified"] for item in probe_results) else "partial"
    except Exception as exc:
        payload["status"] = "failed"
        payload["error_code"] = "E521_LIVE_PROBE_FAILED"
        payload["error_class"] = exc.__class__.__name__
        payload["message"] = str(exc)
        payload["traceback"] = traceback.format_exc(limit=8)
        probe_results = [
            _probe_result(name, verified=False, status="failed", error_code="E521_LIVE_PROBE_FAILED")
            for name in PROBE_NAMES
        ]
    finally:
        payload["release"] = release_status
        payload["probe_results"] = probe_results
        payload["gate_result"] = _gate_result(probe_results)
        _write_json(output, payload)
    return payload


def probe_exit_code(payload: dict[str, Any]) -> int:
    if payload.get("mode") == "dry_run":
        return 0
    return 0 if payload.get("status") == "ok" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="OriginPlot v5.8.8 Origin 2022 calibration probe gate.")
    parser.add_argument("--output", type=Path, default=Path("outputs/originplot_v588_calibration_probe.json"))
    parser.add_argument("--live", action="store_true", help="Attempt live Origin probe execution; requires admin Python.")
    args = parser.parse_args()
    payload = run_live_probe(args.output) if args.live else run_dry_probe(args.output)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return probe_exit_code(payload)


if __name__ == "__main__":
    raise SystemExit(main())
