from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.visual_qa import score_visual
    from scripts.materialize_live_evidence import materialize_standard_evidence
    from scripts.acceptance_hardening import (
        derive_release_status,
        evaluate_target_visual_gate,
        normalize_fig12_parameters,
        render_parameter_fingerprint,
    )
    from scripts.fig12_roi import evaluate_fig12_rois
except ImportError:
    from visual_qa import score_visual
    from materialize_live_evidence import materialize_standard_evidence
    from acceptance_hardening import derive_release_status, evaluate_target_visual_gate, normalize_fig12_parameters, render_parameter_fingerprint
    from fig12_roi import evaluate_fig12_rois


REQUIRED_LIVE_ARTIFACTS = [
    "candidate.opju",
    "candidate_export.png",
    "candidate_readback.json",
    "candidate_visual_metrics.json",
    "candidate_manifest.json",
]

SKILL_ROOT = Path(__file__).resolve().parents[1]
AA2195_BUILDER_PACKAGE = SKILL_ROOT / "builders" / "aa2195"

VISUAL_THRESHOLDS = {
    "fig12": {"mae_max": 0.15, "layout_min": 0.60, "demo_cyan_ratio_max": 0.0005},
    "fig15": {"mae_max": 0.08, "layout_min": 0.85, "demo_cyan_ratio_max": 0.0005},
    "fig16": {"mae_max": 0.15, "layout_min": 0.85, "demo_cyan_ratio_max": 0.0005},
}

FIG15_FROZEN_BASELINE_THRESHOLDS = {
    "mae_0_1_max": 0.040,
    "ssim_score_min": 0.810,
    "layout_score_min": 0.985,
    "color_score_min": 0.925,
    "registration_abs_dx_px_max": 4.0,
    "registration_abs_dy_px_max": 2.0,
    "demo_cyan_ratio_max": 0.0005,
}
GEOMETRY_TABLE_VERSIONS = {"fig12": "aa2195_fig12_loggrid_5000_text_lines_v14", "fig15": "aa2195_fig15_run047_v1", "fig16": "aa2195_fig16_run052_v1"}
TEMPLATE_IDS = {"fig12": ["GID499", "GID459", "GID27"], "fig15": ["GID1609", "GID27"], "fig16": ["GID399", "GID1652"]}
FIG15_FROZEN_EFFECTIVE_ROUTE = {
    "route": "worksheet_backed_source_calibrated_two_layer",
    "reproduction_mode": "reconstructed_approximate",
    "canvas_size": [850, 335],
    "page_size_inches": [8.5, 3.35],
    "expected_plot_count": 10,
    "expected_plot_count_by_layer": {"0": 5, "1": 5},
    "expected_graphobject_count": 29,
}
FIG15_SOURCE_CROP_SHA256 = "a0d3c0f0e106af6353579fa176524cb552ec22deb5107c33383cbf4aea9e63a0"


def is_admin() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def read_candidate(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("candidate JSON must be an object")
    return payload


def candidate_sha256(candidate: dict[str, Any]) -> str:
    stable = {key: value for key, value in candidate.items() if key not in {"candidate_sha256", "sha256"}}
    return hashlib.sha256(json.dumps(stable, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


def make_run_id(figure: str, candidate: dict[str, Any]) -> str:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"p13-{figure}-{candidate_sha256(candidate)[:12]}-{timestamp}"


def export_path_by_phase(exports: list[dict[str, Any]], phase: str) -> Path:
    matches = [Path(item.get("path", "")) for item in exports if item.get("phase") == phase]
    return matches[0] if len(matches) == 1 else Path()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_manifest(
    *,
    figure: str,
    candidate: dict[str, Any],
    output_dir: Path,
    mode: str,
    status: str,
    error_code: str | None = None,
    message: str | None = None,
) -> dict[str, Any]:
    sha = candidate_sha256(candidate)
    manifest: dict[str, Any] = {
        "schema": "originplot.clean_rebuild_candidate_worker.v5.8.9-p13",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "figure": figure,
        "mode": mode,
        "status": status,
        "candidate": candidate,
        "candidate_sha256": sha,
        "candidate_sha256_matches_input": candidate.get("candidate_sha256") in {None, sha},
        "output_dir": str(output_dir),
        "required_live_artifacts": REQUIRED_LIVE_ARTIFACTS,
        "python_is_admin": is_admin(),
        "pass_eligible": False,
        "build_origin_figure_required": True,
        "same_run_candidate_promotion_policy": "hard_gates_before_visual_metrics",
    }
    if error_code:
        manifest["error_code"] = error_code
    if message:
        manifest["message"] = message
    return manifest


def run_dry(figure: str, candidate_path: Path, output_dir: Path) -> dict[str, Any]:
    candidate = read_candidate(candidate_path)
    manifest = build_manifest(
        figure=figure,
        candidate=candidate,
        output_dir=output_dir,
        mode="dry_run",
        status="planned_not_executed",
        error_code="E524_LIVE_CANDIDATE_WORKER_REQUIRED",
        message="Dry-run validates candidate shape/SHA and required real build route only; it does not build OPJU or export PNG.",
    )
    write_json(output_dir / "candidate_manifest.json", manifest)
    return manifest


def _load_aa2195_builder() -> Any:
    if not (AA2195_BUILDER_PACKAGE / "__init__.py").exists():
        raise RuntimeError(f"packaged AA2195 builder is missing: {AA2195_BUILDER_PACKAGE}")
    if str(SKILL_ROOT) not in sys.path:
        sys.path.insert(0, str(SKILL_ROOT))
    from builders import aa2195

    return aa2195


def _copy_if_exists(src: Path, dst: Path) -> dict[str, Any]:
    record = {"source": str(src), "target": str(dst), "copied": False}
    if src and src.exists() and src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        record.update({"copied": True, "size_bytes": dst.stat().st_size})
    return record


def _resolve_source_crop(
    candidate: dict[str, Any],
    candidate_path: Path | None = None,
) -> Path | None:
    raw = str(candidate.get("source_crop", "")).strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path
    candidate_dir = candidate_path.resolve().parent if candidate_path else None
    project_root = candidate.get("project_root")
    bases: list[Path] = []
    if project_root:
        project_path = Path(project_root)
        if project_path.is_absolute():
            bases.append(project_path)
        elif candidate_dir:
            bases.append(candidate_dir / project_path)
        bases.append(Path.cwd() / project_path)
    if candidate_dir:
        bases.append(candidate_dir)
    bases.extend([Path.cwd(), SKILL_ROOT, SKILL_ROOT.parent])
    for base in bases:
        resolved = (base / path).resolve()
        if resolved.exists():
            return resolved
    return (Path.cwd() / path).resolve()


def _effective_builder_route(fig_result: dict[str, Any]) -> dict[str, Any]:
    route = fig_result.get("builder_route") if isinstance(fig_result, dict) else {}
    if not isinstance(route, dict):
        return {}
    keys = [
        "route",
        "reproduction_mode",
        "canvas_size",
        "page_size_inches",
        "expected_plot_count",
        "expected_plot_count_by_layer",
        "expected_graphobject_count",
        "panel_inventory",
        "colorbar_inventory",
        "fig12_colorbar_offsets",
        "fig12_label_sizes",
        "fig12_matrix_biases",
        "fig12_matrix_contrasts",
        "fig12_matrix_resolution_scale",
        "fig12_matrix_smoothing_sigma",
        "fig12_matrix_mode",
        "fig12_y_minor_ticks",
        "fig12_panel_layout_offsets",
        "fig12_levels_reapplied_after_palette",
        "fig12_contour_line_style_reapplied_after_levels",
        "fig12_origin_label_size_scales",
        "fig12_axis_tick_fsize",
        "fig12_axis_title_fsize",
        "fig12_axis_title_text",
        "fig12_contour_line_color",
        "fig12_contour_line_width",
        "fig16_tuning",
        "fig16_colors",
        "fig16_text_sizes",
        "fig16_column_gap_percent",
        "fig16_group_frame_width",
        "candidate_params",
    ]
    effective = {key: route[key] for key in keys if key in route}
    label_sizes = route.get("fig12_label_sizes") if isinstance(route.get("fig12_label_sizes"), dict) else {}
    if label_sizes:
        effective["fig12_contour_label_size_offset"] = round(float(label_sizes.get("contour", 8.4)) - 8.4, 6)
        effective["fig12_mechanism_label_size_offset"] = round(float(label_sizes.get("mechanism", 11.2)) - 11.2, 6)
    return effective


def _prepare_candidate_for_build(figure: str, candidate: dict[str, Any]) -> dict[str, Any]:
    if figure != "fig12":
        return {"candidate": dict(candidate), "parameter_normalization": None}
    strict = bool(candidate.get("strict_parameter_validation", True))
    normalization = normalize_fig12_parameters(candidate, strict=strict)
    effective = normalization["effective_parameters"]
    prepared = dict(candidate)
    for name in (
        "fig12_matrix_resolution_scale", "fig12_matrix_smoothing_sigma", "fig12_matrix_mode",
        "fig12_y_minor_ticks", "fig12_panel_layout_offsets", "fig12_matrix_biases",
        "fig12_label_sizes",
    ):
        prepared[name] = effective[name]
    prepared["fig12_label_size_offsets"] = {
        "contour": effective["fig12_contour_label_size_offset"],
        "mechanism": effective["fig12_mechanism_label_size_offset"],
    }
    return {"candidate": prepared, "parameter_normalization": normalization}


def _render_identity_payload(figure: str, route: dict[str, Any], source_crop_sha256: str) -> dict[str, Any]:
    effective = {key: value for key, value in route.items() if key != "candidate_params"}
    return {
        "effective_parameters": effective,
        "effective_builder_route": effective,
        "data_digest": GEOMETRY_TABLE_VERSIONS[figure],
        "geometry_table_version": GEOMETRY_TABLE_VERSIONS[figure],
        "source_crop_sha256": source_crop_sha256.lower(),
        "origin_version": "Origin 2022",
        "export_profile": {"canvas_size": effective.get("canvas_size"), "page_size_inches": effective.get("page_size_inches")},
        "template_ids": TEMPLATE_IDS[figure],
        "font_profile": "origin_2022_default_serif",
        "feature_flags": {"speed_mode": False, "editable_reopen": True},
    }


def _source_sha256(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fig15_frozen_fingerprint() -> str:
    payload = _render_identity_payload("fig15", FIG15_FROZEN_EFFECTIVE_ROUTE, FIG15_SOURCE_CROP_SHA256)
    return render_parameter_fingerprint(payload)["fingerprint"]


def evaluate_visual_metrics(
    *,
    figure: str,
    candidate: dict[str, Any],
    png: Path,
    opju: Path,
    output_dir: Path,
    hard_gate_status: dict[str, Any],
    origin_export_qa: list[Any],
    source_crop: Path | None = None,
) -> dict[str, Any]:
    source_crop = source_crop or _resolve_source_crop(candidate)
    metrics: dict[str, Any] = {
        "schema": "originplot.clean_candidate_visual_metrics.v589",
        "candidate_sha256": candidate_sha256(candidate),
        "candidate_export_exists": png.exists(),
        "candidate_export_size": png.stat().st_size if png.exists() else 0,
        "candidate_opju_exists": opju.exists(),
        "candidate_opju_size": opju.stat().st_size if opju.exists() else 0,
        "source_crop": str(source_crop) if source_crop else None,
        "source_crop_exists": bool(source_crop and source_crop.exists()),
        "origin_export_qa": origin_export_qa,
        "hard_gate_status": hard_gate_status,
        "blocking_reasons": [],
        "pass_eligible": False,
    }
    if not png.exists() or not source_crop or not source_crop.exists():
        metrics["blocking_reasons"] = [
            "candidate_export_missing" if not png.exists() else "source_crop_missing"
        ]
        return metrics

    visual = score_visual(
        source_crop,
        png,
        comparison_dir=output_dir / "visual_evidence",
        thresholds=VISUAL_THRESHOLDS[figure],
    )
    visual.pop("schema", None)
    metrics.update(visual)
    blocking = list(metrics.get("blocking_reasons", []))
    if hard_gate_status.get("status") != "pass":
        blocking.append("origin_structure_hard_gate_failed")
    metrics["blocking_reasons"] = list(dict.fromkeys(blocking))
    metrics["pass_eligible"] = not metrics["blocking_reasons"]
    return metrics


def run_live(figure: str, candidate_path: Path, output_dir: Path) -> dict[str, Any]:
    candidate = read_candidate(candidate_path)
    resolved_source_crop = _resolve_source_crop(candidate, candidate_path)
    if not is_admin():
        manifest = build_manifest(
            figure=figure,
            candidate=candidate,
            output_dir=output_dir,
            mode="live",
            status="failed",
            error_code="E120_ENVIRONMENT_MISMATCH",
            message="Administrator Python is required before importing originpro or attaching to Origin.",
        )
        manifest["origin_attach_not_attempted"] = True
        write_json(output_dir / "candidate_manifest.json", manifest)
        return manifest

    manifest = build_manifest(
        figure=figure,
        candidate=candidate,
        output_dir=output_dir,
        mode="live",
        status="started",
    )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        prepared = _prepare_candidate_for_build(figure, candidate)
        build_candidate = prepared["candidate"]
        if figure == "fig12" and resolved_source_crop is not None:
            build_candidate["_runtime_source_crop"] = str(resolved_source_crop)
        manifest["parameter_normalization"] = prepared["parameter_normalization"]
        builder = _load_aa2195_builder()
        build_result = builder.build_origin_figure(
            figure_id=figure,
            candidate_params=build_candidate,
            output_dir=output_dir,
            attach_existing_authorized=True,
        )
        if not isinstance(build_result, dict) or build_result.get("status") == "failed":
            failure = build_result if isinstance(build_result, dict) else {}
            manifest.update(
                {
                    "status": "failed",
                    "error_code": failure.get("error_code", "E525_CANDIDATE_WORKER_FAILED"),
                    "message": failure.get("message", "The packaged Origin builder failed before producing a candidate."),
                    "builder_result_status": failure.get("status", "invalid_result"),
                    "origin_attach_not_attempted": bool(failure.get("origin_attach_not_attempted", False)),
                    "opju_generation_allowed": bool(failure.get("opju_generation_allowed", False)),
                    "pass_eligible": False,
                    "builder_failure": failure,
                }
            )
            write_json(
                output_dir / "candidate_readback.json",
                {
                    "schema": "originplot.clean_candidate_readback.v588",
                    "figure": figure,
                    "candidate_sha256": candidate_sha256(candidate),
                    "builder_status": failure.get("status", "invalid_result"),
                    "builder_failure": failure,
                    "origin_object_readback": {},
                    "origin_object_readback_validation": {},
                },
            )
            write_json(
                output_dir / "candidate_visual_metrics.json",
                {
                    "schema": "originplot.clean_candidate_visual_metrics.v589",
                    "candidate_sha256": candidate_sha256(candidate),
                    "candidate_export_exists": False,
                    "candidate_opju_exists": False,
                    "blocking_reasons": ["origin_builder_failed"],
                    "pass_eligible": False,
                },
            )
            return manifest
        fig_result = build_result.get("per_figure", {}).get(figure, {}) if isinstance(build_result, dict) else {}
        opju = output_dir / "candidate.opju"
        png = output_dir / "candidate_export.png"
        readback_path = output_dir / "candidate_readback.json"
        metrics_path = output_dir / "candidate_visual_metrics.json"
        source_opju = Path(fig_result.get("opju_path", "")) if fig_result.get("opju_path") else Path()
        if source_opju and not source_opju.is_absolute():
            source_opju = SKILL_ROOT / source_opju
        exports = fig_result.get("origin_rendered_exports", []) if isinstance(fig_result, dict) else []
        source_pre_png = export_path_by_phase(exports, "pre_save")
        source_png = export_path_by_phase(exports, "post_reopen")
        if source_pre_png and not source_pre_png.is_absolute():
            source_pre_png = SKILL_ROOT / source_pre_png
        if source_png and not source_png.is_absolute():
            source_png = SKILL_ROOT / source_png
        copy_records = {
            "opju": _copy_if_exists(source_opju, opju),
            "png": _copy_if_exists(source_png, png),
        }
        source_crop = resolved_source_crop
        readback = {
            "schema": "originplot.clean_candidate_readback.v588",
            "figure": figure,
            "candidate_sha256": candidate_sha256(candidate),
            "builder_status": build_result.get("status") if isinstance(build_result, dict) else "missing",
            "figure_status": fig_result.get("status"),
            "effective_builder_route": _effective_builder_route(fig_result),
            "editable_view_evidence": fig_result.get("editable_view_evidence", {}),
            "origin_object_readback": fig_result.get("origin_object_readback", {}),
            "origin_object_readback_validation": fig_result.get("origin_object_readback_validation", {}),
            "copy_records": copy_records,
        }
        metrics = evaluate_visual_metrics(
            figure=figure,
            candidate=candidate,
            png=png,
            opju=opju,
            output_dir=output_dir,
            hard_gate_status=fig_result.get("origin_candidate_hard_gate", {}),
            origin_export_qa=fig_result.get("origin_export_qa", []),
            source_crop=source_crop,
        )
        effective_route = readback.get("effective_builder_route", {})
        source_hash = _source_sha256(source_crop)
        render_identity = render_parameter_fingerprint(
            _render_identity_payload(figure, effective_route, source_hash)
        )
        frozen_recognized = figure == "fig15" and render_identity["fingerprint"] == _fig15_frozen_fingerprint()
        target_visual_gate = evaluate_target_visual_gate(
            figure, metrics, frozen_identity_recognized=frozen_recognized
        )
        structure_pass = fig_result.get("origin_candidate_hard_gate", {}).get("status") == "pass"
        runtime_ready = bool(opju.exists() and png.exists() and fig_result.get("status") == "post_reopen_built")
        release_status = derive_release_status(
            runtime_ready,
            structure_pass,
            target_visual_gate["visual_baseline_status"],
        )
        metrics["render_identity"] = render_identity
        metrics["target_visual_gate"] = target_visual_gate
        metrics["release_status"] = release_status
        metrics["fig15_frozen_identity_recognized"] = frozen_recognized if figure == "fig15" else None
        if figure == "fig15":
            metrics["fig15_status"] = "frozen_regression_baseline" if frozen_recognized and target_visual_gate["visual_baseline_promoted"] else "frozen_regression_baseline_failed"
        if figure == "fig12":
            metrics["fig12_roi_metrics"] = evaluate_fig12_rois(
                source_crop, png, output_dir / "visual_evidence" / "fig12_roi_overlay_debug.png"
            )
        metrics["pass_eligible"] = release_status["pass_eligible"]
        if not release_status["pass_eligible"]:
            metrics["blocking_reasons"] = list(dict.fromkeys(list(metrics.get("blocking_reasons", [])) + target_visual_gate["failures"] + ["p13_overall_release_pass_false"]))
        readback["parameter_normalization"] = prepared.get("parameter_normalization")
        readback["render_identity"] = render_identity
        readback["target_visual_gate"] = target_visual_gate
        readback["release_status"] = release_status
        write_json(output_dir / "candidate_readback.json", readback)
        write_json(output_dir / "candidate_visual_metrics.json", metrics)
        standard_evidence = materialize_standard_evidence(
            output_dir=output_dir / "evidence",
            run_id=make_run_id(figure, candidate),
            figure_id=figure,
            skill_version="5.8.9-p13",
            source_crop=source_crop if source_crop is not None else Path(),
            opju=opju,
            pre_save=source_pre_png,
            post_reopen=png,
            inspection=readback,
            visual_metrics=metrics,
            route=readback.get("effective_builder_route", {}),
        )
        manifest.update(
            {
                "status": (
                    "built_real_candidate_pass_eligible"
                    if metrics.get("pass_eligible")
                    else "built_real_candidate_not_promoted"
                ),
                "candidate_export": str(png),
                "candidate_opju": str(opju),
                "candidate_readback": str(output_dir / "candidate_readback.json"),
                "candidate_visual_metrics": str(output_dir / "candidate_visual_metrics.json"),
                "pass_eligible": bool(metrics.get("pass_eligible")),
                "release_status": metrics.get("release_status"),
                "render_identity": metrics.get("render_identity"),
                "target_visual_gate": metrics.get("target_visual_gate"),
                "parameter_normalization": prepared.get("parameter_normalization"),
                "fig15_status": metrics.get("fig15_status"),
                "fig15_frozen_baseline": metrics.get("fig15_frozen_baseline"),
                "effective_builder_route": readback.get("effective_builder_route"),
                "standard_evidence_dir": "evidence",
                "standard_evidence": standard_evidence,
                "builder_result_status": build_result.get("status") if isinstance(build_result, dict) else "missing",
                "figure_result_status": fig_result.get("status"),
                "reason": (
                    "Candidate passed reopen, structure, canvas, watermark, and visual thresholds."
                    if metrics.get("pass_eligible")
                    else "Candidate remains gated by reopen, structure, canvas, watermark, or visual thresholds."
                ),
            }
        )
    except Exception as exc:
        manifest.update(
            {
                "status": "failed",
                "error_code": "E525_CANDIDATE_WORKER_FAILED",
                "error_class": exc.__class__.__name__,
                "message": str(exc),
                "traceback": traceback.format_exc(limit=8),
            }
        )
    finally:
        manifest["release"] = manifest.get("release") or "builder_owned_session_released"
        write_json(output_dir / "candidate_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="OriginPlot v5.8.8 clean rebuild candidate worker.")
    parser.add_argument("--figure", required=True, choices=["fig12", "fig15", "fig16"])
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    manifest = run_live(args.figure, args.candidate, args.output_dir) if args.live else run_dry(
        args.figure, args.candidate, args.output_dir
    )
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest.get("mode") == "dry_run" or manifest.get("status") in {
        "built_real_candidate_not_promoted",
        "built_real_candidate_pass_eligible",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
