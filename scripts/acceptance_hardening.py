from __future__ import annotations

import hashlib
import json
import math
from typing import Any


RENDER_IDENTITY_SCHEMA = "originplot.render_identity.v1"
FIG12_DEFAULTS = {
    "fig12_matrix_resolution_scale": 0.5,
    "fig12_matrix_smoothing_sigma": 0.5,
    "fig12_matrix_mode": "source_palette_digitized",
    "fig12_y_minor_ticks": 0,
    "fig12_panel_layout_offsets": {str(i): {"dx": 0.0, "dy": 0.0} for i in range(3)},
    "fig12_matrix_biases": {"0": 0.0, "1": 0.0, "2": 0.0},
    "fig12_matrix_contrasts": {"0": 1.0, "1": 1.0, "2": 1.0},
    "fig12_matrix_region_values": {},
    "fig12_path_overlays": True,
    "fig12_axis_title_overlays": True,
    "fig12_contour_label_size_offset": 0.0,
    "fig12_mechanism_label_size_offset": 0.0,
    "fig12_label_sizes": {
        "panel": 11.0, "contour": 8.4, "mechanism": 10.0,
        "colorbar_title": 10.0, "colorbar_tick": 8.0,
    },
}
FIG12_NUMERIC_RANGES = {
    "fig12_matrix_resolution_scale": (0.35, 0.5),
    "fig12_matrix_smoothing_sigma": (0.0, 8.0),
    "fig12_y_minor_ticks": (0.0, 8.0),
    "fig12_contour_label_size_offset": (-6.0, 6.0),
    "fig12_mechanism_label_size_offset": (-6.0, 6.0),
}
TARGET_VISUAL_GATES = {
    "fig3": {
        # Source-calibrated four-panel route; other geometry/color gates remain strict.
        "mae_0_1": ("max", 0.090), "ssim_score": ("min", 0.650),
        "layout_score": ("min", 0.955), "edge_score": ("min", 0.600),
        "color_score": ("min", 0.900), "registration_abs_dx_px": ("max", 12.0),
        "registration_abs_dy_px": ("max", 8.0), "foreground_f1": ("min", 0.520),
        "edge_f1": ("min", 0.550), "nonwhite_delta": ("max", 0.030),
    },
    "fig12": {
        "mae_0_1": ("max", 0.0405), "ssim_score": ("min", 0.7770),
        "layout_score": ("min", 0.9420), "edge_score": ("min", 0.7450),
        "color_score": ("min", 0.9200), "registration_abs_dx_px": ("max", 16.0),
        "registration_abs_dy_px": ("max", 6.0), "content_bbox_axis_error_px": ("max", 31.0),
        "nonwhite_delta": ("max", 0.035), "foreground_f1": ("min", 0.970),
        "edge_f1": ("min", 0.810),
    },
    "fig15": {
        "mae_0_1": ("max", 0.040), "ssim_score": ("min", 0.810),
        "layout_score": ("min", 0.985), "edge_score": ("min", 0.730),
        "color_score": ("min", 0.925), "registration_abs_dx_px": ("max", 4.0),
        "registration_abs_dy_px": ("max", 2.0), "foreground_f1": ("min", 0.700),
        "edge_f1": ("min", 0.730), "nonwhite_delta": ("max", 0.035),
    },
    "fig14": {
        "mae_0_1": ("max", 0.065), "ssim_score": ("min", 0.760),
        "layout_score": ("min", 0.970), "edge_score": ("min", 0.650),
        "color_score": ("min", 0.930), "registration_abs_dx_px": ("max", 8.0),
        "registration_abs_dy_px": ("max", 6.0), "foreground_f1": ("min", 0.430),
        "edge_f1": ("min", 0.440), "nonwhite_delta": ("max", 0.012),
    },
    "fig16": {
        "mae_0_1": ("max", 0.067), "ssim_score": ("min", 0.695),
        "layout_score": ("min", 0.985), "edge_score": ("min", 0.590),
        "color_score": ("min", 0.950), "registration_abs_dx_px": ("max", 5.0),
        "registration_abs_dy_px": ("max", 2.0), "foreground_f1": ("min", 0.970),
        "edge_f1": ("min", 0.820), "nonwhite_delta": ("max", 0.065),
        "fig16_bar_boundary_max_error_px": ("max", 1.0),
        "fig16_bar_boundary_mean_error_px": ("max", 0.5),
        "fig16_bar_boundary_missing_segments": ("max", 0.0),
    },
}
NEAR_THRESHOLD_MARGIN = 0.001


def derive_release_status(
    runtime_release_ready: bool,
    structure_pass: bool,
    visual_baseline: bool | str,
) -> dict[str, Any]:
    promoted = visual_baseline is True or visual_baseline == "promoted"
    visual_status = "promoted" if promoted else (
        str(visual_baseline) if isinstance(visual_baseline, str) else "not_promoted"
    )
    overall = bool(runtime_release_ready and structure_pass and promoted)
    return {
        "runtime_release_ready": bool(runtime_release_ready),
        "structure_pass": bool(structure_pass),
        "visual_baseline_status": visual_status,
        "visual_baseline_promoted": promoted,
        "overall_release_pass": overall,
        "pass_eligible": overall,
        "pass_eligible_deprecated": True,
        "pass_eligible_source": "derived_from_release_status",
    }


def evaluate_target_visual_gate(
    figure: str,
    metrics: dict[str, Any],
    *,
    frozen_identity_recognized: bool = False,
    fig16_frozen_identity_recognized: bool = False,
) -> dict[str, Any]:
    if figure not in TARGET_VISUAL_GATES:
        raise ValueError(f"unsupported figure visual gate: {figure}")
    shift = metrics.get("registration_shift") if isinstance(metrics.get("registration_shift"), dict) else {}
    source_bbox = metrics.get("source_content_bbox")
    actual_bbox = metrics.get("actual_content_bbox")
    values = dict(metrics)
    values["registration_abs_dx_px"] = abs(float(shift.get("dx_px", 999.0)))
    values["registration_abs_dy_px"] = abs(float(shift.get("dy_px", 999.0)))
    if isinstance(source_bbox, list) and isinstance(actual_bbox, list) and len(source_bbox) == len(actual_bbox) == 4:
        values["content_bbox_axis_error_px"] = max(abs(float(a) - float(b)) for a, b in zip(source_bbox, actual_bbox))
    else:
        values["content_bbox_axis_error_px"] = 999.0
    if "nonwhite_delta" not in values:
        values["nonwhite_delta"] = abs(float(metrics.get("source_nonwhite_ratio", 0.0)) - float(metrics.get("actual_nonwhite_ratio", 0.0)))
    checks: dict[str, bool] = {}
    gate_margins: dict[str, float] = {}
    for name, (direction, threshold) in TARGET_VISUAL_GATES[figure].items():
        value = float(values.get(name, 999.0 if direction == "max" else -999.0))
        checks[name] = value <= threshold if direction == "max" else value >= threshold
        gate_margins[name] = threshold - value if direction == "max" else value - threshold
    failures = [name for name, passed in checks.items() if not passed]
    if figure == "fig15" and not frozen_identity_recognized:
        failures.append("frozen_render_identity_not_recognized")
    if figure == "fig16" and not fig16_frozen_identity_recognized:
        failures.append("frozen_render_identity_not_recognized")
    promoted = not failures
    status = "promoted" if promoted else "not_promoted"
    return {
        "schema": "originplot.target_visual_gate.v1",
        "figure_id": figure,
        "baseline_role": "frozen_regression" if figure in {"fig15", "fig16"} else "candidate_baseline",
        "thresholds": TARGET_VISUAL_GATES[figure],
        "values": {name: values.get(name) for name in TARGET_VISUAL_GATES[figure]},
        "checks": checks,
        "gate_margins": gate_margins,
        "near_threshold_metrics": sorted(
            name for name, margin in gate_margins.items()
            if checks[name] and margin < NEAR_THRESHOLD_MARGIN
        ),
        "failures": failures,
        "frozen_identity_recognized": (
            bool(frozen_identity_recognized) if figure == "fig15"
            else bool(fig16_frozen_identity_recognized) if figure == "fig16"
            else None
        ),
        "visual_baseline_status": status,
        "visual_baseline_promoted": promoted,
    }


def _normalize_json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _normalize_json(value[k]) for k in sorted(value, key=str)}
    if isinstance(value, (list, tuple)):
        return [_normalize_json(item) for item in value]
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("render identity cannot contain non-finite floats")
        return float(format(value, ".12g"))
    return value


def render_parameter_fingerprint(payload: dict[str, Any]) -> dict[str, Any]:
    effective = payload.get("effective_parameters") or {}
    identity = {
        "schema_version": "1",
        "effective_parameters": effective,
        "effective_builder_route": payload.get("effective_builder_route") or {},
        "data_digest": payload.get("data_digest"),
        "geometry_table_version": payload.get("geometry_table_version"),
        "source_crop_sha256": payload.get("source_crop_sha256"),
        "origin_version": payload.get("origin_version"),
        "export_profile": payload.get("export_profile"),
        "template_ids": payload.get("template_ids") or [],
        "font_profile": payload.get("font_profile"),
        "feature_flags": payload.get("feature_flags") or {},
    }
    normalized = _normalize_json(identity)
    encoded = json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    effective_encoded = json.dumps(
        _normalize_json(effective), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return {
        "schema": RENDER_IDENTITY_SCHEMA,
        "schema_version": "1",
        "algorithm": "sha256",
        "fingerprint": hashlib.sha256(encoded).hexdigest(),
        "effective_parameter_digest": hashlib.sha256(effective_encoded).hexdigest(),
        "source_crop_sha256": payload.get("source_crop_sha256"),
        "geometry_table_version": payload.get("geometry_table_version"),
        "origin_version": payload.get("origin_version"),
        "export_profile": payload.get("export_profile"),
    }


def _number_record(name: str, requested: Any, default: float, low: float, high: float, strict: bool) -> tuple[float, dict[str, Any]]:
    defaulted = requested is None
    try:
        number = default if defaulted else float(requested)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} requested={requested!r} is not numeric") from exc
    clamped = number < low or number > high
    if strict and clamped:
        raise ValueError(f"{name} requested={number} outside allowed range [{low}, {high}]")
    effective = min(high, max(low, number))
    reason = "below_minimum" if number < low else "above_maximum" if number > high else "default_used" if defaulted else "within_range"
    return effective, {
        "requested": requested,
        "effective": effective,
        "clamped": clamped,
        "defaulted": defaulted,
        "allowed_range": [low, high],
        "reason": reason,
    }


def normalize_fig12_parameters(requested: dict[str, Any], *, strict: bool) -> dict[str, Any]:
    requested = requested if isinstance(requested, dict) else {}
    requested = dict(requested)
    legacy_offsets = requested.get("fig12_label_size_offsets")
    if isinstance(legacy_offsets, dict):
        requested.setdefault("fig12_contour_label_size_offset", legacy_offsets.get("contour"))
        requested.setdefault("fig12_mechanism_label_size_offset", legacy_offsets.get("mechanism"))
    effective = json.loads(json.dumps(FIG12_DEFAULTS))
    records: dict[str, Any] = {}
    diagnostic = False
    for name, (low, high) in FIG12_NUMERIC_RANGES.items():
        value, record = _number_record(name, requested.get(name), float(FIG12_DEFAULTS[name]), low, high, strict)
        if name == "fig12_y_minor_ticks":
            value = int(round(value))
            record["effective"] = value
        effective[name] = value
        records[name] = record
        diagnostic = diagnostic or record["clamped"]
    mode = requested.get("fig12_matrix_mode")
    allowed_modes = ["source_palette_digitized", "analytic_fallback"]
    if mode is not None and mode not in allowed_modes:
        if strict:
            raise ValueError(f"fig12_matrix_mode requested={mode!r} allowed={allowed_modes}")
        diagnostic = True
        effective["fig12_matrix_mode"] = FIG12_DEFAULTS["fig12_matrix_mode"]
    elif mode is not None:
        effective["fig12_matrix_mode"] = mode
    records["fig12_matrix_mode"] = {
        "requested": mode,
        "effective": effective["fig12_matrix_mode"],
        "clamped": mode is not None and mode not in allowed_modes,
        "defaulted": mode is None,
        "allowed_values": allowed_modes,
        "reason": "invalid_choice" if mode is not None and mode not in allowed_modes else "default_used" if mode is None else "valid_choice",
    }
    for name in (
        "fig12_panel_layout_offsets",
        "fig12_matrix_biases",
        "fig12_matrix_contrasts",
        "fig12_matrix_region_values",
    ):
        if name in requested:
            effective[name] = _normalize_json(requested[name])
        records[name] = {
            "requested": requested.get(name),
            "effective": effective[name],
            "clamped": False,
            "defaulted": name not in requested,
            "reason": "default_used" if name not in requested else "normalized",
        }
    path_overlays = requested.get("fig12_path_overlays")
    if path_overlays is not None and not isinstance(path_overlays, bool):
        if strict:
            raise ValueError("fig12_path_overlays must be boolean")
        path_overlays = False
        diagnostic = True
    effective["fig12_path_overlays"] = FIG12_DEFAULTS["fig12_path_overlays"] if path_overlays is None else path_overlays
    records["fig12_path_overlays"] = {
        "requested": requested.get("fig12_path_overlays"),
        "effective": effective["fig12_path_overlays"],
        "clamped": path_overlays is not None and not isinstance(requested.get("fig12_path_overlays"), bool),
        "defaulted": path_overlays is None,
        "reason": "default_used" if path_overlays is None else "normalized",
    }
    axis_title_overlays = requested.get("fig12_axis_title_overlays")
    if axis_title_overlays is not None and not isinstance(axis_title_overlays, bool):
        if strict:
            raise ValueError("fig12_axis_title_overlays must be boolean")
        axis_title_overlays = False
        diagnostic = True
    effective["fig12_axis_title_overlays"] = (
        FIG12_DEFAULTS["fig12_axis_title_overlays"] if axis_title_overlays is None else axis_title_overlays
    )
    records["fig12_axis_title_overlays"] = {
        "requested": requested.get("fig12_axis_title_overlays"),
        "effective": effective["fig12_axis_title_overlays"],
        "clamped": axis_title_overlays is not None and not isinstance(requested.get("fig12_axis_title_overlays"), bool),
        "defaulted": axis_title_overlays is None,
        "reason": "default_used" if axis_title_overlays is None else "normalized",
    }
    raw_sizes = requested.get("fig12_label_sizes")
    raw_sizes = raw_sizes if isinstance(raw_sizes, dict) else {}
    for role, default in FIG12_DEFAULTS["fig12_label_sizes"].items():
        name = f"fig12_label_sizes.{role}"
        value, record = _number_record(name, raw_sizes.get(role), float(default), 4.0, 18.0, strict)
        effective["fig12_label_sizes"][role] = value
        records[name] = record
    return {
        "schema": "originplot.parameter_normalization.v1",
        "strict_parameter_validation": bool(strict),
        "mode": "formal_benchmark" if strict else "diagnostic",
        "promotion_eligible": not diagnostic,
        "effective_parameters": effective,
        "parameter_normalization": records,
        "warnings": ["clamped_parameters_make_candidate_diagnostic"] if diagnostic else [],
    }
