from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.audit_five_figure_batch import FIGURES, audit_batch
from scripts.materialize_live_evidence import json_safe
from scripts.validate_benchmark_evidence_package import REQUIRED_FILES


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _digest(payload: object) -> str:
    return hashlib.sha256(
        json.dumps(
            payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    ).hexdigest()


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _passing_batch(root: Path, *, pid: int = 4242) -> None:
    bundle_path = root / "source_bundle" / "source_bundle.json"
    bundle_path.parent.mkdir(parents=True)
    source_figures = {}
    for figure in FIGURES:
        crop_path = bundle_path.parent / f"{figure}_source.png"
        crop_path.write_bytes(f"synthetic crop for {figure}".encode("ascii"))
        data = {"method": "test_fixture", "values": [1, 2, 3]}
        source_figures[figure] = {
            "source_crop": crop_path.name,
            "source_crop_sha256": _file_hash(crop_path),
            "data": data,
            "data_sha256": _digest(data),
        }
    bundle_digest = _digest(
        {
            figure: {key: record[key] for key in ("source_crop_sha256", "data_sha256")}
            for figure, record in source_figures.items()
        }
    )
    _write(
        bundle_path,
        {
            "schema": "originplot.aa2195_fresh_source_bundle.v1",
            "fresh_extraction": True,
            "source_pdf": {"sha256": "a" * 64},
            "figures": source_figures,
            "bundle_data_sha256": bundle_digest,
        },
    )
    _write(
        root / "live_validation_status.json",
        {
            "schema": "originplot.five_figure_live_batch.v2",
            "status": "completed",
            "started_visible_origin_pid": pid,
            "fresh_output_root_verified": True,
            "source_data_policy": "fresh_extract",
            "source_bundle_manifest": str(bundle_path),
            "source_bundle_data_sha256": bundle_digest,
            "same_run_fresh_source_verified": True,
            "validated_source_data_reuse_verified": False,
            "validated_crop_reextract_verified": False,
            "runs": [
                {
                    "figure": figure,
                    "run_id": f"test-{figure}",
                    "figure_id": figure,
                    "exit_code": 0,
                    "pid_stable": True,
                    "visible_origin_pid": pid,
                }
                for figure in FIGURES
            ],
        },
    )
    for figure in FIGURES:
        candidate_hash = _digest({"figure": figure})
        gate = {
            "status": "pass",
            "policy": "fresh_extract",
            "schema": "originplot.aa2195_fresh_source_bundle.v1",
            "manifest_path": str(bundle_path),
            "manifest_sha256": _file_hash(bundle_path),
            "source_crop_sha256": source_figures[figure]["source_crop_sha256"],
            "data_sha256": source_figures[figure]["data_sha256"],
            "bundle_data_sha256": bundle_digest,
            "source_pdf_sha256": "a" * 64,
            "reuse_validation": "not_required",
        }
        _write(
            root / figure / "candidate_manifest.json",
            {
                "skill_version": "5.8.9-p18",
                "figure": figure,
                "candidate_sha256": candidate_hash,
                "live_origin_verified": True,
                "structure_pass": True,
                "visual_pass": True,
                "source_data_gate": gate,
            },
        )
        readback = {
            "figure": figure,
            "candidate_sha256": candidate_hash,
            "origin_object_readback": {
                "graphs": [{"name": figure}],
                "worksheets": [{"name": "Data", "rows": 3}],
                "project_path": str((root / figure / "candidate.opju").resolve()),
            },
            "origin_object_readback_validation": {
                "source_geometry_group_validation": {"status": "ok"},
                "subplot_worksheet_validation": {"status": "ok"},
                "legend_plot_reference_validation": {"status": "ok"},
                "plot_style_validation": {"status": "ok"},
            },
            "source_data_gate": gate,
        }
        _write(root / figure / "candidate_readback.json", readback)
        _write(
            root / figure / "evidence" / "inspection.json",
            {
                "schema": "originplot.inspection.v5",
                "run_id": f"test-{figure}",
                "figure_id": figure,
                "provenance": "live_same_run",
                "origin_object_readback": json_safe(readback["origin_object_readback"]),
                "origin_object_readback_validation": json_safe(
                    readback["origin_object_readback_validation"]
                ),
            },
        )
        _write(
            root / figure / "evidence" / "run_manifest.json",
            {
                "schema": "originplot.run_manifest.v5",
                "run_id": f"test-{figure}",
                "figure_id": figure,
                "status": "pass",
                "provenance": "live_same_run",
                "eligible_for_pass": True,
                "release_status": {"overall_release_pass": True},
            },
        )
        evidence_dir = root / figure / "evidence"
        for name in REQUIRED_FILES - {
            "run_manifest.json",
            "run_artifacts.json",
            "inspection.json",
        }:
            path = evidence_dir / name
            if name == "source_crop.png":
                path.write_bytes(
                    (bundle_path.parent / f"{figure}_source.png").read_bytes()
                )
            else:
                path.write_bytes(b"synthetic artifact")
        (root / figure / "candidate.opju").write_bytes(
            (evidence_dir / "result.opju").read_bytes()
        )
        (root / figure / "candidate_export.png").write_bytes(
            (evidence_dir / "post_reopen.png").read_bytes()
        )
        _write(
            evidence_dir / "run_artifacts.json",
            {
                "schema": "originplot.artifacts.v1",
                "run_id": f"test-{figure}",
                "figure_id": figure,
                "provenance": "live_same_run",
                "eligible_for_pass": True,
                "artifacts": [
                    {
                        "path": name,
                        "run_id": f"test-{figure}",
                        "sha256": _file_hash(evidence_dir / name),
                        "exists": True,
                        "provenance": "live_same_run",
                        "eligible_for_pass": True,
                    }
                    for name in sorted(REQUIRED_FILES - {"run_artifacts.json"})
                ],
            },
        )


@pytest.mark.parametrize(
    "mutation", ["raw_objects", "validation_flag", "figure", "candidate_hash"]
)
def test_candidate_readback_binding_rejects_mutation(
    tmp_path: Path, mutation: str
) -> None:
    _passing_batch(tmp_path)
    path = tmp_path / "fig3" / "candidate_readback.json"
    readback = json.loads(path.read_text(encoding="utf-8"))
    if mutation == "raw_objects":
        readback["origin_object_readback"] = {"graphs": [], "worksheets": []}
    elif mutation == "validation_flag":
        readback["origin_object_readback_validation"][
            "legend_plot_reference_validation"
        ]["status"] = "not_required"
    elif mutation == "figure":
        readback["figure"] = "fig16"
    else:
        readback["candidate_sha256"] = "c" * 64
    _write(path, readback)

    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(
        item["code"] == "ARTIFACT_INTEGRITY_FAILED" and item["figure"] == "fig3"
        for item in result["findings"]
    )


@pytest.mark.parametrize("value", [None, "", "a" * 63, "g" * 64, 123])
def test_candidate_readback_binding_rejects_matching_invalid_hashes(
    tmp_path: Path, value: object
) -> None:
    _passing_batch(tmp_path)
    for name in ("candidate_manifest.json", "candidate_readback.json"):
        path = tmp_path / "fig3" / name
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["candidate_sha256"] = value
        _write(path, payload)
    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(
        item["code"] == "ARTIFACT_INTEGRITY_FAILED" for item in result["findings"]
    )


@pytest.mark.parametrize("name", ["candidate_manifest.json", "candidate_readback.json"])
def test_candidate_readback_binding_requires_hash(tmp_path: Path, name: str) -> None:
    _passing_batch(tmp_path)
    path = tmp_path / "fig3" / name
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("candidate_sha256")
    _write(path, payload)
    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(
        item["code"] == "ARTIFACT_INTEGRITY_FAILED" for item in result["findings"]
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("schema", "originplot.inspection.v4"),
        ("figure_id", "fig16"),
        ("run_id", "older-run"),
        ("provenance", "inherited"),
        ("schema", None),
        ("figure_id", None),
        ("run_id", None),
        ("provenance", None),
    ],
)
def test_hashed_inspection_identity_must_match_audited_run(
    tmp_path: Path, field: str, value: object
) -> None:
    _passing_batch(tmp_path)
    evidence_dir = tmp_path / "fig3" / "evidence"
    path = evidence_dir / "inspection.json"
    inspection = json.loads(path.read_text(encoding="utf-8"))
    if value is None:
        inspection.pop(field)
    else:
        inspection[field] = value
    _write(path, inspection)
    artifacts_path = evidence_dir / "run_artifacts.json"
    artifacts = json.loads(artifacts_path.read_text(encoding="utf-8"))
    for record in artifacts["artifacts"]:
        if record["path"] == "inspection.json":
            record["sha256"] = _file_hash(path)
    _write(artifacts_path, artifacts)

    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(
        item["code"] == "ARTIFACT_INTEGRITY_FAILED"
        and "inspection identity" in item["detail"]
        for item in result["findings"]
    )


def test_inspection_hash_is_checked_before_readback_binding(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    (tmp_path / "fig3" / "evidence" / "inspection.json").write_bytes(b"not JSON")
    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(
        item["code"] == "ARTIFACT_INTEGRITY_FAILED"
        and "artifact hash or same-run provenance invalid: inspection.json"
        in item["detail"]
        for item in result["findings"]
    )


def test_candidate_readback_binding_accepts_materializer_path_normalization(
    tmp_path: Path,
) -> None:
    _passing_batch(tmp_path)
    readback = json.loads(
        (tmp_path / "fig3" / "candidate_readback.json").read_text(encoding="utf-8")
    )
    inspection = json.loads(
        (tmp_path / "fig3" / "evidence" / "inspection.json").read_text(encoding="utf-8")
    )
    assert readback["origin_object_readback"] != inspection["origin_object_readback"]
    assert (
        json_safe(readback["origin_object_readback"])
        == inspection["origin_object_readback"]
    )
    assert audit_batch(tmp_path)["status"] == "pass"


@pytest.mark.parametrize("name", ["candidate.opju", "candidate_export.png"])
@pytest.mark.parametrize("mutation", ["missing", "tampered"])
def test_published_deliverable_must_match_audited_artifact(
    tmp_path: Path, name: str, mutation: str
) -> None:
    _passing_batch(tmp_path)
    path = tmp_path / "fig3" / name
    if mutation == "missing":
        path.unlink()
    else:
        path.write_bytes(b"not the audited deliverable")
    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(
        finding["code"] == "ARTIFACT_INTEGRITY_FAILED" for finding in result["findings"]
    )


@pytest.mark.parametrize("missing", ["source_bundle_manifest", "source_data_policy"])
def test_source_contract_missing_fails_closed(tmp_path: Path, missing: str) -> None:
    _passing_batch(tmp_path)
    status_path = tmp_path / "live_validation_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload.pop(missing)
    _write(status_path, payload)
    assert audit_batch(tmp_path)["status"] == "fail"


def test_missing_source_bundle_fails_closed(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    (tmp_path / "source_bundle" / "source_bundle.json").unlink()
    assert audit_batch(tmp_path)["status"] == "fail"


@pytest.mark.parametrize(
    "field", ["fresh_output_root_verified", "same_run_fresh_source_verified"]
)
@pytest.mark.parametrize("value", [False, None, "true", 1])
def test_false_or_missing_freshness_fails_closed(
    tmp_path: Path, field: str, value: object
) -> None:
    _passing_batch(tmp_path)
    status_path = tmp_path / "live_validation_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload[field] = value
    _write(status_path, payload)
    assert audit_batch(tmp_path)["status"] == "fail"


@pytest.mark.parametrize("kind", ["crop", "data", "bundle_digest", "fresh_extraction"])
def test_tampered_source_fails_closed(tmp_path: Path, kind: str) -> None:
    _passing_batch(tmp_path)
    bundle_path = tmp_path / "source_bundle" / "source_bundle.json"
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    if kind == "crop":
        (bundle_path.parent / "fig3_source.png").write_bytes(b"tampered")
    elif kind == "data":
        payload["figures"]["fig3"]["data"]["values"][0] = 999
    elif kind == "bundle_digest":
        payload["bundle_data_sha256"] = "b" * 64
    else:
        payload["fresh_extraction"] = False
    _write(bundle_path, payload)
    assert audit_batch(tmp_path)["status"] == "fail"


def test_mixed_source_policies_fail_closed(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    for name in ("candidate_manifest.json", "candidate_readback.json"):
        path = tmp_path / "fig3" / name
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["source_data_gate"]["policy"] = "validated_reuse"
        _write(path, payload)
    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(
        item["code"] == "SOURCE_DATA_POLICY_MISMATCH" for item in result["findings"]
    )


@pytest.mark.parametrize(
    "field,value",
    [("provenance", "inherited"), ("eligible_for_pass", False), ("status", "failed")],
)
def test_per_run_fresh_provenance_fails_closed(
    tmp_path: Path, field: str, value: object
) -> None:
    _passing_batch(tmp_path)
    path = tmp_path / "fig3" / "evidence" / "run_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[field] = value
    _write(path, payload)
    assert audit_batch(tmp_path)["status"] == "fail"


@pytest.mark.parametrize(
    "kind",
    [
        "missing",
        "tampered",
        "inherited",
        "inherited_manifest",
        "wrong_run",
        "missing_record",
        "wrong_crop",
    ],
)
def test_artifact_integrity_fails_closed(tmp_path: Path, kind: str) -> None:
    _passing_batch(tmp_path)
    evidence_dir = tmp_path / "fig3" / "evidence"
    path = evidence_dir / "run_artifacts.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if kind == "missing":
        path.unlink()
    elif kind == "tampered":
        (evidence_dir / "result.opju").write_bytes(b"tampered")
    elif kind == "wrong_crop":
        (evidence_dir / "source_crop.png").write_bytes(b"unrelated crop")
        for record in payload["artifacts"]:
            if record["path"] == "source_crop.png":
                record["sha256"] = _file_hash(evidence_dir / "source_crop.png")
        _write(path, payload)
    else:
        if kind == "inherited":
            payload["artifacts"][0]["inherited_from_run"] = "older-run"
        elif kind == "inherited_manifest":
            payload["inherited_from_run"] = "older-run"
        elif kind == "wrong_run":
            payload["artifacts"][0]["run_id"] = "older-run"
        else:
            payload["artifacts"].pop()
        _write(path, payload)
    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(
        item["code"] == "ARTIFACT_INTEGRITY_FAILED" for item in result["findings"]
    )


def test_clean_batch_passes(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    assert audit_batch(tmp_path)["status"] == "pass"


def _set_reuse_policy(root: Path, policy: str) -> None:
    status_path = root / "live_validation_status.json"
    status = json.loads(status_path.read_text(encoding="utf-8"))
    bundle_path = root / "source_bundle" / "source_bundle.json"
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    reuse_path = root / "source_data_reuse.json"
    reuse = {
        "schema": "originplot.aa2195_validated_data_reuse.v1",
        "status": "ok",
        "source_bundle_manifest_sha256": _file_hash(bundle_path),
        "source_bundle_data_sha256": bundle["bundle_data_sha256"],
        "figures": {
            figure: {
                "run_id": f"prior-{figure}",
                "structure_pass": True,
                "visual_pass": True,
                "live_origin_verified": True,
                "overall_release_pass": True,
                "provenance": "live_same_run",
                "source_crop_sha256": record["source_crop_sha256"],
                "data_sha256": record["data_sha256"],
            }
            for figure, record in bundle["figures"].items()
        },
    }
    _write(reuse_path, reuse)
    if policy == "validated_crop_reextract":
        bundle.update(
            {
                "fresh_extraction": False,
                "validated_crop_reextract": True,
                "source_data_policy": policy,
                "reextracted_figures": ["fig14"],
                "parent_source_bundle_manifest_sha256": reuse[
                    "source_bundle_manifest_sha256"
                ],
                "parent_source_bundle_data_sha256": reuse["source_bundle_data_sha256"],
                "source_reuse_record_sha256": _file_hash(reuse_path),
            }
        )
        for figure, record in bundle["figures"].items():
            record["parent_data_sha256"] = record["data_sha256"]
            record["data_policy"] = policy if figure == "fig14" else "validated_reuse"
            if figure == "fig14":
                record["data"]["method"] = (
                    "fresh_source_crop_color_marker_and_component_errorbar_digitization"
                )
                record["data_sha256"] = _digest(record["data"])
        bundle["bundle_data_sha256"] = _digest(
            {
                figure: {
                    key: record[key] for key in ("source_crop_sha256", "data_sha256")
                }
                for figure, record in bundle["figures"].items()
            }
        )
        _write(bundle_path, bundle)
    status.update(
        {
            "source_data_policy": policy,
            "same_run_fresh_source_verified": False,
            "validated_source_data_reuse_verified": True,
            "validated_crop_reextract_verified": policy == "validated_crop_reextract",
            "validated_reuse_record": str(reuse_path),
            "source_bundle_data_sha256": bundle["bundle_data_sha256"],
        }
    )
    _write(status_path, status)
    for figure in FIGURES:
        for name in ("candidate_manifest.json", "candidate_readback.json"):
            path = root / figure / name
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["source_data_gate"].update(
                {
                    "policy": policy,
                    "manifest_sha256": _file_hash(bundle_path),
                    "data_sha256": bundle["figures"][figure]["data_sha256"],
                    "bundle_data_sha256": bundle["bundle_data_sha256"],
                    "reuse_validation": "pass",
                    "reuse_record_path": str(reuse_path),
                    "reuse_record_sha256": _file_hash(reuse_path),
                    "validated_run_id": f"prior-{figure}",
                    "reextracted_from_validated_crop": policy
                    == "validated_crop_reextract"
                    and figure == "fig14",
                }
            )
            payload["fresh_source_gate"] = {
                "status": "not_required",
                "policy": "validated_reuse",
            }
            _write(path, payload)


@pytest.mark.parametrize("policy", ["validated_reuse", "validated_crop_reextract"])
def test_valid_source_reuse_preserves_fresh_artifacts(
    tmp_path: Path, policy: str
) -> None:
    _passing_batch(tmp_path)
    _set_reuse_policy(tmp_path, policy)
    result = audit_batch(tmp_path)
    assert result["status"] == "pass", result["findings"]


@pytest.mark.parametrize("policy", ["validated_reuse", "validated_crop_reextract"])
def test_invalid_reuse_record_fails_closed(tmp_path: Path, policy: str) -> None:
    _passing_batch(tmp_path)
    _set_reuse_policy(tmp_path, policy)
    path = tmp_path / "source_data_reuse.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["figures"]["fig3"]["visual_pass"] = False
    _write(path, payload)
    assert audit_batch(tmp_path)["status"] == "fail"


@pytest.mark.parametrize(
    "kind",
    [
        "alias",
        "manifest_gate",
        "crop_escape",
        "bundle_escape",
        "lineage",
        "missing_crop",
        "missing_figure",
    ],
)
def test_source_evidence_contradictions_fail_closed(tmp_path: Path, kind: str) -> None:
    _passing_batch(tmp_path)
    path = tmp_path / "source_bundle" / "source_bundle.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if kind in {"alias", "manifest_gate"}:
        path = tmp_path / "fig3" / "candidate_manifest.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if kind == "alias":
            payload["fresh_source_gate"] = {
                "status": "fail",
                "policy": "validated_reuse",
            }
        else:
            payload["source_data_gate"]["data_sha256"] = "f" * 64
    elif kind == "bundle_escape":
        path = tmp_path / "live_validation_status.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["source_bundle_manifest"] = "../source_bundle.json"
    elif kind == "crop_escape":
        payload["figures"]["fig3"]["source_crop"] = "../../other.png"
    elif kind == "lineage":
        payload["parent_run"] = "old-run"
    elif kind == "missing_crop":
        (path.parent / "fig3_source.png").unlink()
    else:
        payload["figures"].pop("fig3")
    _write(path, payload)
    assert audit_batch(tmp_path)["status"] == "fail"


def test_legacy_gate_alias_requires_full_source_evidence(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    for figure in FIGURES:
        for name in ("candidate_manifest.json", "candidate_readback.json"):
            path = tmp_path / figure / name
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["fresh_source_gate"] = payload.pop("source_data_gate")
            _write(path, payload)
    assert audit_batch(tmp_path)["status"] == "pass"
    (tmp_path / "source_bundle" / "source_bundle.json").unlink()
    assert audit_batch(tmp_path)["status"] == "fail"


def test_manifest_file_hash_is_checked_even_when_data_matches(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    path = tmp_path / "source_bundle" / "source_bundle.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["created_at"] = "2020-01-01T00:00:00+00:00"
    _write(path, payload)
    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(
        item["code"] == "SOURCE_GATE_INTEGRITY_MISMATCH" for item in result["findings"]
    )


def test_invalid_primary_gate_cannot_fall_back_to_legacy_alias(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    path = tmp_path / "fig3" / "candidate_readback.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["fresh_source_gate"] = payload["source_data_gate"]
    payload["source_data_gate"] = None
    _write(path, payload)
    assert audit_batch(tmp_path)["status"] == "fail"


def test_runner_failure_verdict_is_not_ignored(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    status_path = tmp_path / "live_validation_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["status"] = "failed"
    _write(status_path, payload)

    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(f["code"] == "BATCH_STATUS_NOT_COMPLETED" for f in result["findings"])


def test_nonzero_worker_exit_is_reported(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    status_path = tmp_path / "live_validation_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["runs"][2]["exit_code"] = 1
    _write(status_path, payload)

    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    finding = next(
        f for f in result["findings"] if f["code"] == "FIGURE_WORKER_EXIT_NONZERO"
    )
    assert finding["figure"] == FIGURES[2]


def test_unstable_origin_pid_is_reported(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    status_path = tmp_path / "live_validation_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["runs"][4]["pid_stable"] = False
    _write(status_path, payload)

    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    assert any(f["code"] == "ORIGIN_PID_UNSTABLE" for f in result["findings"])


def test_batch_missing_run_fields_fails_closed(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    status_path = tmp_path / "live_validation_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    for run in payload["runs"]:
        run.pop("exit_code")
        run.pop("pid_stable")
    _write(status_path, payload)

    result = audit_batch(tmp_path)
    assert result["status"] == "fail"


def test_batch_missing_worker_run_id_fails_closed(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    status_path = tmp_path / "live_validation_status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    payload["runs"][0].pop("run_id")
    _write(status_path, payload)

    result = audit_batch(tmp_path)

    assert result["status"] == "fail"
    assert any(
        finding["code"] == "BATCH_RUN_ID_MISSING" and finding["figure"] == FIGURES[0]
        for finding in result["findings"]
    )


def test_unstamped_skill_version_is_reported(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    # Five manifests that all omit the version agree with each other, so the
    # mismatch check alone used to accept this batch.
    for figure in FIGURES:
        path = tmp_path / figure / "candidate_manifest.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload.pop("skill_version")
        _write(path, payload)

    result = audit_batch(tmp_path)
    assert result["status"] == "fail"
    finding = next(
        f for f in result["findings"] if f["code"] == "SKILL_VERSION_MISSING"
    )
    assert sorted(finding["figures"]) == sorted(FIGURES)
