from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIGURES = ("fig3", "fig12", "fig14", "fig15", "fig16")
BATCH_SCHEMA = "originplot.five_figure_live_batch.v2"


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _valid_window(window: Any, pid: Any) -> bool:
    if not isinstance(window, dict):
        return False
    handle = window.get("main_window_handle")
    return (
        window.get("pid") == pid
        and isinstance(handle, int)
        and not isinstance(handle, bool)
        and handle > 0
        and window.get("is_visible") is True
        and window.get("is_iconic") is False
    )


def audit_batch(
    root: Path, *, require_visible_window_evidence: bool = False
) -> dict[str, Any]:
    root = Path(root)
    findings: list[dict[str, Any]] = []
    records: dict[str, dict[str, Any]] = {}
    status_path = root / "live_validation_status.json"
    if not status_path.exists():
        findings.append({"code": "MISSING_BATCH_STATUS", "path": status_path.name})
        batch_status: dict[str, Any] = {}
    else:
        batch_status = _load(status_path)

    if batch_status.get("schema") != BATCH_SCHEMA:
        findings.append(
            {
                "code": "BATCH_SCHEMA_INVALID",
                "expected": BATCH_SCHEMA,
                "actual": batch_status.get("schema"),
            }
        )
    runs = batch_status.get("runs")
    run_records = (
        [item for item in runs if isinstance(item, dict)]
        if isinstance(runs, list)
        else []
    )
    runs_by_figure = {str(item.get("figure")): item for item in run_records}
    if len(run_records) != len(runs_by_figure):
        findings.append(
            {
                "code": "BATCH_RUN_RECORDS_NOT_UNIQUE",
                "record_count": len(run_records),
                "unique_figure_count": len(runs_by_figure),
            }
        )
    run_ids = [str(item.get("run_id")) for item in run_records if item.get("run_id")]
    for item in run_records:
        if not item.get("run_id"):
            findings.append(
                {"code": "BATCH_RUN_ID_MISSING", "figure": item.get("figure")}
            )
    if len(run_ids) != len(set(run_ids)):
        findings.append({"code": "BATCH_RUN_IDS_NOT_UNIQUE", "run_ids": run_ids})
    pids = {
        item.get("visible_origin_pid")
        for item in runs_by_figure.values()
        if item.get("visible_origin_pid") is not None
    }
    if len(runs_by_figure) != len(FIGURES) or set(runs_by_figure) != set(FIGURES):
        findings.append(
            {"code": "BATCH_FIGURE_SET_INCOMPLETE", "figures": sorted(runs_by_figure)}
        )
    if len(pids) != 1:
        findings.append(
            {
                "code": "ORIGIN_PID_NOT_SHARED",
                "visible_origin_pids": sorted(str(pid) for pid in pids),
            }
        )
    started_pid = batch_status.get("started_visible_origin_pid")
    if started_pid is None or len(pids) != 1 or started_pid not in pids:
        findings.append(
            {
                "code": "ORIGIN_PID_START_RECORD_MISMATCH",
                "started_visible_origin_pid": started_pid,
                "run_pids": sorted(str(pid) for pid in pids),
            }
        )
    # The batch runner already decides whether every worker exited zero against a
    # stable visible Origin, and run_five_figure_live_batch.ps1 exits with this
    # auditor's status. Ignoring the runner's own verdict let a batch that the
    # runner marked failed be audited as pass and exit zero. Fail closed: an
    # absent field is not evidence of success.
    batch_run_status = batch_status.get("status")
    if batch_run_status != "completed":
        findings.append(
            {"code": "BATCH_STATUS_NOT_COMPLETED", "status": batch_run_status}
        )
    for figure, run in sorted(runs_by_figure.items()):
        if run.get("exit_code") != 0:
            findings.append(
                {
                    "code": "FIGURE_WORKER_EXIT_NONZERO",
                    "figure": figure,
                    "exit_code": run.get("exit_code"),
                }
            )
        if run.get("pid_stable") is not True:
            findings.append(
                {
                    "code": "ORIGIN_PID_UNSTABLE",
                    "figure": figure,
                    "pid_stable": run.get("pid_stable"),
                }
            )
    visibility_required = (
        require_visible_window_evidence
        or batch_status.get("visible_window_evidence_required") is True
    )
    if visibility_required:
        for figure, run in sorted(runs_by_figure.items()):
            for phase in (
                "origin_processes_before_cleanup",
                "origin_processes_after_cleanup",
            ):
                inventory = run.get(phase)
                unique_visible_process = (
                    isinstance(inventory, list)
                    and len(inventory) == 1
                    and isinstance(inventory[0], dict)
                    and inventory[0].get("pid") == started_pid
                    and inventory[0].get("is_embedding") is False
                    and isinstance(inventory[0].get("main_window_handle"), int)
                    and inventory[0]["main_window_handle"] > 0
                )
                if not unique_visible_process:
                    findings.append(
                        {
                            "code": "ORIGIN_WINDOW_PROCESS_CONFLICT",
                            "figure": figure,
                            "phase": phase,
                        }
                    )
            for phase in (
                "origin_window_presentation",
                "origin_window_after_worker",
                "origin_window_after_display",
            ):
                window = run.get(phase)
                if not _valid_window(window, started_pid):
                    findings.append(
                        {
                            "code": "ORIGIN_WINDOW_NOT_VISIBLE",
                            "figure": figure,
                            "phase": phase,
                        }
                    )
            samples_path = root / figure / "origin_window_samples.json"
            try:
                samples = json.loads(samples_path.read_text(encoding="utf-8-sig"))
            except (OSError, ValueError):
                samples = None
            valid_samples = (
                isinstance(samples, list)
                and len(samples) >= 2
                and all(_valid_window(sample, started_pid) for sample in samples)
                and run.get("visibility_sample_count") == len(samples)
                and run.get("visibility_failed_sample_count") == 0
                and run.get("visibility_verified") is True
            )
            if not valid_samples:
                findings.append(
                    {"code": "ORIGIN_WINDOW_SAMPLES_INVALID", "figure": figure}
                )
    for figure in FIGURES:
        manifest_path = root / figure / "candidate_manifest.json"
        readback_path = root / figure / "candidate_readback.json"
        run_manifest_path = root / figure / "evidence" / "run_manifest.json"
        if (
            not manifest_path.exists()
            or not readback_path.exists()
            or not run_manifest_path.exists()
        ):
            findings.append({"code": "MISSING_FIGURE_EVIDENCE", "figure": figure})
            continue
        manifest = _load(manifest_path)
        readback = _load(readback_path)
        run_manifest = _load(run_manifest_path)
        source_geometry_status = (
            readback.get("origin_object_readback_validation", {})
            .get("source_geometry_group_validation", {})
            .get("status")
        )
        subplot_worksheet_status = (
            readback.get("origin_object_readback_validation", {})
            .get("subplot_worksheet_validation", {})
            .get("status")
        )
        legend_plot_reference_status = (
            readback.get("origin_object_readback_validation", {})
            .get("legend_plot_reference_validation", {})
            .get("status")
        )
        plot_style_status = (
            readback.get("origin_object_readback_validation", {})
            .get("plot_style_validation", {})
            .get("status")
        )
        source_data_gate = readback.get("source_data_gate") or readback.get(
            "fresh_source_gate"
        )
        source_data_status = (
            source_data_gate.get("status")
            if isinstance(source_data_gate, dict)
            else None
        )
        source_data_policy = (
            source_data_gate.get("policy")
            if isinstance(source_data_gate, dict)
            else None
        )
        if manifest.get("figure") != figure:
            findings.append(
                {
                    "code": "MANIFEST_FIGURE_MISMATCH",
                    "figure": figure,
                    "manifest_figure": manifest.get("figure"),
                }
            )
        if run_manifest.get("figure_id") != figure:
            findings.append(
                {
                    "code": "RUN_MANIFEST_FIGURE_MISMATCH",
                    "figure": figure,
                    "run_manifest_figure": run_manifest.get("figure_id"),
                }
            )
        run = runs_by_figure.get(figure, {})
        if run.get("run_id") != run_manifest.get("run_id"):
            findings.append(
                {
                    "code": "RUN_ID_MISMATCH",
                    "figure": figure,
                    "batch_run_id": run.get("run_id"),
                    "evidence_run_id": run_manifest.get("run_id"),
                }
            )
        records[figure] = {
            "skill_version": manifest.get("skill_version"),
            "run_id": run_manifest.get("run_id"),
            "provenance": run_manifest.get("provenance"),
            "overall_release_pass": run_manifest.get("release_status", {}).get(
                "overall_release_pass"
            ),
            "live_origin_verified": manifest.get("live_origin_verified"),
            "structure_pass": manifest.get("structure_pass"),
            "visual_pass": manifest.get("visual_pass"),
            "source_geometry_group_validation": source_geometry_status,
            "subplot_worksheet_validation": subplot_worksheet_status,
            "legend_plot_reference_validation": legend_plot_reference_status,
            "plot_style_validation": plot_style_status,
            "source_data_gate": source_data_status,
            "source_data_policy": source_data_policy,
        }
        if run_manifest.get("provenance") != "live_same_run":
            findings.append({"code": "INHERITED_OR_NONLIVE_EVIDENCE", "figure": figure})
        if manifest.get("live_origin_verified") is not True:
            findings.append({"code": "LIVE_ORIGIN_NOT_VERIFIED", "figure": figure})
        if not all(
            manifest.get(name) is True for name in ("structure_pass", "visual_pass")
        ):
            findings.append({"code": "FIGURE_GATE_FAILED", "figure": figure})
        if (
            run_manifest.get("release_status", {}).get("overall_release_pass")
            is not True
        ):
            findings.append({"code": "RELEASE_STATUS_FAILED", "figure": figure})
        if source_geometry_status != "ok":
            findings.append(
                {
                    "code": "SOURCE_GEOMETRY_GROUP_FAILED",
                    "figure": figure,
                    "status": source_geometry_status,
                }
            )
        if subplot_worksheet_status != "ok":
            findings.append(
                {
                    "code": "SUBPLOT_WORKSHEET_BINDING_FAILED",
                    "figure": figure,
                    "status": subplot_worksheet_status,
                }
            )
        if legend_plot_reference_status not in {"ok", "not_required"}:
            findings.append(
                {
                    "code": "PLOT_DERIVED_LEGEND_FAILED",
                    "figure": figure,
                    "status": legend_plot_reference_status,
                }
            )
        if figure == "fig14" and plot_style_status != "ok":
            findings.append(
                {
                    "code": "PLOT_STYLE_FAILED",
                    "figure": figure,
                    "status": plot_style_status,
                }
            )
        if source_data_status != "pass" or source_data_policy not in {
            "fresh_extract",
            "validated_reuse",
            "validated_crop_reextract",
        }:
            findings.append(
                {
                    "code": "SOURCE_DATA_GATE_FAILED",
                    "figure": figure,
                    "status": source_data_status,
                    "policy": source_data_policy,
                }
            )

    versions = {record["skill_version"] for record in records.values()}
    if len(versions) != 1:
        findings.append(
            {
                "code": "SKILL_VERSION_MISMATCH",
                "versions": sorted(str(version) for version in versions),
            }
        )
    # Five manifests that all omit skill_version agree with each other, so the
    # mismatch check alone accepted a batch that stamped no version at all.
    unstamped = sorted(
        figure
        for figure, record in records.items()
        if not isinstance(record["skill_version"], str)
        or not record["skill_version"].strip()
    )
    if unstamped:
        findings.append({"code": "SKILL_VERSION_MISSING", "figures": unstamped})
    return {
        "schema": "originplot.five_figure_batch_audit.v1",
        "figures": list(FIGURES),
        "records": records,
        "shared_visible_origin_pid": next(iter(pids)) if len(pids) == 1 else None,
        "visible_window_evidence_verified": visibility_required
        and not any(item["code"].startswith("ORIGIN_WINDOW_") for item in findings),
        "findings": findings,
        "status": "pass" if not findings else "fail",
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit the five named AA2195 live Origin routes as one batch."
    )
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--require-visible-window-evidence", action="store_true")
    args = parser.parse_args()
    result = audit_batch(
        args.root, require_visible_window_evidence=args.require_visible_window_evidence
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
