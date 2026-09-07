"""Compare two five-figure live batch roots and report metric drift.

The batch audit answers "did this run pass?" but not "did this run produce the
same figure as last time?". Those are different questions: a route can keep
passing while its measured output moves, and a gate sitting at a fraction of a
percent of its budget can flip on the next machine without anything in the
recorded identity changing.

This tool answers the second question. It reports, per figure and per gated
metric, the signed drift between a baseline batch and a candidate batch, and it
raises the cases that matter:

``pass_flip``
    A metric that passed in the baseline and fails in the candidate, or vice
    versa.
``identity_claims_equality_but_metrics_differ``
    The two runs recorded the same ``render_identity.fingerprint`` -- same
    effective parameters, route, geometry version, source crop hash, Origin
    version and export profile -- yet produced different measured values. The
    fingerprint therefore does not capture everything that varies, so identical
    fingerprints must not be read as identical output.
``near_threshold_regression``
    A metric that moved closer to its threshold and now sits inside the
    near-threshold band.

Usage::

    python scripts/compare_five_figure_batches.py \
        --baseline <baseline batch root> \
        --candidate <candidate batch root> \
        [--json-out report.json]
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

try:
    from scripts.acceptance_hardening import (
        NEAR_THRESHOLD_HEADROOM_FRACTION,
        NEAR_THRESHOLD_MARGIN,
        gate_headroom_fraction,
    )
except ImportError:  # executed as `python scripts/compare_five_figure_batches.py`
    from acceptance_hardening import (
        NEAR_THRESHOLD_HEADROOM_FRACTION,
        NEAR_THRESHOLD_MARGIN,
        gate_headroom_fraction,
    )

FIGURES = ("fig3", "fig12", "fig14", "fig15", "fig16")
SCHEMA = "originplot.five_figure_batch_comparison.v1"


def _load_metrics(root: Path, figure: str) -> dict[str, Any] | None:
    path = root / figure / "candidate_visual_metrics.json"
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _is_near_threshold(direction: str, threshold: float, margin: float) -> bool:
    if margin < NEAR_THRESHOLD_MARGIN:
        return True
    return (
        gate_headroom_fraction(direction, threshold, margin)
        < NEAR_THRESHOLD_HEADROOM_FRACTION
    )


def compare_figure(
    baseline: dict[str, Any] | None, candidate: dict[str, Any] | None
) -> dict[str, Any]:
    if baseline is None or candidate is None:
        return {
            "status": "missing",
            "findings": [
                {
                    "code": "figure_metrics_missing",
                    "baseline_present": baseline is not None,
                    "candidate_present": candidate is not None,
                }
            ],
            "metrics": {},
        }

    base_gate = baseline.get("target_visual_gate")
    cand_gate = candidate.get("target_visual_gate")
    invalid_gates = [
        side
        for side, gate in (("baseline", base_gate), ("candidate", cand_gate))
        if not isinstance(gate, dict)
    ]
    if invalid_gates:
        return {
            "status": "incomplete",
            "moved_metric_count": 0,
            "baseline_fingerprint": None,
            "candidate_fingerprint": None,
            "findings": [
                {"code": "visual_gate_invalid", "side": side} for side in invalid_gates
            ],
            "metrics": {},
        }
    base_thresholds = base_gate.get("thresholds")
    cand_thresholds = cand_gate.get("thresholds")
    findings: list[dict[str, Any]] = []
    if not isinstance(base_thresholds, dict) or not base_thresholds:
        findings.append({"code": "thresholds_missing", "side": "baseline"})
    if not isinstance(cand_thresholds, dict) or not cand_thresholds:
        findings.append({"code": "thresholds_missing", "side": "candidate"})
    if findings:
        return {
            "status": "incomplete",
            "moved_metric_count": 0,
            "baseline_fingerprint": None,
            "candidate_fingerprint": None,
            "findings": findings,
            "metrics": {},
        }
    if base_thresholds != cand_thresholds:
        findings.append(
            {
                "code": "threshold_definition_changed",
                "baseline_thresholds": base_thresholds,
                "candidate_thresholds": cand_thresholds,
                "detail": "baseline and candidate use different visual-gate definitions; metric drift is not directly comparable",
            }
        )
    thresholds = cand_thresholds

    for name, spec in thresholds.items():
        valid = isinstance(spec, (list, tuple)) and len(spec) == 2
        if valid:
            direction = str(spec[0])
            try:
                threshold = float(spec[1])
            except (TypeError, ValueError):
                valid = False
            else:
                valid = direction in {"min", "max"} and math.isfinite(threshold)
        if not valid:
            findings.append(
                {
                    "code": "threshold_definition_invalid",
                    "metric": name,
                    "definition": spec,
                }
            )
    if any(finding["code"] == "threshold_definition_invalid" for finding in findings):
        return {
            "status": "incomplete",
            "moved_metric_count": 0,
            "baseline_fingerprint": None,
            "candidate_fingerprint": None,
            "findings": findings,
            "metrics": {},
        }

    metrics: dict[str, Any] = {}
    moved = 0

    for name, spec in thresholds.items():
        direction, threshold = str(spec[0]), float(spec[1])
        base_value = base_gate.get("values", {}).get(name)
        cand_value = cand_gate.get("values", {}).get(name)
        if base_value is None or cand_value is None:
            findings.append({"code": "metric_missing", "metric": name})
            continue
        base_value = float(base_value)
        cand_value = float(cand_value)
        base_margin = (
            threshold - base_value if direction == "max" else base_value - threshold
        )
        cand_margin = (
            threshold - cand_value if direction == "max" else cand_value - threshold
        )
        delta = cand_value - base_value
        if delta != 0.0:
            moved += 1

        base_pass = base_margin >= 0.0
        cand_pass = cand_margin >= 0.0
        base_near = base_pass and _is_near_threshold(direction, threshold, base_margin)
        cand_near = cand_pass and _is_near_threshold(direction, threshold, cand_margin)

        metrics[name] = {
            "direction": direction,
            "threshold": threshold,
            "baseline_value": base_value,
            "candidate_value": cand_value,
            "delta": delta,
            "baseline_margin": base_margin,
            "candidate_margin": cand_margin,
            "baseline_headroom_fraction": gate_headroom_fraction(
                direction, threshold, base_margin
            ),
            "candidate_headroom_fraction": gate_headroom_fraction(
                direction, threshold, cand_margin
            ),
            "baseline_pass": base_pass,
            "candidate_pass": cand_pass,
            "baseline_near_threshold": base_near,
            "candidate_near_threshold": cand_near,
        }

        if base_pass != cand_pass:
            findings.append(
                {
                    "code": "pass_flip",
                    "metric": name,
                    "baseline_pass": base_pass,
                    "candidate_pass": cand_pass,
                    "delta": delta,
                }
            )
        elif cand_near and not base_near:
            findings.append(
                {
                    "code": "near_threshold_regression",
                    "metric": name,
                    "delta": delta,
                    "candidate_margin": cand_margin,
                    "candidate_headroom_fraction": gate_headroom_fraction(
                        direction, threshold, cand_margin
                    ),
                }
            )

    base_fp = (baseline.get("render_identity") or {}).get("fingerprint")
    cand_fp = (candidate.get("render_identity") or {}).get("fingerprint")
    if base_fp and cand_fp and base_fp == cand_fp and moved:
        findings.append(
            {
                "code": "identity_claims_equality_but_metrics_differ",
                "fingerprint": base_fp,
                "moved_metric_count": moved,
                "detail": (
                    "identical render_identity fingerprint produced different "
                    "measured values; the fingerprint does not capture every "
                    "input that affects the export"
                ),
            }
        )

    if any(f["code"] == "metric_missing" for f in findings):
        status = "incomplete"
    elif any(f["code"] == "pass_flip" for f in findings):
        status = "regressed"
    elif findings:
        status = "drifted"
    elif moved:
        status = "drifted"
    else:
        status = "stable"

    return {
        "status": status,
        "moved_metric_count": moved,
        "baseline_fingerprint": base_fp,
        "candidate_fingerprint": cand_fp,
        "findings": findings,
        "metrics": metrics,
    }


def compare_batches(baseline_root: Path, candidate_root: Path) -> dict[str, Any]:
    figures = {
        figure: compare_figure(
            _load_metrics(baseline_root, figure), _load_metrics(candidate_root, figure)
        )
        for figure in FIGURES
    }
    statuses = {name: record["status"] for name, record in figures.items()}
    if "regressed" in statuses.values():
        overall = "regressed"
    elif any(status in {"missing", "incomplete"} for status in statuses.values()):
        overall = "incomplete"
    elif "drifted" in statuses.values():
        overall = "drifted"
    else:
        overall = "stable"
    return {
        "schema": SCHEMA,
        "baseline_root": str(baseline_root),
        "candidate_root": str(candidate_root),
        "status": overall,
        "figure_status": statuses,
        "figures": figures,
    }


def _format_report(report: dict[str, Any]) -> str:
    lines = [f"five-figure batch comparison: {report['status']}"]
    for figure, record in report["figures"].items():
        lines.append(f"  {figure}: {record['status']}")
        for finding in record["findings"]:
            lines.append(
                f"    ! {finding['code']}: {finding.get('metric', '')}".rstrip()
            )
        for name, metric in record["metrics"].items():
            if metric["delta"] == 0.0:
                continue
            lines.append(
                f"      {name:34s} {metric['baseline_value']:.9f} -> "
                f"{metric['candidate_value']:.9f} "
                f"(delta {metric['delta']:+.9f}, headroom "
                f"{metric['candidate_headroom_fraction'] * 100:.2f}%)"
            )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare two five-figure live batch roots for metric drift."
    )
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument(
        "--fail-on",
        default="regressed",
        choices=["never", "regressed", "drifted"],
        help="exit nonzero at or above this severity (default: regressed)",
    )
    args = parser.parse_args()

    report = compare_batches(args.baseline.resolve(), args.candidate.resolve())
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(_format_report(report))

    severity = {"stable": 0, "drifted": 1, "incomplete": 2, "regressed": 3}
    limit = {"never": 99, "drifted": 1, "regressed": 3}[args.fail_on]
    if report["status"] == "incomplete":
        return 1
    return 1 if severity[report["status"]] >= limit else 0


if __name__ == "__main__":
    raise SystemExit(main())
