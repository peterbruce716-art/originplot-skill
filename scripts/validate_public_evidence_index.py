from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

try:
    from scripts.versioning import load_versions
except ModuleNotFoundError:
    from versioning import load_versions


VERSIONS = load_versions()
REQUIRED_FIGURES = {"fig3", "fig12", "fig14", "fig15", "fig16"}
HASH_FIELDS = {
    "candidate_sha256",
    "render_fingerprint",
    "manifest_sha256",
    "visual_metrics_sha256",
}
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
RUN_ID_RE = re.compile(r"^p18-(fig3|fig12|fig14|fig15|fig16)-[0-9a-f]{12}-\d{8}T\d{6}$")
REQUIRED_METRICS = {
    "mae_0_1",
    "ssim_score",
    "layout_score",
    "edge_score",
    "color_score",
    "foreground_f1",
    "edge_f1",
    "nonwhite_delta",
}
ALLOWED_SOURCE_DATA_POLICIES = {"fresh_extract", "validated_crop_reextract", "validated_reuse"}
PUBLIC_LIMITS = {
    "verification_level": "maintainer_attested_index",
    "public_artifacts_reproducible": False,
    "independent_pixel_verification_possible": False,
    "reason": "copyrighted_or_authorized_assets_not_redistributed",
}


def _result(failures: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "originplot.public_evidence_index_validation.v1",
        **VERSIONS.as_dict(),
        "status": "ok" if not failures else "failed",
        "verification_level": "maintainer_attested_index",
        "live_origin_verified": False,
        "pass_eligible": False,
        "independent_pixel_verification_possible": False,
        "failures": failures,
    }


def validate(payload: Any) -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        return _result([{"code": "invalid_payload_type", "expected": "object"}])
    if payload.get("schema") != "originplot.aa2195_release_evidence_index.v1":
        failures.append({"code": "invalid_schema"})
    expected_versions = {
        "release_version": VERSIONS.release_version,
        "contract_version": VERSIONS.contract_version,
        "evidence_version": VERSIONS.evidence_version,
        "skill_version": VERSIONS.evidence_version,
    }
    for field, expected in expected_versions.items():
        if payload.get(field) != expected:
            failures.append({"code": "version_mismatch", "field": field, "expected": expected})
    for field, expected in PUBLIC_LIMITS.items():
        if payload.get(field) != expected:
            failures.append({"code": "public_verification_limit_mismatch", "field": field})

    batch = payload.get("batch")
    valid_batch = (
        isinstance(batch, dict)
        and isinstance(batch.get("completed_at"), str)
        and bool(batch["completed_at"].strip())
        and batch.get("status") == "pass"
        and type(batch.get("figure_count")) is int
        and batch["figure_count"] == 5
        and type(batch.get("findings_count")) is int
        and batch["findings_count"] == 0
        and batch.get("single_visible_origin_pid_verified") is True
        and batch.get("source_data_policy") in ALLOWED_SOURCE_DATA_POLICIES
        and (
            batch.get("source_data_policy") != "fresh_extract"
            or (
                batch.get("same_run_fresh_source_verified") is True
                and batch.get("origin_launch_mode") == "batch_started"
            )
        )
    )
    if not valid_batch:
        failures.append({"code": "invalid_batch_attestation"})

    routes = payload.get("routes")
    if not isinstance(routes, list):
        failures.append({"code": "routes_not_list"})
        routes = []
    figure_ids = [route.get("figure") for route in routes if isinstance(route, dict)]
    if len(routes) != 5 or len(set(figure_ids)) != 5 or set(figure_ids) != REQUIRED_FIGURES:
        failures.append({"code": "duplicate_or_incomplete_figure_set"})

    for route in routes:
        if not isinstance(route, dict):
            failures.append({"code": "invalid_route"})
            continue
        figure = str(route.get("figure", ""))
        run_id = route.get("run_id")
        run_match = RUN_ID_RE.fullmatch(run_id) if isinstance(run_id, str) else None
        if run_match is None or run_match.group(1) != figure:
            failures.append({"code": "invalid_run_id", "figure": figure})
        if (
            route.get("status") != "built_real_candidate_pass_eligible"
            or not isinstance(route.get("geometry_table_version"), str)
            or not route["geometry_table_version"].strip()
        ):
            failures.append({"code": "invalid_route_attestation", "figure": figure})
        for field in sorted(HASH_FIELDS):
            value = route.get(field)
            if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
                failures.append({"code": "invalid_sha256", "figure": figure, "field": field})
        metrics = route.get("metrics")
        if not isinstance(metrics, dict) or set(metrics) != REQUIRED_METRICS:
            failures.append({"code": "invalid_metric_set", "figure": figure})
        if isinstance(metrics, dict):
            for field, value in metrics.items():
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or not 0.0 <= float(value) <= 1.0
                ):
                    failures.append({"code": "invalid_metric", "figure": figure, "field": field})
        if figure == "fig16":
            boundary = route.get("bar_boundary")
            valid_boundary = isinstance(boundary, dict) and (
                type(boundary.get("expected_segment_count")) is int
                and boundary["expected_segment_count"] == 21
                and type(boundary.get("source_segment_count")) is int
                and boundary["source_segment_count"] == 21
                and type(boundary.get("actual_segment_count")) is int
                and boundary["actual_segment_count"] == 21
                and type(boundary.get("missing_segments")) is int
                and boundary["missing_segments"] == 0
                and not isinstance(boundary.get("max_abs_boundary_error_px"), bool)
                and isinstance(boundary.get("max_abs_boundary_error_px"), (int, float))
                and math.isfinite(boundary["max_abs_boundary_error_px"])
                and 0.0 <= float(boundary["max_abs_boundary_error_px"]) <= 1.0
                and not isinstance(boundary.get("mean_abs_boundary_error_px"), bool)
                and isinstance(boundary.get("mean_abs_boundary_error_px"), (int, float))
                and math.isfinite(boundary["mean_abs_boundary_error_px"])
                and 0.0 <= float(boundary["mean_abs_boundary_error_px"]) <= 0.5
            )
            if not valid_boundary:
                failures.append({"code": "incomplete_fig16_boundary_audit", "figure": figure})

    return _result(failures)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate the sanitized OriginPlot public evidence index.")
    parser.add_argument("path", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        payload = json.loads(args.path.read_text(encoding="utf-8-sig"))
        result = validate(payload)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        result = {
            "schema": "originplot.public_evidence_index_validation.v1",
            "status": "failed",
            "live_origin_verified": False,
            "pass_eligible": False,
            "failures": [{"code": "invalid_evidence_index_file", "message": str(exc)}],
        }
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
