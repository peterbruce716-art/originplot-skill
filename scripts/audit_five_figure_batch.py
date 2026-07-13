from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FIGURES = ("fig3", "fig12", "fig14", "fig15", "fig16")


def _load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def audit_batch(root: Path) -> dict[str, Any]:
    root = Path(root)
    findings: list[dict[str, Any]] = []
    records: dict[str, dict[str, Any]] = {}
    status_path = root / "live_validation_status.json"
    if not status_path.exists():
        findings.append({"code": "MISSING_BATCH_STATUS", "path": status_path.name})
        batch_status: dict[str, Any] = {}
    else:
        batch_status = _load(status_path)

    runs = batch_status.get("runs")
    runs_by_figure = {str(item.get("figure")): item for item in runs if isinstance(item, dict)} if isinstance(runs, list) else {}
    pids = {item.get("visible_origin_pid") for item in runs_by_figure.values() if item.get("visible_origin_pid") is not None}
    if len(runs_by_figure) != len(FIGURES) or set(runs_by_figure) != set(FIGURES):
        findings.append({"code": "BATCH_FIGURE_SET_INCOMPLETE", "figures": sorted(runs_by_figure)})
    if len(pids) != 1:
        findings.append({"code": "ORIGIN_PID_NOT_SHARED", "visible_origin_pids": sorted(str(pid) for pid in pids)})
    for figure in FIGURES:
        manifest_path = root / figure / "candidate_manifest.json"
        readback_path = root / figure / "candidate_readback.json"
        run_manifest_path = root / figure / "evidence" / "run_manifest.json"
        if not manifest_path.exists() or not readback_path.exists() or not run_manifest_path.exists():
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
        records[figure] = {
            "skill_version": manifest.get("skill_version"),
            "run_id": run_manifest.get("run_id"),
            "provenance": run_manifest.get("provenance"),
            "overall_release_pass": run_manifest.get("release_status", {}).get("overall_release_pass"),
            "live_origin_verified": manifest.get("live_origin_verified"),
            "structure_pass": manifest.get("structure_pass"),
            "visual_pass": manifest.get("visual_pass"),
            "source_geometry_group_validation": source_geometry_status,
            "subplot_worksheet_validation": subplot_worksheet_status,
            "legend_plot_reference_validation": legend_plot_reference_status,
            "plot_style_validation": plot_style_status,
        }
        if run_manifest.get("provenance") != "live_same_run":
            findings.append({"code": "INHERITED_OR_NONLIVE_EVIDENCE", "figure": figure})
        if manifest.get("live_origin_verified") is not True:
            findings.append({"code": "LIVE_ORIGIN_NOT_VERIFIED", "figure": figure})
        if not all(manifest.get(name) is True for name in ("structure_pass", "visual_pass")):
            findings.append({"code": "FIGURE_GATE_FAILED", "figure": figure})
        if run_manifest.get("release_status", {}).get("overall_release_pass") is not True:
            findings.append({"code": "RELEASE_STATUS_FAILED", "figure": figure})
        if source_geometry_status != "ok":
            findings.append({"code": "SOURCE_GEOMETRY_GROUP_FAILED", "figure": figure, "status": source_geometry_status})
        if subplot_worksheet_status != "ok":
            findings.append({"code": "SUBPLOT_WORKSHEET_BINDING_FAILED", "figure": figure, "status": subplot_worksheet_status})
        if legend_plot_reference_status not in {"ok", "not_required"}:
            findings.append({"code": "PLOT_DERIVED_LEGEND_FAILED", "figure": figure, "status": legend_plot_reference_status})
        if figure == "fig14" and plot_style_status != "ok":
            findings.append({"code": "PLOT_STYLE_FAILED", "figure": figure, "status": plot_style_status})

    versions = {record["skill_version"] for record in records.values()}
    if len(versions) != 1:
        findings.append({"code": "SKILL_VERSION_MISMATCH", "versions": sorted(str(version) for version in versions)})
    return {
        "schema": "originplot.five_figure_batch_audit.v1",
        "figures": list(FIGURES),
        "records": records,
        "shared_visible_origin_pid": next(iter(pids)) if len(pids) == 1 else None,
        "findings": findings,
        "status": "pass" if not findings else "fail",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the five named AA2195 live Origin routes as one batch.")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = audit_batch(args.root)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
