from __future__ import annotations

import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from typing import Any

from PIL import Image, ImageChops


SKILL_VERSION = "5.8.9-p14"
STANDARD_FILES = {
    "result.opju",
    "source_crop.png",
    "pre_save.png",
    "post_reopen.png",
    "inspection.json",
    "qa_report.json",
    "benchmark_actual.json",
    "semantic_benchmark_report.json",
    "deviation_ledger.json",
    "comparison_board.png",
    "figurespec.json",
    "compiled_ir.json",
    "operation_plan.json",
    "run_artifacts.json",
    "run_manifest.json",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


def json_safe(value: Any, *, key: str | None = None) -> Any:
    if callable(value):
        return getattr(value, "__qualname__", repr(value))
    if isinstance(value, Path):
        return value.name
    if isinstance(value, str):
        if key == "project_root" and (WINDOWS_ABSOLUTE_RE.match(value) or value.startswith("/")):
            return "."
        if WINDOWS_ABSOLUTE_RE.match(value) or value.startswith("/"):
            return "source_crop.png" if key == "source_crop" else Path(value).name
        return value
    if isinstance(value, dict):
        return {str(item_key): json_safe(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item, key=key) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if hasattr(value, "item"):
        try:
            return json_safe(value.item())
        except Exception:
            return str(value)
    return value


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(json_safe(payload), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def copy_required(source: Path, target: Path) -> None:
    source = Path(source)
    if not source.is_file():
        raise FileNotFoundError(source)
    shutil.copy2(source, target)


def create_comparison_board(source: Path, pre: Path, post: Path, output: Path) -> None:
    with Image.open(source) as src_image, Image.open(pre) as pre_image, Image.open(post) as post_image:
        src = src_image.convert("RGB")
        size = src.size
        pre_rgb = pre_image.convert("RGB").resize(size)
        post_rgb = post_image.convert("RGB").resize(size)
        diff = ImageChops.difference(src, post_rgb)
        board = Image.new("RGB", (size[0] * 2, size[1] * 2), "white")
        board.paste(src, (0, 0))
        board.paste(pre_rgb, (size[0], 0))
        board.paste(post_rgb, (0, size[1]))
        board.paste(diff, (size[0], size[1]))
        board.save(output)


def identity(run_id: str, figure_id: str, skill_version: str) -> dict[str, str]:
    return {
        "run_id": run_id,
        "figure_id": figure_id,
        "skill_version": skill_version,
    }


def selected_visual_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "canvas_match",
        "source_canvas",
        "candidate_canvas",
        "mae_0_1",
        "rmse_0_1",
        "ssim_score",
        "layout_score",
        "edge_score",
        "color_score",
        "registration_shift",
        "nonwhite_ratio_source",
        "nonwhite_ratio_candidate",
        "demo_cyan_ratio",
        "blocking_reasons",
        "pass_eligible",
        "release_status",
        "render_identity",
        "target_visual_gate",
        "fig12_roi_metrics",
        "fig15_frozen_identity_recognized",
    ]
    return {key: json_safe(metrics[key]) for key in keys if key in metrics}


def materialize_standard_evidence(
    *,
    output_dir: Path,
    run_id: str,
    figure_id: str,
    skill_version: str,
    source_crop: Path,
    opju: Path,
    pre_save: Path,
    post_reopen: Path,
    inspection: dict[str, Any],
    visual_metrics: dict[str, Any],
    route: dict[str, Any],
) -> dict[str, Any]:
    if not run_id or not figure_id or skill_version != SKILL_VERSION:
        raise ValueError("p14 evidence requires nonempty run_id/figure_id and skill_version=5.8.9-p14")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise RuntimeError("standard evidence output directory must be empty")

    copy_required(opju, output_dir / "result.opju")
    copy_required(source_crop, output_dir / "source_crop.png")
    copy_required(pre_save, output_dir / "pre_save.png")
    copy_required(post_reopen, output_dir / "post_reopen.png")
    create_comparison_board(
        output_dir / "source_crop.png",
        output_dir / "pre_save.png",
        output_dir / "post_reopen.png",
        output_dir / "comparison_board.png",
    )

    ident = identity(run_id, figure_id, skill_version)
    route_safe = json_safe(route)
    metrics_safe = selected_visual_metrics(visual_metrics)
    release_status = json_safe(visual_metrics.get("release_status", {}))
    pass_eligible = bool(release_status.get("overall_release_pass"))
    readback = inspection.get("origin_object_readback", inspection)
    readback_validation = inspection.get("origin_object_readback_validation", {})

    figurespec = {
        "schema": "originplot.figurespec.v5",
        **ident,
        "figure_class": "native_chart" if figure_id == "fig12" else "semantic_schematic",
        "acceptance_mode": "visual_editable",
        "reproduction_mode": route_safe.get("reproduction_mode", "reconstructed_approximate"),
        "primary_route": route_safe.get("route"),
        "source_crop": "source_crop.png",
    }
    compiled_ir = {
        "schema": "originplot.compiled_ir.v5",
        **ident,
        "primary_route": route_safe,
        "operations": ["build", "pre_save_export", "save", "release", "reopen", "inspect", "post_reopen_export"],
    }
    operation_plan = {
        "schema": "originplot.operation_plan.v5",
        **ident,
        "session_mode": "administrator_attach_existing_authorized_two_phase",
        "steps": [
            "attach_build",
            "pre_save_export",
            "save_result_opju",
            "detach_build",
            "attach_reopen",
            "editable_same_path_save",
            "deep_readback",
            "post_reopen_export",
            "detach_reopen",
        ],
    }
    inspection_payload = {
        "schema": "originplot.inspection.v5",
        **ident,
        "provenance": "live_same_run",
        "origin_object_readback": json_safe(readback),
        "origin_object_readback_validation": json_safe(readback_validation),
    }
    qa_report = {
        "schema": "originplot.qa_report.v1",
        **ident,
        "status": "pass" if pass_eligible else "failed",
        "pass_eligible": pass_eligible,
        "visual_metrics": metrics_safe,
        "release_status": release_status,
        "blocking_reasons": json_safe(visual_metrics.get("blocking_reasons", [])),
    }
    benchmark_actual = {
        "schema": "originplot.benchmark_actual.v1",
        **ident,
        "status": "pass" if pass_eligible else "failed",
        "materialized_from": ["inspection.json", "qa_report.json"],
        "structure": json_safe(readback_validation),
        "visual": metrics_safe,
        "release_status": release_status,
    }
    semantic_report = {
        "schema": "originplot.semantic_figure_benchmark.v1",
        **ident,
        "status": "pass" if pass_eligible else "failed",
        "eligible_for_pass": pass_eligible,
        "blocking_deviations": json_safe(visual_metrics.get("blocking_reasons", [])),
        "release_status": release_status,
    }
    deviation_ledger = {
        "schema": "originplot.deviation_ledger.v1",
        **ident,
        "status": "pass" if pass_eligible else "failed",
        "blocking": json_safe(visual_metrics.get("blocking_reasons", [])),
        "warnings": ["reconstructed_approximate provenance"],
    }
    run_manifest = {
        "schema": "originplot.run_manifest.v5",
        **ident,
        "status": "pass" if pass_eligible else "failed",
        "provenance": "live_same_run",
        "eligible_for_pass": pass_eligible,
        "release_status": release_status,
        "session_mode": "administrator_attach_existing_authorized_two_phase",
        "standard_evidence_files": sorted(STANDARD_FILES),
    }

    payloads = {
        "figurespec.json": figurespec,
        "compiled_ir.json": compiled_ir,
        "operation_plan.json": operation_plan,
        "inspection.json": inspection_payload,
        "qa_report.json": qa_report,
        "benchmark_actual.json": benchmark_actual,
        "semantic_benchmark_report.json": semantic_report,
        "deviation_ledger.json": deviation_ledger,
        "run_manifest.json": run_manifest,
    }
    for name, payload in payloads.items():
        write_json(output_dir / name, payload)

    artifact_records = []
    for name in sorted(STANDARD_FILES - {"run_artifacts.json"}):
        path = output_dir / name
        artifact_records.append(
            {
                "path": name,
                "sha256": sha256_file(path),
                "exists": True,
                "provenance": "live_same_run",
                "eligible_for_pass": pass_eligible,
            }
        )
    run_artifacts = {
        "schema": "originplot.artifacts.v1",
        **ident,
        "provenance": "live_same_run",
        "eligible_for_pass": pass_eligible,
        "artifacts": artifact_records,
    }
    write_json(output_dir / "run_artifacts.json", run_artifacts)
    actual_files = {path.name for path in output_dir.iterdir() if path.is_file()}
    return {
        "status": "ok" if actual_files == STANDARD_FILES else "failed",
        "run_id": run_id,
        "figure_id": figure_id,
        "skill_version": skill_version,
        "pass_eligible": pass_eligible,
        "files": sorted(actual_files),
    }
