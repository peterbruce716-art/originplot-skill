from __future__ import annotations

import json
from pathlib import Path

import pytest

from originplot.core.errors import OriginPlotError
from originplot.semantic import inspect_table
from originplot.semantic.plan import build_figurespec
from originplot.semantic.recommend import recommend_plots
from originplot.spec import FIGURE_SPEC_SCHEMA, load_figure_spec


def test_semantic_inspection_is_conservative(tmp_path: Path) -> None:
    source = tmp_path / "stress.csv"
    source.write_text("Strain (%),Stress (MPa),Stress SD,Mystery\n0,100,2,9\n1,120,3,10\n", encoding="utf-8")
    result = inspect_table(source)
    roles = {item["name"]: item["role"] for item in result["columns"]}
    assert roles["Strain (%)"] == "x"
    assert roles["Stress (MPa)"] == "y"
    assert roles["Stress SD"] == "y_error"
    assert roles["Mystery"] == "uncertain"
    assert result["recommended_plots"][0] == "errorbar"


def test_figurespec_v6_freezes_source_hash_and_mapping(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Intensity\n0,1\n1,2\n", encoding="utf-8")
    spec_path = tmp_path / "figure.json"
    spec_path.write_text(
        json.dumps(
            {
                "schema": FIGURE_SPEC_SCHEMA,
                "source": {"file": "data.csv"},
                "data": {"series": [{"id": "s1", "x": "Time", "y": "Intensity"}]},
                "figure": {"id": "demo", "type": "line"},
                "verification": {"profile": "standard"},
            }
        ),
        encoding="utf-8",
    )
    spec = load_figure_spec(spec_path)
    assert len(spec.source_hash) == 64
    assert spec.plot_type == "line"
    assert spec.data["series"][0]["y"] == "Intensity"


def test_figurespec_rejects_missing_columns(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Intensity\n0,1\n1,2\n", encoding="utf-8")
    spec_path = tmp_path / "figure.json"
    spec_path.write_text(
        json.dumps(
            {
                "schema": FIGURE_SPEC_SCHEMA,
                "source": {"file": "data.csv"},
                "data": {"series": [{"id": "s1", "x": "Time", "y": "Missing"}]},
                "figure": {"type": "line"},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(OriginPlotError, match="required columns not found"):
        load_figure_spec(spec_path)


def test_grouped_bar_auto_planning_uses_all_wide_y_columns(tmp_path: Path) -> None:
    source = tmp_path / "wide.csv"
    source.write_text("Category,Signal A,Signal B\nA,1,2\nB,3,4\n", encoding="utf-8")
    result = build_figurespec(source)
    assert result["figure"]["type"] == "grouped_bar"
    assert [series["y"] for series in result["data"]["series"]] == ["Signal A", "Signal B"]
    assert all(series["category"] == "Category" for series in result["data"]["series"])


def test_long_form_group_is_not_silently_recommended_as_grouped_bar() -> None:
    understanding = {
        "columns": [
            {"name": "Category", "role": "category"},
            {"name": "Condition", "role": "group"},
            {"name": "Signal", "role": "y"},
        ]
    }
    recommendations = recommend_plots(understanding)
    assert "grouped_bar" not in recommendations
    assert "stacked_bar" not in recommendations
    assert "bar" not in recommendations


def test_explicit_long_form_grouped_bar_requires_manual_series_mapping(tmp_path: Path) -> None:
    source = tmp_path / "long.csv"
    source.write_text("Category,Condition,Signal\nA,control,1\nA,treated,2\nB,control,3\nB,treated,4\n", encoding="utf-8")
    with pytest.raises(OriginPlotError, match="long-form grouped/stacked bar"):
        build_figurespec(source, plot_type="grouped_bar")
