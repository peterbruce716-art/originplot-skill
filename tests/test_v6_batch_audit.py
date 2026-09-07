from __future__ import annotations

import json
from pathlib import Path

from scripts.audit_five_figure_batch import FIGURES, audit_batch


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _passing_batch(root: Path, *, pid: int = 4242) -> None:
    _write(
        root / "live_validation_status.json",
        {
            "schema": "originplot.five_figure_live_batch.v2",
            "status": "completed",
            "started_visible_origin_pid": pid,
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
        _write(
            root / figure / "candidate_manifest.json",
            {
                "skill_version": "5.8.9-p18",
                "figure": figure,
                "live_origin_verified": True,
                "structure_pass": True,
                "visual_pass": True,
            },
        )
        _write(
            root / figure / "candidate_readback.json",
            {
                "origin_object_readback_validation": {
                    "source_geometry_group_validation": {"status": "ok"},
                    "subplot_worksheet_validation": {"status": "ok"},
                    "legend_plot_reference_validation": {"status": "ok"},
                    "plot_style_validation": {"status": "ok"},
                },
                "source_data_gate": {"status": "pass", "policy": "fresh_extract"},
            },
        )
        _write(
            root / figure / "evidence" / "run_manifest.json",
            {
                "run_id": f"test-{figure}",
                "figure_id": figure,
                "provenance": "live_same_run",
                "release_status": {"overall_release_pass": True},
            },
        )


def test_clean_batch_passes(tmp_path: Path) -> None:
    _passing_batch(tmp_path)
    assert audit_batch(tmp_path)["status"] == "pass"


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
