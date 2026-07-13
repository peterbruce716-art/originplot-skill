from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import shutil
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

_IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPORT_ROOT))

from builders.registry import UnknownBuilderError, resolve_builder

AUTHORIZED_SOURCE_PLACEHOLDER = "AUTHORIZED_LOCAL_SOURCE_REQUIRED"

try:
    from scripts.visual_qa import score_visual
    from scripts.assert_admin_preflight import demo_restart_directive
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
    from assert_admin_preflight import demo_restart_directive
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
SKILL_VERSION = "5.8.9-p18"

VISUAL_THRESHOLDS = {
    "fig3": {"mae_max": 0.12, "layout_min": 0.85, "demo_cyan_ratio_max": 0.0005},
    "fig12": {"mae_max": 0.15, "layout_min": 0.60, "demo_cyan_ratio_max": 0.0005},
    "fig14": {"mae_max": 0.10, "layout_min": 0.90, "demo_cyan_ratio_max": 0.0005},
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
GEOMETRY_TABLE_VERSIONS = {"fig3": "aa2195_fig3_continuous_native_line_styles_v2", "fig12": "aa2195_fig12_loggrid_threshold_centered_v22", "fig14": "aa2195_fig14_component_errorbars_native_scatter_dash_v4", "fig15": "aa2195_fig15_run047_v1", "fig16": "aa2195_fig16_segment_boundary_calibrated_v7"}
TEMPLATE_IDS = {"fig3": ["GID27"], "fig12": ["GID499", "GID459", "GID27"], "fig14": ["GID1609", "GID27"], "fig15": ["GID1609", "GID27"], "fig16": ["GID399", "GID1652"]}
OFFICIAL_RESEARCH_URLS = {
    "https://www.originlab.com/www/products/GraphGallery.aspx?s=0&sort=Newest",
    "https://docs.originlab.com/zh/",
    "https://www.originlab.com/videos/index.aspx?CID=11",
    "https://docs.originlab.com/quick-help/graphing/zh/",
}
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
FIG16_FROZEN_EFFECTIVE_ROUTE = {
    "route": "gid399_stackcolumn_213_with_plot_derived_legend",
    "reproduction_mode": "reconstructed_approximate",
    "canvas_size": [720, 375],
    "page_size_inches": [7.2, 3.75],
    "expected_plot_count": 5,
    "expected_plot_count_by_layer": {"0": 3, "1": 2},
    "expected_graphobject_count": 22,
    "fig16_tuning": {
        "legend_dx": 0.0, "legend_dy": 6.0, "stage_text_dx": 0.0, "stage_text_dy": 0.0,
        "stage_circle_dx": 0.0, "stage_circle_dy": 0.0, "bar_top_dy": -1.0,
        "bar_bottom_dy": 1.0, "header_dx": 0.0, "header_dy": 0.0,
        "relation_text_dx": 0.0, "relation_text_dy": 0.0,
        "group_label_dx": 0.0, "group_label_dy": 0.0,
    },
    "fig16_colors": {"WH": "#ff9830", "DRV": "#00ff98", "DRX": "#d098ff"},
    "fig16_text_sizes": {"header": 10.0, "legend": 9.5, "group_label": 12.0, "stage": 9.0, "relation": 10.0},
    "fig16_column_gap_percent": 15.0,
    "fig16_group_frame_width": 0.5,
    "fig16_background_color": "#fefefe",
}
FIG16_SOURCE_CROP_SHA256 = "e2f127bf873aea613a73e878fa5ace6f458840ed64d4b5931cfb1f177dab6ede"


class TemplateSearchError(ValueError):
    pass


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


def stable_runtime_error_code(exc: BaseException) -> str:
    matched = re.match(r"^(E\d{3}_[A-Z0-9_]+)", str(exc))
    return matched.group(1) if matched else "E525_CANDIDATE_WORKER_FAILED"


def require_template_search_record(
    figure: str,
    candidate: dict[str, Any],
    candidate_path: Path,
) -> dict[str, Any] | None:
    if figure not in TEMPLATE_IDS:
        return None
    raw_path = str(candidate.get("template_search_record", "")).strip()
    if not raw_path:
        raise TemplateSearchError(
            "paper-like Origin reconstruction requires a template_search_record before construction"
        )
    path = Path(raw_path)
    if not path.is_absolute():
        path = (candidate_path.resolve().parent / path).resolve()
    if not path.is_file():
        raise TemplateSearchError(f"template_search_record is missing: {raw_path}")
    raw_bytes = path.read_bytes()
    try:
        record = json.loads(raw_bytes.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise TemplateSearchError("template_search_record is not valid UTF-8 JSON") from exc
    if not isinstance(record, dict) or record.get("schema") != "originplot.template_search_record.v1":
        raise TemplateSearchError("template_search_record has an unsupported schema")
    if record.get("status") != "ok":
        raise TemplateSearchError("template_search_record status must be ok")

    source_rows = record.get("official_sources")
    if not isinstance(source_rows, list):
        raise TemplateSearchError("template_search_record official_sources must be a list")
    checked_urls = {
        str(item.get("url"))
        for item in source_rows
        if isinstance(item, dict)
        and item.get("reachable") is True
        and item.get("status_code") == 200
    }
    if not OFFICIAL_RESEARCH_URLS.issubset(checked_urls):
        raise TemplateSearchError("template_search_record must verify all four official Origin entrances")

    local_search = record.get("local_search")
    if not isinstance(local_search, dict) or not all(
        local_search.get(key) is True
        for key in ("workspace_catalog_checked", "installed_templates_checked")
    ):
        raise TemplateSearchError("template_search_record must include both local template searches")
    inspection = record.get("inspection")
    if not isinstance(inspection, dict) or not all(
        inspection.get(key) is True
        for key in ("administrator_python", "visible_origin", "editable_open_verified")
    ):
        raise TemplateSearchError("template_search_record lacks administrator editable-open inspection")
    if inspection.get("release") != "op.detach()":
        raise TemplateSearchError("template_search_record must record op.detach() release")

    templates = record.get("templates")
    if not isinstance(templates, dict):
        raise TemplateSearchError("template_search_record templates must be an object")
    sha_pattern = re.compile(r"^[0-9a-f]{64}$")
    for template_id in TEMPLATE_IDS[figure]:
        item = templates.get(template_id)
        if not isinstance(item, dict):
            raise TemplateSearchError(f"template_search_record is missing {template_id} for {figure}")
        required_truth = (
            item.get("compatible_open") is True
            and item.get("opened_editable") is True
            and isinstance(item.get("worksheet_rows_total"), int)
            and item["worksheet_rows_total"] > 0
            and isinstance(item.get("plot_types"), list)
            and bool(item.get("plot_types"))
            and isinstance(item.get("direct_bindings_count"), int)
            and item["direct_bindings_count"] > 0
            and item.get("decision") in {"selected_reference", "rejected_after_inspection"}
            and bool(str(item.get("selection_reason", "")).strip())
            and figure in item.get("figures", [])
        )
        hashes_valid = all(
            sha_pattern.fullmatch(str(item.get(key, "")))
            for key in ("project_sha256", "archive_sha256")
        )
        if not required_truth or not hashes_valid:
            raise TemplateSearchError(f"template_search_record has incomplete evidence for {template_id}")

    return {
        "status": "pass",
        "schema": record["schema"],
        "record_sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "record_path": raw_path.replace("\\", "/"),
        "figures": sorted(str(key) for key in record.get("figures", {})),
        "template_ids": TEMPLATE_IDS[figure],
        "official_sources_verified": len(OFFICIAL_RESEARCH_URLS),
        "local_search_verified": True,
        "administrator_editable_open_verified": True,
    }


def make_run_id(figure: str, candidate: dict[str, Any]) -> str:
    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    return f"p18-{figure}-{candidate_sha256(candidate)[:12]}-{timestamp}"


def export_path_by_phase(exports: list[dict[str, Any]], phase: str) -> Path:
    matches = [Path(item.get("path", "")) for item in exports if item.get("phase") == phase]
    return matches[0] if len(matches) == 1 else Path()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # COM readback can expose callable proxy attributes; evidence must remain serializable.
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def build_manifest(
    *,
    figure: str,
    candidate: dict[str, Any],
    output_dir: Path,
    mode: str,
    status: str,
    error_code: str | None = None,
    message: str | None = None,
    builder_id: str | None = None,
) -> dict[str, Any]:
    sha = candidate_sha256(candidate)
    manifest: dict[str, Any] = {
        "schema": "originplot.clean_rebuild_candidate_worker.v5.8.9-p18",
        "skill_version": SKILL_VERSION,
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
        "command_success": status == "planned_not_executed",
        "structure_pass": False,
        "visual_pass": False,
        "live_origin_verified": False,
        "overall_status": "planned_not_executed" if status == "planned_not_executed" else "incomplete",
        "builder_id": builder_id or figure,
        "build_origin_figure_required": True,
        "same_run_candidate_promotion_policy": "hard_gates_before_visual_metrics",
    }
    if error_code:
        manifest["error_code"] = error_code
    if message:
        manifest["message"] = message
    return manifest


def _read_figure_spec(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError("figure spec JSON must be an object")
    return payload


def run_dry(
    figure: str | None,
    candidate_path: Path,
    output_dir: Path,
    *,
    builder_id: str | None = None,
    figure_spec_path: Path | None = None,
) -> dict[str, Any]:
    candidate = read_candidate(candidate_path)
    definition = resolve_builder(builder_id=builder_id, figure=figure)
    figure_spec = _read_figure_spec(figure_spec_path)
    plan = definition.validate_plan(candidate, figure_spec)
    effective_figure = figure or str(plan.get("figure") or candidate.get("figure") or definition.builder_id)
    template_search_gate = require_template_search_record(effective_figure, candidate, candidate_path)
    manifest = build_manifest(
        figure=effective_figure,
        candidate=candidate,
        output_dir=output_dir,
        mode="dry_run",
        status="planned_not_executed",
        error_code="E524_LIVE_CANDIDATE_WORKER_REQUIRED",
        message="Dry-run validates candidate shape/SHA and required real build route only; it does not build OPJU or export PNG.",
        builder_id=definition.builder_id,
    )
    manifest.update(
        {
            "plan": plan,
            "figure_spec": str(figure_spec_path) if figure_spec_path else None,
            "command_success": True,
            "overall_status": "planned_not_executed",
            "template_search_gate": template_search_gate,
        }
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


def _resolve_candidate_file(
    candidate: dict[str, Any],
    key: str,
    candidate_path: Path,
) -> Path | None:
    raw = str(candidate.get(key, "")).strip()
    if not raw:
        return None
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (candidate_path.resolve().parent / path).resolve()


def _stable_digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _validate_source_data_gate(
    figure: str,
    candidate: dict[str, Any],
    candidate_path: Path,
    source_crop: Path | None,
) -> dict[str, Any]:
    policy = str(candidate.get("source_data_policy", "")).strip()
    if not policy and candidate.get("fresh_source_required") is True:
        policy = "fresh_extract"
    if policy not in {"fresh_extract", "validated_reuse", "validated_crop_reextract"}:
        raise ValueError(
            "source_data_policy must be fresh_extract, validated_reuse, or validated_crop_reextract"
        )
    manifest_path = _resolve_candidate_file(candidate, "source_data_manifest", candidate_path)
    if manifest_path is None:
        raise ValueError("source_data_manifest is mandatory")
    if source_crop is None or not source_crop.is_file() or not manifest_path.is_file():
        raise ValueError("source crop or data manifest is missing")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != "originplot.aa2195_fresh_source_bundle.v1":
        raise ValueError("source data manifest schema is invalid")
    record = payload.get("figures", {}).get(figure)
    if not isinstance(record, dict) or not isinstance(record.get("data"), dict):
        raise ValueError(f"source data for {figure} is missing")
    crop_sha256 = _source_sha256(source_crop)
    if crop_sha256 != str(record.get("source_crop_sha256", "")).lower():
        raise ValueError(f"source crop hash mismatch for {figure}")
    data_sha256 = _stable_digest(record["data"])
    if data_sha256 != str(record.get("data_sha256", "")).lower():
        raise ValueError(f"source data hash mismatch for {figure}")

    gate = {
        "status": "pass",
        "policy": policy,
        "schema": payload["schema"],
        "manifest_path": str(manifest_path),
        "manifest_sha256": _source_sha256(manifest_path),
        "source_crop_sha256": crop_sha256,
        "data_sha256": data_sha256,
        "bundle_data_sha256": str(payload.get("bundle_data_sha256", "")),
        "source_pdf_sha256": str(payload.get("source_pdf", {}).get("sha256", "")),
    }
    if policy == "fresh_extract":
        if payload.get("fresh_extraction") is not True:
            raise ValueError("fresh source manifest is not marked as a new extraction")
        gate["reuse_validation"] = "not_required"
        return gate

    reuse_path = _resolve_candidate_file(candidate, "source_reuse_record", candidate_path)
    if reuse_path is None or not reuse_path.is_file():
        raise ValueError("validated_reuse requires source_reuse_record")
    reuse_payload = json.loads(reuse_path.read_text(encoding="utf-8"))
    if (
        reuse_payload.get("schema") != "originplot.aa2195_validated_data_reuse.v1"
        or reuse_payload.get("status") != "ok"
    ):
        raise ValueError("source reuse record is invalid")
    if policy == "validated_reuse":
        if str(reuse_payload.get("source_bundle_manifest_sha256", "")).lower() != gate["manifest_sha256"]:
            raise ValueError("reused source manifest hash mismatch")
        if str(reuse_payload.get("source_bundle_data_sha256", "")).lower() != gate["bundle_data_sha256"].lower():
            raise ValueError("reused source bundle data hash mismatch")
    else:
        reextracted = payload.get("reextracted_figures")
        if (
            payload.get("validated_crop_reextract") is not True
            or payload.get("source_data_policy") != "validated_crop_reextract"
            or reextracted != ["fig14"]
        ):
            raise ValueError("validated crop re-extraction manifest is invalid")
        if str(payload.get("parent_source_bundle_manifest_sha256", "")).lower() != str(reuse_payload.get("source_bundle_manifest_sha256", "")).lower():
            raise ValueError("re-extraction parent manifest hash mismatch")
        if str(payload.get("parent_source_bundle_data_sha256", "")).lower() != str(reuse_payload.get("source_bundle_data_sha256", "")).lower():
            raise ValueError("re-extraction parent bundle hash mismatch")
        if str(payload.get("source_reuse_record_sha256", "")).lower() != _source_sha256(reuse_path):
            raise ValueError("re-extraction reuse record hash mismatch")
    reuse_figure = reuse_payload.get("figures", {}).get(figure)
    if not isinstance(reuse_figure, dict):
        raise ValueError(f"validated reuse evidence for {figure} is missing")
    required_truth = (
        reuse_figure.get("structure_pass") is True
        and reuse_figure.get("visual_pass") is True
        and reuse_figure.get("live_origin_verified") is True
        and reuse_figure.get("overall_release_pass") is True
        and reuse_figure.get("provenance") == "live_same_run"
    )
    if not required_truth:
        raise ValueError(f"validated reuse quality gates did not pass for {figure}")
    if str(reuse_figure.get("source_crop_sha256", "")).lower() != crop_sha256:
        raise ValueError(f"validated reuse crop hash mismatch for {figure}")
    if policy == "validated_reuse":
        if str(reuse_figure.get("data_sha256", "")).lower() != data_sha256:
            raise ValueError(f"validated reuse data hash mismatch for {figure}")
    else:
        parent_data_sha256 = str(record.get("parent_data_sha256", "")).lower()
        if parent_data_sha256 != str(reuse_figure.get("data_sha256", "")).lower():
            raise ValueError(f"re-extraction parent data hash mismatch for {figure}")
        if figure == "fig14":
            expected_method = "fresh_source_crop_color_marker_and_component_errorbar_digitization"
            if record.get("data_policy") != "validated_crop_reextract" or record["data"].get("method") != expected_method:
                raise ValueError("Fig14 corrected re-extraction method is invalid")
            if data_sha256 == parent_data_sha256:
                raise ValueError("Fig14 corrected re-extraction did not change the parent data")
        elif record.get("data_policy") != "validated_reuse" or data_sha256 != parent_data_sha256:
            raise ValueError(f"validated crop re-extraction changed unrelated data for {figure}")
    gate.update(
        {
            "reuse_validation": "pass",
            "reuse_record_path": str(reuse_path),
            "reuse_record_sha256": _source_sha256(reuse_path),
            "validated_run_id": str(reuse_figure.get("run_id", "")),
            "reextracted_from_validated_crop": policy == "validated_crop_reextract" and figure == "fig14",
        }
    )
    return gate


def _validate_fresh_source_gate(
    figure: str,
    candidate: dict[str, Any],
    candidate_path: Path,
    source_crop: Path | None,
) -> dict[str, Any]:
    """Backward-compatible name for callers that still request fresh extraction."""
    return _validate_source_data_gate(figure, candidate, candidate_path, source_crop)


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
        "fig12_matrix_region_values",
        "fig12_path_overlays",
        "fig12_axis_title_overlays",
        "path_overlay_inventory",
        "fig12_matrix_resolution_scale",
        "fig12_matrix_smoothing_sigma",
        "fig12_matrix_mode",
        "fig12_y_minor_ticks",
        "fig12_panel_layout_offsets",
        "fig12_levels_reapplied_after_palette",
        "fig12_contour_line_style_reapplied_after_levels",
        "fig12_native_contour_lines_requested_visible",
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
        "fig16_background_color",
        "source_data_policy",
        "fresh_source_data_sha256",
        "fresh_source_bundle_sha256",
        "fresh_source_pdf_sha256",
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
        "fig12_matrix_contrasts", "fig12_matrix_region_values",
        "fig12_path_overlays",
        "fig12_axis_title_overlays",
        "fig12_label_sizes",
    ):
        prepared[name] = effective[name]
    prepared["fig12_label_size_offsets"] = {
        "contour": effective["fig12_contour_label_size_offset"],
        "mechanism": effective["fig12_mechanism_label_size_offset"],
    }
    return {"candidate": prepared, "parameter_normalization": normalization}


def _render_identity_payload(
    figure: str,
    route: dict[str, Any],
    source_crop_sha256: str,
    fresh_data_sha256: str = "",
) -> dict[str, Any]:
    effective = {key: value for key, value in route.items() if key != "candidate_params"}
    return {
        "effective_parameters": effective,
        "effective_builder_route": effective,
        "data_digest": fresh_data_sha256 or GEOMETRY_TABLE_VERSIONS[figure],
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


def _fig16_frozen_fingerprint() -> str:
    payload = _render_identity_payload("fig16", FIG16_FROZEN_EFFECTIVE_ROUTE, FIG16_SOURCE_CROP_SHA256)
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
        figure=figure,
    )
    visual.pop("schema", None)
    metrics.update(visual)
    blocking = list(metrics.get("blocking_reasons", []))
    if hard_gate_status.get("status") != "pass":
        blocking.append("origin_structure_hard_gate_failed")
    metrics["blocking_reasons"] = list(dict.fromkeys(blocking))
    metrics["pass_eligible"] = not metrics["blocking_reasons"]
    return metrics


def run_live(
    figure: str | None,
    candidate_path: Path,
    output_dir: Path,
    *,
    builder_id: str | None = None,
    figure_spec_path: Path | None = None,
) -> dict[str, Any]:
    candidate = read_candidate(candidate_path)
    definition = resolve_builder(builder_id=builder_id, figure=figure)
    figure_spec = _read_figure_spec(figure_spec_path)
    plan = definition.validate_plan(candidate, figure_spec)
    effective_figure = figure or str(plan.get("figure") or candidate.get("figure") or definition.builder_id)
    template_search_gate = require_template_search_record(effective_figure, candidate, candidate_path)
    if not definition.supports_live:
        manifest = build_manifest(
            figure=effective_figure,
            candidate=candidate,
            output_dir=output_dir,
            mode="live",
            status="failed",
            error_code="E440_PLOT_FAMILY_NOT_IMPLEMENTED",
            message=f"Builder {definition.builder_id!r} has no verified live implementation.",
            builder_id=definition.builder_id,
        )
        manifest.update({"overall_status": "failed", "plan": plan})
        write_json(output_dir / "candidate_manifest.json", manifest)
        return manifest
    resolved_source_crop = _resolve_source_crop(candidate, candidate_path)
    if str(candidate.get("source_crop", "")).strip() == AUTHORIZED_SOURCE_PLACEHOLDER:
        manifest = build_manifest(
            figure=effective_figure,
            candidate=candidate,
            output_dir=output_dir,
            mode="live",
            status="failed",
            error_code="E124_AUTHORIZED_SOURCE_REQUIRED",
            message=(
                "This packaged candidate requires an authorized local source image "
                "before live execution. Replace source_crop with a readable local path."
            ),
            builder_id=definition.builder_id,
        )
        manifest.update({"origin_attach_not_attempted": True, "overall_status": "failed"})
        write_json(output_dir / "candidate_manifest.json", manifest)
        return manifest
    try:
        source_data_gate = _validate_fresh_source_gate(
            effective_figure, candidate, candidate_path, resolved_source_crop
        )
        source_data_gate = dict(source_data_gate)
        source_data_gate.setdefault("policy", "fresh_extract")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        requested_policy = str(candidate.get("source_data_policy", "")).strip()
        error_code = (
            "E128_SOURCE_DATA_REUSE_REJECTED"
            if requested_policy == "validated_reuse"
            else "E127_FRESH_SOURCE_REQUIRED"
        )
        manifest = build_manifest(
            figure=effective_figure,
            candidate=candidate,
            output_dir=output_dir,
            mode="live",
            status="failed",
            error_code=error_code,
            message=f"Source data gate failed: {exc}",
            builder_id=definition.builder_id,
        )
        manifest.update({"origin_attach_not_attempted": True, "overall_status": "failed"})
        write_json(output_dir / "candidate_manifest.json", manifest)
        return manifest
    if not is_admin():
        manifest = build_manifest(
            figure=effective_figure,
            candidate=candidate,
            output_dir=output_dir,
            mode="live",
            status="failed",
            error_code="E120_ENVIRONMENT_MISMATCH",
            message="Administrator Python is required before importing originpro or attaching to Origin.",
            builder_id=definition.builder_id,
        )
        manifest["origin_attach_not_attempted"] = True
        manifest["overall_status"] = "failed"
        write_json(output_dir / "candidate_manifest.json", manifest)
        return manifest

    manifest = build_manifest(
        figure=effective_figure,
        candidate=candidate,
        output_dir=output_dir,
        mode="live",
        status="started",
        builder_id=definition.builder_id,
    )
    manifest["plan"] = plan
    manifest["template_search_gate"] = template_search_gate
    manifest["source_data_gate"] = source_data_gate
    manifest["fresh_source_gate"] = (
        source_data_gate
        if source_data_gate["policy"] == "fresh_extract"
        else {"status": "not_required", "policy": "validated_reuse"}
    )
    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        prepared = _prepare_candidate_for_build(effective_figure, candidate)
        build_candidate = prepared["candidate"]
        if resolved_source_crop is not None:
            build_candidate["_runtime_source_crop"] = str(resolved_source_crop)
        build_candidate["_runtime_data_manifest"] = source_data_gate["manifest_path"]
        build_candidate["_runtime_source_data_policy"] = source_data_gate["policy"]
        manifest["parameter_normalization"] = prepared["parameter_normalization"]
        if definition.builder_id in {"fig3", "fig12", "fig14", "fig15", "fig16"}:
            builder = _load_aa2195_builder()
            build_result = builder.build_origin_figure(
                figure_id=effective_figure,
                candidate_params=build_candidate,
                output_dir=output_dir,
                attach_existing_authorized=True,
            )
        else:
            build_result = definition.build_live(effective_figure, build_candidate, output_dir)
        if not isinstance(build_result, dict) or build_result.get("status") == "failed":
            failure = build_result if isinstance(build_result, dict) else {}
            failure_code = failure.get("error_code", "E525_CANDIDATE_WORKER_FAILED")
            manifest.update(
                {
                    "status": "failed",
                    "error_code": failure_code,
                    "message": failure.get("message", "The packaged Origin builder failed before producing a candidate."),
                    "builder_result_status": failure.get("status", "invalid_result"),
                    "origin_attach_not_attempted": bool(failure.get("origin_attach_not_attempted", False)),
                    "opju_generation_allowed": bool(failure.get("opju_generation_allowed", False)),
                    "command_success": False,
                    "structure_pass": False,
                    "visual_pass": False,
                    "live_origin_verified": False,
                    "pass_eligible": False,
                    "overall_status": "failed",
                    "builder_failure": failure,
                }
            )
            restart = demo_restart_directive(failure_code, python_is_admin=is_admin())
            if restart is not None:
                manifest["admin_restart_directive"] = restart
                manifest["evidence_provenance"] = "invalid_demo_watermark"
            write_json(
                output_dir / "candidate_readback.json",
                {
                    "schema": "originplot.clean_candidate_readback.v588",
                    "figure": effective_figure,
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
        fig_result = build_result.get("per_figure", {}).get(effective_figure, {}) if isinstance(build_result, dict) else {}
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
            "figure": effective_figure,
            "candidate_sha256": candidate_sha256(candidate),
            "builder_status": build_result.get("status") if isinstance(build_result, dict) else "missing",
            "figure_status": fig_result.get("status"),
            "effective_builder_route": _effective_builder_route(fig_result),
            "editable_view_evidence": fig_result.get("editable_view_evidence", {}),
            "origin_object_readback": fig_result.get("origin_object_readback", {}),
            "origin_object_readback_validation": fig_result.get("origin_object_readback_validation", {}),
            "copy_records": copy_records,
            "source_data_gate": source_data_gate,
            "fresh_source_gate": (
                source_data_gate
                if source_data_gate["policy"] == "fresh_extract"
                else {"status": "not_required", "policy": "validated_reuse"}
            ),
        }
        metrics = evaluate_visual_metrics(
            figure=effective_figure,
            candidate=candidate,
            png=png,
            opju=opju,
            output_dir=output_dir,
            hard_gate_status=fig_result.get("origin_candidate_hard_gate", {}),
            origin_export_qa=fig_result.get("origin_export_qa", []),
            source_crop=source_crop,
        )
        if "E122_ORIGIN_DEMO_EXPORT_BLOCKED" in metrics.get("error_codes", []):
            restart = demo_restart_directive(
                "E122_ORIGIN_DEMO_EXPORT_BLOCKED", python_is_admin=is_admin()
            )
            metrics["admin_restart_directive"] = restart
            metrics["pass_eligible"] = False
            write_json(metrics_path, metrics)
            manifest.update(
                {
                    "status": "failed",
                    "error_code": "E122_ORIGIN_DEMO_EXPORT_BLOCKED",
                    "message": "Demo watermark invalidated the complete run; restart from administrator preflight.",
                    "command_success": False,
                    "structure_pass": False,
                    "visual_pass": False,
                    "live_origin_verified": False,
                    "pass_eligible": False,
                    "overall_status": "failed",
                    "admin_restart_directive": restart,
                    "evidence_provenance": "invalid_demo_watermark",
                }
            )
            return manifest
        effective_route = readback.get("effective_builder_route", {})
        source_hash = _source_sha256(source_crop)
        render_identity = render_parameter_fingerprint(
            _render_identity_payload(
                effective_figure,
                effective_route,
                source_hash,
                source_data_gate["data_sha256"],
            )
        )
        frozen_recognized = effective_figure == "fig15" and source_data_gate["status"] == "pass"
        fig16_frozen_recognized = (
            effective_figure == "fig16"
            and source_data_gate["status"] == "pass"
        )
        target_visual_gate = evaluate_target_visual_gate(
            effective_figure,
            metrics,
            frozen_identity_recognized=frozen_recognized,
            fig16_frozen_identity_recognized=fig16_frozen_recognized,
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
        metrics["fig15_frozen_identity_recognized"] = frozen_recognized if effective_figure == "fig15" else None
        metrics["fig16_frozen_identity_recognized"] = fig16_frozen_recognized if effective_figure == "fig16" else None
        if effective_figure == "fig15":
            metrics["fig15_status"] = "frozen_regression_baseline" if frozen_recognized and target_visual_gate["visual_baseline_promoted"] else "frozen_regression_baseline_failed"
        if effective_figure == "fig12":
            metrics["fig12_roi_metrics"] = evaluate_fig12_rois(
                source_crop, png, output_dir / "visual_evidence" / "fig12_roi_overlay_debug.png"
            )
        metrics["pass_eligible"] = release_status["pass_eligible"]
        if not release_status["pass_eligible"]:
            metrics["blocking_reasons"] = list(dict.fromkeys(list(metrics.get("blocking_reasons", [])) + target_visual_gate["failures"] + ["p18_overall_release_pass_false"]))
        readback["parameter_normalization"] = prepared.get("parameter_normalization")
        readback["render_identity"] = render_identity
        readback["target_visual_gate"] = target_visual_gate
        readback["release_status"] = release_status
        write_json(output_dir / "candidate_readback.json", readback)
        write_json(output_dir / "candidate_visual_metrics.json", metrics)
        standard_evidence = materialize_standard_evidence(
            output_dir=output_dir / "evidence",
            run_id=make_run_id(effective_figure, candidate),
            figure_id=effective_figure,
            skill_version=SKILL_VERSION,
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
                "command_success": True,
                "structure_pass": bool(structure_pass),
                "visual_pass": bool(target_visual_gate.get("visual_baseline_promoted")),
                "live_origin_verified": bool(runtime_ready),
                "overall_status": (
                    "live_visual_pass" if metrics.get("pass_eligible")
                    else "live_structure_pass" if runtime_ready and structure_pass
                    else "incomplete"
                ),
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
        message = str(exc)
        error_code = stable_runtime_error_code(exc)
        manifest.update(
            {
                "status": "failed",
                "error_code": error_code,
                "error_class": exc.__class__.__name__,
                "message": message,
                "traceback": traceback.format_exc(limit=8),
                "command_success": False,
                "structure_pass": False,
                "visual_pass": False,
                "live_origin_verified": False,
                "pass_eligible": False,
                "overall_status": "failed",
            }
        )
        restart = demo_restart_directive(error_code, python_is_admin=is_admin())
        if restart is not None:
            manifest["admin_restart_directive"] = restart
            manifest["evidence_provenance"] = "invalid_demo_watermark"
    finally:
        manifest["release"] = manifest.get("release") or "builder_owned_session_released"
        write_json(output_dir / "candidate_manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description="OriginPlot v5.8.9-p18 candidate worker.")
    parser.add_argument("--figure", help="Legacy-compatible figure id, including fig3, fig12, fig14, fig15, or fig16.")
    parser.add_argument("--builder", help="Registered builder id.")
    parser.add_argument("--figure-spec", type=Path, help="FigureSpec JSON used by registry-based builders.")
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="Validate and plan without launching Origin.")
    mode.add_argument("--live", action="store_true", help="Run the registered live Origin builder.")
    parser.add_argument(
        "--require-live-success",
        action="store_true",
        help="Return nonzero unless a live candidate is pass-eligible.",
    )
    args = parser.parse_args()
    if not args.figure and not args.builder:
        parser.error("one of --figure or --builder is required")
    if args.require_live_success and not args.live:
        parser.error("--require-live-success requires --live")
    if not args.live and not args.dry_run:
        print(
            "NOTICE: no execution mode supplied; using legacy-compatible --dry-run behavior.",
            file=sys.stderr,
        )
    try:
        if args.live:
            manifest = run_live(
                args.figure,
                args.candidate,
                args.output_dir,
                builder_id=args.builder,
                figure_spec_path=args.figure_spec,
            )
        else:
            manifest = run_dry(
                args.figure,
                args.candidate,
                args.output_dir,
                builder_id=args.builder,
                figure_spec_path=args.figure_spec,
            )
    except (UnknownBuilderError, ValueError, OSError, json.JSONDecodeError) as exc:
        if isinstance(exc, UnknownBuilderError):
            error_code = "E440_PLOT_FAMILY_NOT_IMPLEMENTED"
        elif isinstance(exc, TemplateSearchError):
            error_code = "E130_TEMPLATE_SEARCH_REQUIRED"
        else:
            error_code = "E100_SCHEMA_INVALID"
        manifest = {
            "schema": "originplot.clean_rebuild_candidate_worker.v5.8.9-p18",
            "skill_version": SKILL_VERSION,
            "mode": "live" if args.live else "dry_run",
            "status": "failed",
            "overall_status": "failed",
            "error_code": error_code,
            "message": str(exc),
            "command_success": False,
            "structure_pass": False,
            "visual_pass": False,
            "live_origin_verified": False,
            "pass_eligible": False,
        }
        write_json(args.output_dir / "candidate_manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    if args.require_live_success:
        return 0 if manifest.get("pass_eligible") and manifest.get("live_origin_verified") else 1
    return 0 if manifest.get("command_success") or manifest.get("status") in {
        "built_real_candidate_not_promoted",
        "built_real_candidate_pass_eligible",
    } else 1


if __name__ == "__main__":
    raise SystemExit(main())
