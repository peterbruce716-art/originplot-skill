from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

_IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(_IMPORT_ROOT))

from runtime.artifact_manifest import same_run_failures, sha256_file
from scripts.build_validated_data_reuse_record import _stable_digest
from scripts.materialize_live_evidence import json_safe
from scripts.validate_benchmark_evidence_package import REQUIRED_FILES


FIGURES = ("fig3", "fig12", "fig14", "fig15", "fig16")
BATCH_SCHEMA = "originplot.five_figure_live_batch.v2"
SOURCE_POLICIES = ("fresh_extract", "validated_reuse", "validated_crop_reextract")


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


def _contained_path(base: Path, raw: Any) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise ValueError("source or artifact path is missing")
    path = (base / raw).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("source or artifact path escapes its run directory")
    return path


def _source_gate(payload: dict[str, Any]) -> Any:
    return payload.get("source_data_gate", payload.get("fresh_source_gate"))


def _audit_sources(
    root: Path, batch_status: dict[str, Any], findings: list[dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    policy = batch_status.get("source_data_policy")
    if policy not in SOURCE_POLICIES:
        findings.append({"code": "SOURCE_DATA_POLICY_INVALID", "policy": policy})
        return {}
    flags = {
        "fresh_output_root_verified": True,
        "same_run_fresh_source_verified": policy == "fresh_extract",
        "validated_source_data_reuse_verified": policy != "fresh_extract",
        "validated_crop_reextract_verified": policy == "validated_crop_reextract",
    }
    for field, expected in flags.items():
        if batch_status.get(field) is not expected:
            findings.append({"code": "SOURCE_FRESHNESS_INVALID", "field": field})
    try:
        bundle_path = _contained_path(root, batch_status.get("source_bundle_manifest"))
        if bundle_path.suffix.lower() != ".json":
            raise ValueError("source bundle must be a JSON manifest")
        bundle = _load(bundle_path)
        source_figures = bundle.get("figures")
        if not isinstance(source_figures, dict) or set(source_figures) != set(FIGURES):
            raise ValueError("source bundle figure set is incomplete")
        if bundle.get("fresh_extraction") is not (policy != "validated_crop_reextract"):
            raise ValueError("source extraction freshness contradicts its policy")
        pdf_hash = bundle.get("source_pdf", {}).get("sha256")
        if (
            not isinstance(pdf_hash, str)
            or len(pdf_hash) != 64
            or any(char not in "0123456789abcdef" for char in pdf_hash.lower())
        ):
            raise ValueError("source PDF identity hash is missing or invalid")
        candidate = {
            "source_data_policy": policy,
            "source_data_manifest": str(bundle_path),
        }
        if policy != "fresh_extract":
            reuse_path = _contained_path(
                root, batch_status.get("validated_reuse_record")
            )
            if reuse_path.suffix.lower() != ".json":
                raise ValueError("reuse record must be a JSON manifest")
            candidate["source_reuse_record"] = str(reuse_path)
        actual_digests = {}
        crop_paths = {}
        for figure, record in source_figures.items():
            if not isinstance(record, dict) or not isinstance(record.get("data"), dict):
                raise ValueError(f"source data for {figure} is missing")
            crop = _contained_path(bundle_path.parent, record.get("source_crop"))
            if crop.suffix.lower() != ".png":
                raise ValueError("source crop must be a PNG file")
            crop_paths[figure] = crop
            actual_digests[figure] = {
                "source_crop_sha256": sha256_file(crop),
                "data_sha256": _stable_digest(record["data"]),
            }
        actual_bundle_digest = _stable_digest(actual_digests)
        if any(
            actual_bundle_digest != payload.get("bundle_data_sha256")
            for payload in (
                bundle,
                {"bundle_data_sha256": batch_status.get("source_bundle_data_sha256")},
            )
        ):
            raise ValueError(
                "source bundle data or crop digest does not match actual sources"
            )
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        findings.append({"code": "SOURCE_BUNDLE_INVALID", "detail": str(exc)})
        return {}

    from scripts.origin_candidate_worker import _validate_source_data_gate

    gates = {}
    for figure in FIGURES:
        try:
            gates[figure] = _validate_source_data_gate(
                figure, candidate, bundle_path, crop_paths[figure]
            )
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            findings.append(
                {
                    "code": "SOURCE_INTEGRITY_FAILED",
                    "figure": figure,
                    "detail": str(exc),
                }
            )
    return gates


def _audit_artifacts(
    root: Path,
    figure: str,
    run_manifest: dict[str, Any],
    source_gate: dict[str, Any],
    manifest: dict[str, Any],
    readback: dict[str, Any],
) -> None:
    evidence_dir = root / figure / "evidence"
    artifacts = _load(evidence_dir / "run_artifacts.json")
    if (
        artifacts.get("schema") != "originplot.artifacts.v1"
        or artifacts.get("run_id") != run_manifest.get("run_id")
        or artifacts.get("figure_id") != figure
        or artifacts.get("provenance") != "live_same_run"
        or artifacts.get("eligible_for_pass") is not True
        or artifacts.get("inherited_from_run")
        or same_run_failures(artifacts)
    ):
        raise ValueError("artifact manifest is not fresh same-run evidence")
    records = artifacts.get("artifacts")
    if not isinstance(records, list) or not records:
        raise ValueError("artifact records are missing")
    required = {
        (evidence_dir / name).resolve()
        for name in REQUIRED_FILES - {"run_artifacts.json"}
    }
    paths = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("invalid artifact record")
        raw = record.get("path")
        path = _contained_path(evidence_dir, raw)
        if path not in required:
            raise ValueError("unexpected artifact path")
        if path in paths:
            raise ValueError("duplicate artifact path")
        paths.add(path)
        if (
            record.get("run_id") != run_manifest.get("run_id")
            or record.get("provenance") != "live_same_run"
            or record.get("eligible_for_pass") is not True
            or record.get("exists") is not True
            or record.get("sha256") != sha256_file(path)
        ):
            raise ValueError(f"artifact hash or same-run provenance invalid: {raw}")
    if not required.issubset(paths):
        raise ValueError("required artifact records are missing")
    published_artifacts = {
        "candidate.opju": "result.opju",
        "candidate_export.png": "post_reopen.png",
    }
    for published_name, evidence_name in published_artifacts.items():
        published = _contained_path(root / figure, published_name)
        if not published.is_file() or sha256_file(published) != sha256_file(
            evidence_dir / evidence_name
        ):
            raise ValueError(
                f"published deliverable does not match audited evidence: {published_name}"
            )
    if sha256_file(evidence_dir / "source_crop.png") != source_gate.get(
        "source_crop_sha256"
    ):
        raise ValueError("evidence source crop does not match the source bundle")
    inspection = _load(evidence_dir / "inspection.json")
    if (
        inspection.get("schema") != "originplot.inspection.v5"
        or inspection.get("figure_id") != figure
        or inspection.get("run_id") != run_manifest.get("run_id")
        or inspection.get("provenance") != "live_same_run"
        or inspection.get("provenance") != run_manifest.get("provenance")
    ):
        raise ValueError("inspection identity does not match the audited run")
    if readback.get("figure") != figure:
        raise ValueError("candidate readback figure does not match the audited figure")
    for payload in (manifest, readback):
        candidate_hash = payload.get("candidate_sha256")
        if (
            not isinstance(candidate_hash, str)
            or re.fullmatch(r"[0-9a-fA-F]{64}", candidate_hash) is None
        ):
            raise ValueError("candidate identity requires a valid SHA256 hash")
    if readback["candidate_sha256"] != manifest["candidate_sha256"]:
        raise ValueError("candidate readback hash does not match the manifest")
    for field in ("origin_object_readback", "origin_object_readback_validation"):
        if (
            field not in readback
            or field not in inspection
            or json_safe(readback[field]) != inspection[field]
        ):
            raise ValueError(
                f"candidate readback does not match hashed inspection: {field}"
            )


def audit_batch(
    root: Path, *, require_visible_window_evidence: bool = False
) -> dict[str, Any]:
    root = Path(root).resolve()
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
    source_gates = _audit_sources(root, batch_status, findings)
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
        source_data_gate = _source_gate(readback)
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
        if source_data_policy != batch_status.get("source_data_policy"):
            findings.append({"code": "SOURCE_DATA_POLICY_MISMATCH", "figure": figure})
        expected_gate = source_gates.get(figure)
        for name, payload in (("manifest", manifest), ("readback", readback)):
            gate = _source_gate(payload)
            matches = isinstance(gate, dict) and expected_gate is not None
            if matches:
                try:
                    gate = dict(gate)
                    gate["manifest_path"] = str(
                        _contained_path(root, gate.get("manifest_path"))
                    )
                    if "reuse_record_path" in expected_gate:
                        gate["reuse_record_path"] = str(
                            _contained_path(root, gate.get("reuse_record_path"))
                        )
                    matches = all(
                        gate.get(key) == value for key, value in expected_gate.items()
                    )
                except (OSError, ValueError, TypeError):
                    matches = False
            if not matches:
                findings.append(
                    {
                        "code": "SOURCE_GATE_INTEGRITY_MISMATCH",
                        "figure": figure,
                        "evidence": name,
                    }
                )
            alias = payload.get("fresh_source_gate")
            if "source_data_gate" in payload and alias is not None:
                if (
                    batch_status.get("source_data_policy") == "fresh_extract"
                    and alias != payload["source_data_gate"]
                ):
                    findings.append(
                        {
                            "code": "SOURCE_GATE_ALIAS_MISMATCH",
                            "figure": figure,
                            "evidence": name,
                        }
                    )
        if (
            run_manifest.get("status") != "pass"
            or run_manifest.get("eligible_for_pass") is not True
            or run_manifest.get("inherited_from_run")
        ):
            findings.append({"code": "RUN_FRESH_PROVENANCE_INVALID", "figure": figure})
        try:
            _audit_artifacts(
                root, figure, run_manifest, expected_gate or {}, manifest, readback
            )
        except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
            findings.append(
                {
                    "code": "ARTIFACT_INTEGRITY_FAILED",
                    "figure": figure,
                    "detail": str(exc),
                }
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
