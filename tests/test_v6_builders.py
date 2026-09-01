from __future__ import annotations

from pathlib import Path

import pytest

from originplot.builders import compile_figure, list_builders
from originplot.core.errors import OriginPlotError
from originplot.spec.io import normalize_figure_spec

EXPECTED = {
    "line",
    "scatter",
    "line_scatter",
    "errorbar",
    "bar",
    "grouped_bar",
    "stacked_bar",
    "heatmap",
    "contour",
    "multi_panel",
}


def _source(tmp_path: Path) -> Path:
    path = tmp_path / "data.csv"
    path.write_text("X,Y,E,Category,Z,Label,Group\n0,1,0.1,A,2,p1,g1\n1,2,0.2,B,3,p2,g2\n", encoding="utf-8")
    return path


def _spec(tmp_path: Path, plot_type: str):
    source = _source(tmp_path)
    if plot_type in {"heatmap", "contour"}:
        data = {"matrix": {"x": "X", "y": "Y", "z": "Z"}}
    elif plot_type in {"bar", "grouped_bar", "stacked_bar"}:
        data = {"series": [{"id": "s1", "category": "Category", "y": "Y"}]}
    else:
        series = {"id": "s1", "x": "X", "y": "Y"}
        if plot_type == "errorbar":
            series["y_error"] = "E"
        data = {"series": [series]}
    return normalize_figure_spec(
        {"schema": "originplot.figurespec.v6", "source": {"file": str(source)}, "data": data, "figure": {"id": "f", "type": plot_type}},
        tmp_path,
    )


def test_registry_exposes_exact_v6_primitives() -> None:
    assert set(list_builders()) == EXPECTED


def test_all_non_composite_primitives_compile_without_origin(tmp_path: Path) -> None:
    for plot_type in sorted(EXPECTED - {"multi_panel"}):
        plan = compile_figure(_spec(tmp_path, plot_type))
        assert plan.plot_type == plot_type
        assert plan.operations
        assert all("originpro" not in repr(item).lower() for item in plan.operations)


def test_xy_builder_rejects_unimplemented_label_mapping(tmp_path: Path) -> None:
    source = _source(tmp_path)
    spec = normalize_figure_spec(
        {
            "schema": "originplot.figurespec.v6",
            "source": {"file": str(source)},
            "data": {"series": [{"id": "s1", "x": "X", "y": "Y", "label": "Label"}]},
            "figure": {"id": "f", "type": "scatter"},
        },
        tmp_path,
    )
    with pytest.raises(OriginPlotError, match="label mapping is not executable"):
        compile_figure(spec)


def test_bar_builder_rejects_unimplemented_group_or_label_mapping(tmp_path: Path) -> None:
    source = _source(tmp_path)
    spec = normalize_figure_spec(
        {
            "schema": "originplot.figurespec.v6",
            "source": {"file": str(source)},
            "data": {"series": [{"id": "s1", "category": "Category", "y": "Y", "group": "Group", "label": "Label"}]},
            "figure": {"id": "f", "type": "grouped_bar"},
        },
        tmp_path,
    )
    with pytest.raises(OriginPlotError, match="group/label mapping is not executable"):
        compile_figure(spec)


def test_multi_panel_reuses_child_builders(tmp_path: Path) -> None:
    source = _source(tmp_path)
    spec = normalize_figure_spec(
        {
            "schema": "originplot.figurespec.v6",
            "source": {"file": str(source)},
            "data": {},
            "figure": {
                "id": "multi",
                "type": "multi_panel",
                "panels": [
                    {"id": "a", "data": {"series": [{"x": "X", "y": "Y"}]}, "figure": {"type": "line"}},
                    {"id": "b", "data": {"series": [{"category": "Category", "y": "Y"}]}, "figure": {"type": "bar"}},
                ],
            },
        },
        tmp_path,
    )
    plan = compile_figure(spec)
    assert plan.plot_type == "multi_panel"
    assert sum(1 for item in plan.operations if item["op"] == "create_graph") == 1
    assert {item.get("layer") for item in plan.operations if item["op"] in {"add_xy_plot", "add_bar_plot"}} == {0, 1}
