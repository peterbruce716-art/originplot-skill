from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.compare_five_figure_batches import FIGURES, compare_batches, compare_figure


def _metrics(edge_f1: float, fingerprint: str = "abc123") -> dict[str, object]:
    return {
        "render_identity": {"fingerprint": fingerprint},
        "target_visual_gate": {
            "thresholds": {
                "edge_f1": ["min", 0.810],
                "mae_0_1": ["max", 0.0405],
            },
            "values": {"edge_f1": edge_f1, "mae_0_1": 0.0354},
        },
    }


def _write_batch(root: Path, metrics: dict[str, object]) -> None:
    for figure in FIGURES:
        figure_root = root / figure
        figure_root.mkdir(parents=True)
        (figure_root / "candidate_visual_metrics.json").write_text(
            json.dumps(metrics), encoding="utf-8"
        )


def test_identical_runs_are_stable() -> None:
    record = compare_figure(_metrics(0.8216), _metrics(0.8216))
    assert record["status"] == "stable"
    assert record["findings"] == []
    assert record["moved_metric_count"] == 0


def test_same_fingerprint_with_different_metrics_is_reported() -> None:
    # The real Fig12 observation: identical render identity, different pixels.
    record = compare_figure(_metrics(0.821641555), _metrics(0.811466457))
    assert record["status"] == "drifted"
    codes = {finding["code"] for finding in record["findings"]}
    assert "identity_claims_equality_but_metrics_differ" in codes
    assert record["metrics"]["edge_f1"]["delta"] < 0


def test_drift_into_the_near_threshold_band_is_reported() -> None:
    record = compare_figure(_metrics(0.900), _metrics(0.8115))
    codes = {finding["code"] for finding in record["findings"]}
    assert "near_threshold_regression" in codes
    assert record["metrics"]["edge_f1"]["candidate_near_threshold"] is True
    assert record["metrics"]["edge_f1"]["baseline_near_threshold"] is False


def test_pass_to_fail_is_a_regression() -> None:
    record = compare_figure(_metrics(0.8216), _metrics(0.5))
    assert record["status"] == "regressed"
    flip = next(f for f in record["findings"] if f["code"] == "pass_flip")
    assert flip["metric"] == "edge_f1"
    assert flip["baseline_pass"] is True
    assert flip["candidate_pass"] is False


def test_different_fingerprints_do_not_raise_the_identity_finding() -> None:
    record = compare_figure(
        _metrics(0.8216, fingerprint="aaa"), _metrics(0.8115, fingerprint="bbb")
    )
    codes = {finding["code"] for finding in record["findings"]}
    assert "identity_claims_equality_but_metrics_differ" not in codes


def test_changed_threshold_definition_is_reported() -> None:
    candidate = _metrics(0.8216)
    candidate["target_visual_gate"]["thresholds"]["edge_f1"] = ["min", 0.820]
    record = compare_figure(_metrics(0.8216), candidate)
    assert record["status"] == "drifted"
    codes = {finding["code"] for finding in record["findings"]}
    assert "threshold_definition_changed" in codes


def test_missing_figure_directory_is_incomplete_not_stable(tmp_path) -> None:
    report = compare_batches(tmp_path / "baseline", tmp_path / "candidate")
    assert report["status"] == "incomplete"
    assert all(record["status"] == "missing" for record in report["figures"].values())


def test_missing_or_empty_thresholds_make_batch_incomplete(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    metrics = _metrics(0.8216)
    _write_batch(baseline, metrics)
    _write_batch(candidate, metrics)

    for figure, thresholds in (("fig3", None), ("fig12", {})):
        path = candidate / figure / "candidate_visual_metrics.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        if thresholds is None:
            del payload["target_visual_gate"]["thresholds"]
        else:
            payload["target_visual_gate"]["thresholds"] = thresholds
        path.write_text(json.dumps(payload), encoding="utf-8")

    report = compare_batches(baseline, candidate)

    assert report["status"] == "incomplete"
    assert report["figure_status"]["fig3"] == "incomplete"
    assert report["figure_status"]["fig12"] == "incomplete"
    assert all(
        "thresholds_missing"
        in {finding["code"] for finding in report["figures"][figure]["findings"]}
        for figure in ("fig3", "fig12")
    )


def test_missing_required_metric_value_makes_batch_incomplete(tmp_path: Path) -> None:
    baseline = tmp_path / "baseline"
    candidate = tmp_path / "candidate"
    metrics = _metrics(0.8216)
    _write_batch(baseline, metrics)
    _write_batch(candidate, metrics)
    path = candidate / "fig14" / "candidate_visual_metrics.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    del payload["target_visual_gate"]["values"]["edge_f1"]
    path.write_text(json.dumps(payload), encoding="utf-8")

    report = compare_batches(baseline, candidate)

    assert report["status"] == "incomplete"
    assert report["figure_status"]["fig14"] == "incomplete"
    assert any(
        finding["code"] == "metric_missing" and finding["metric"] == "edge_f1"
        for finding in report["figures"]["fig14"]["findings"]
    )


def test_cli_default_fails_when_all_figures_are_missing(tmp_path: Path) -> None:
    script = Path(__file__).parents[1] / "scripts" / "compare_five_figure_batches.py"
    completed = subprocess.run(
        [
            sys.executable,
            str(script),
            "--baseline",
            str(tmp_path / "baseline"),
            "--candidate",
            str(tmp_path / "candidate"),
        ],
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode != 0
    assert "five-figure batch comparison: incomplete" in completed.stdout


def test_malformed_gate_payload_fails_closed() -> None:
    malformed = _metrics(0.8216)
    malformed["target_visual_gate"] = []
    record = compare_figure(_metrics(0.8216), malformed)
    assert record["status"] == "incomplete"
    assert record["findings"][0]["code"] == "visual_gate_invalid"


@pytest.mark.parametrize(
    "thresholds",
    [
        {"edge_f1": None},
        {"edge_f1": ["sideways", 0.8]},
        {"edge_f1": ["min", math.nan]},
    ],
)
def test_malformed_threshold_definition_fails_closed(
    thresholds: dict[str, object],
) -> None:
    malformed = _metrics(0.8216)
    malformed["target_visual_gate"]["thresholds"] = thresholds
    record = compare_figure(_metrics(0.8216), malformed)
    assert record["status"] == "incomplete"
    assert any(
        finding["code"] == "threshold_definition_invalid"
        for finding in record["findings"]
    )
