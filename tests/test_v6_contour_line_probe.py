from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.probe_fig12_contour_line_state import compare, probe_project


def _readings(**values: float | None) -> dict[str, dict[str, float | None]]:
    base = {
        "layer.x.from": 250.0,
        "layer.x.to": 400.0,
        "layer.cmap.showLines": None,
        "layer.cmap.enableLines": None,
        "layer.cmap.lines": None,
        "layer.cmap.lineVisible": None,
        "layer.cmap.showLine": None,
        "layer.cmap.numLevels": None,
        "layer.cmap.numColors": 4.0,
        "layer.cmap.lineColor1": 21261142.0,
        "layer.cmap.lineColor2": 21261142.0,
        "layer.cmap.lineWidth1": 0.05,
        "layer.cmap.lineWidth2": 0.05,
        "layer.cmap.lineWidth3": 0.05,
        "layer.cmap.lineStyle1": 1.0,
        "layer.cmap.showLabels": None,
        "layer.cmap.type": 1.0,
    }
    base.update(values)
    return {"0": dict(base)}


def test_measured_origin_2022_result_is_not_recoverable() -> None:
    # Both saved projects read identically on every resolvable property even
    # though one draws three contour lines the other does not.
    report = compare(_readings(), _readings())
    assert report["probe_trustworthy"] is True
    assert report["showlines_recoverable_from_readback"] is False
    assert report["distinguishing"] == []
    assert "layer.cmap.showLines[0]" in report["unreadable"]
    assert "layer.cmap.lineWidth1[0]" in report["readable_but_identical"]


def test_a_distinguishing_property_would_be_reported() -> None:
    report = compare(
        _readings(**{"layer.cmap.showLines": 1.0}),
        _readings(**{"layer.cmap.showLines": 0.0}),
    )
    assert report["showlines_recoverable_from_readback"] is True
    finding = report["distinguishing"][0]
    assert finding["expression"] == "layer.cmap.showLines"
    assert finding["lines_on"] == 1.0
    assert finding["lines_off"] == 0.0


def test_unreadable_controls_make_the_probe_untrustworthy() -> None:
    # If layer context is wrong, every "unreadable" verdict is meaningless.
    blind = _readings(**{"layer.x.from": None, "layer.x.to": None})
    report = compare(blind, blind)
    assert report["probe_trustworthy"] is False
    assert "layer.x.from[0]" in report["control_expressions_unreadable"]


def test_different_controls_do_not_make_showlines_recoverable() -> None:
    lines_on = _readings(**{"layer.x.from": 250.0, "layer.x.to": 400.0})
    lines_off = _readings(**{"layer.x.from": 251.0, "layer.x.to": 399.0})

    report = compare(lines_on, lines_off)

    assert report["showlines_recoverable_from_readback"] is False
    assert report["distinguishing"] == []
    assert report["samples_equivalent"] is False
    assert report["probe_trustworthy"] is False
    assert [
        finding["expression"] for finding in report["control_expressions_differing"]
    ] == ["layer.x.from", "layer.x.to"]


def test_probe_project_fails_closed_when_origin_cannot_open_project(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailedOpenOrigin:
        @staticmethod
        def open(path: str, readonly: bool) -> bool:
            return False

    monkeypatch.setitem(
        sys.modules,
        "benchmarks.aa2195.builders.common_origin_utils",
        SimpleNamespace(find_graph=lambda *_: object()),
    )

    with pytest.raises(RuntimeError, match="failed to open"):
        probe_project(FailedOpenOrigin(), Path("missing.opju"), layers=0)
