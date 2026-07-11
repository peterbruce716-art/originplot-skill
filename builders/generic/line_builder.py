from __future__ import annotations

from typing import Any


def validate_plan(
    candidate: dict[str, Any],
    figure_spec: dict[str, Any] | None,
) -> dict[str, Any]:
    if figure_spec is None:
        raise ValueError("generic_line requires --figure-spec")
    if figure_spec.get("schema") != "originplot.figurespec.v5":
        raise ValueError("generic_line requires schema originplot.figurespec.v5")
    figure = figure_spec.get("figure")
    if not isinstance(figure, dict) or not str(figure.get("id", "")):
        raise ValueError("figure_spec.figure.id is required")
    plots = figure_spec.get("plots")
    layers = figure_spec.get("layers")
    data = figure_spec.get("data")
    if not isinstance(plots, list) or len(plots) != 1 or plots[0].get("type") != "line":
        raise ValueError("generic_line supports exactly one line plot")
    if not isinstance(layers, list) or len(layers) != 1:
        raise ValueError("generic_line supports exactly one layer")
    if not isinstance(data, list) or len(data) != 1:
        raise ValueError("generic_line requires exactly one data source")
    candidate_figure = candidate.get("figure")
    if candidate_figure and candidate_figure != figure["id"]:
        raise ValueError("candidate figure does not match figure_spec.figure.id")
    if candidate.get("builder_id") not in {None, "generic_line"}:
        raise ValueError("candidate builder_id does not match generic_line")
    return {
        "builder_id": "generic_line",
        "figure": figure["id"],
        "figure_class": "native_chart",
        "plot_family": "line",
        "expected_layers": 1,
        "expected_plots": 1,
        "validation": "offline_plan_validated",
        "live_implementation": "not_implemented",
    }
