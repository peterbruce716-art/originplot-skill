from __future__ import annotations

from scripts.acceptance_hardening import (
    NEAR_THRESHOLD_HEADROOM_FRACTION,
    NEAR_THRESHOLD_MARGIN,
    evaluate_target_visual_gate,
    gate_headroom_fraction,
)

# Real Fig12 values from the same-run administrator Origin 2022 baseline batch.
# edge_score clears its 0.745 floor by 0.001058, which is above the absolute
# 0.001 margin and therefore used to be reported as comfortably safe.
FIG12_BASELINE = {
    "mae_0_1": 0.0354192890226841,
    "ssim_score": 0.8012330532073975,
    "layout_score": 0.9924307821875987,
    "edge_score": 0.7460580989718437,
    "color_score": 0.9750876426696777,
    "foreground_f1": 0.9813438266175751,
    "edge_f1": 0.8216415546923588,
    "nonwhite_delta": 0.005587956627013391,
    "registration_shift": {"dx_px": -1.0, "dy_px": -0.5},
    "source_content_bbox": [0, 0, 100, 100],
    "actual_content_bbox": [0, 0, 100, 102],
}


def test_headroom_is_relative_to_each_gate_budget() -> None:
    # min gate: budget is 1 - threshold
    assert gate_headroom_fraction("min", 0.745, 0.001058) == 0.001058 / 0.255
    # max gate: budget is the threshold itself
    assert gate_headroom_fraction("max", 6.0, 0.5) == 0.5 / 6.0
    # zero-tolerance gate has no headroom by definition, and must not divide by zero
    assert gate_headroom_fraction("max", 0.0, 0.0) == 0.0


def test_razor_thin_edge_score_is_reported_near_threshold() -> None:
    gate = evaluate_target_visual_gate("fig12", FIG12_BASELINE)

    assert gate["visual_baseline_promoted"] is True
    assert gate["checks"]["edge_score"] is True

    # The absolute margin alone would have hidden this gate.
    assert gate["gate_margins"]["edge_score"] > NEAR_THRESHOLD_MARGIN
    assert (
        gate["gate_headroom_fractions"]["edge_score"] < NEAR_THRESHOLD_HEADROOM_FRACTION
    )
    assert "edge_score" in gate["near_threshold_metrics"]


def test_near_threshold_reporting_never_changes_pass_or_fail() -> None:
    gate = evaluate_target_visual_gate("fig12", FIG12_BASELINE)
    assert gate["failures"] == []
    assert gate["visual_baseline_status"] == "promoted"

    failing = dict(FIG12_BASELINE, edge_score=0.5)
    failed_gate = evaluate_target_visual_gate("fig12", failing)
    assert failed_gate["failures"] == ["edge_score"]
    assert failed_gate["visual_baseline_promoted"] is False
    # A failing metric is a failure, not a near-threshold advisory.
    assert "edge_score" not in failed_gate["near_threshold_metrics"]


def test_comfortable_metric_is_not_flagged() -> None:
    gate = evaluate_target_visual_gate("fig12", FIG12_BASELINE)
    # layout_score clears 0.942 by 0.050 on a 0.058 budget: genuinely safe.
    assert (
        gate["gate_headroom_fractions"]["layout_score"]
        > NEAR_THRESHOLD_HEADROOM_FRACTION
    )
    assert "layout_score" not in gate["near_threshold_metrics"]


def test_zero_tolerance_bar_boundary_gates_stay_flagged() -> None:
    metrics = {
        "mae_0_1": 0.045066,
        "ssim_score": 0.792995,
        "layout_score": 0.987722,
        "edge_score": 0.676016,
        "color_score": 0.986775,
        "foreground_f1": 0.987996,
        "edge_f1": 0.942612,
        "nonwhite_delta": 0.048330,
        "registration_shift": {"dx_px": 2.5, "dy_px": 0.0},
        "source_content_bbox": [0, 0, 100, 100],
        "actual_content_bbox": [0, 0, 100, 100],
        "fig16_bar_boundary_max_error_px": 1.0,
        "fig16_bar_boundary_mean_error_px": 0.47619047619047616,
        "fig16_bar_boundary_missing_segments": 0,
    }
    gate = evaluate_target_visual_gate(
        "fig16", metrics, fig16_frozen_identity_recognized=True
    )
    assert gate["visual_baseline_promoted"] is True
    # Both were flagged before the relative rule and must remain flagged.
    assert "fig16_bar_boundary_max_error_px" in gate["near_threshold_metrics"]
    assert "fig16_bar_boundary_missing_segments" in gate["near_threshold_metrics"]
