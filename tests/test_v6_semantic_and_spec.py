from __future__ import annotations

import json
from pathlib import Path

import pytest

from originplot.core.errors import OriginPlotError
from originplot.semantic import inspect_table
from originplot.semantic.plan import build_figurespec
from originplot.semantic.recommend import recommend_plots
from originplot.spec import FIGURE_SPEC_SCHEMA, load_figure_spec, normalize_figure_spec


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


def test_handwritten_figurespec_rejects_non_executable_style(tmp_path: Path) -> None:
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
                "style": {"theme": "publication", "series": {"s1": {"symbol_size_pt": 8}}},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(OriginPlotError, match="style field.*not executable"):
        load_figure_spec(spec_path)


def test_handwritten_figurespec_normalizes_supported_style(tmp_path: Path) -> None:
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
                "style": {"legend": {"visible": True, "frame": False}, "series": {"s1": {"color": "red", "line_width_pt": 1.5}}},
            }
        ),
        encoding="utf-8",
    )
    spec = load_figure_spec(spec_path)
    assert spec.style == {"legend": {"visible": True, "frame": False}, "series": {"s1": {"color": "red", "line_width_pt": 1.5}}}
    assert spec.to_dict()["style"] == spec.style


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


def _manual_payload(source: Path) -> dict:
    return {
        "schema": FIGURE_SPEC_SCHEMA,
        "source": {"file": str(source)},
        "data": {"series": [{"id": "s1", "x": "Time", "y": "Intensity"}]},
        "figure": {"id": "demo", "type": "line"},
    }


def test_axis_contract_rejects_fields_the_adapter_does_not_execute(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Intensity\n0,1\n1,2\n", encoding="utf-8")
    payload = _manual_payload(source)
    payload["figure"]["x_axis"] = {"title": "Time", "unit": "s", "scale": "log"}
    with pytest.raises(OriginPlotError, match="E342_AXIS_CONTRACT_INVALID.*x_axis.scale"):
        normalize_figure_spec(payload, tmp_path)


def test_axis_unit_without_title_is_rejected_instead_of_ignored(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Intensity\n0,1\n1,2\n", encoding="utf-8")
    payload = _manual_payload(source)
    payload["figure"]["x_axis"] = {"unit": "s"}
    with pytest.raises(OriginPlotError, match="E342_AXIS_CONTRACT_INVALID.*unit requires title"):
        normalize_figure_spec(payload, tmp_path)


def test_page_geometry_requires_width_and_height_together(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Intensity\n0,1\n1,2\n", encoding="utf-8")
    payload = _manual_payload(source)
    payload["layout"] = {"page": {"width_cm": 18.0}}
    with pytest.raises(OriginPlotError, match="E343_LAYOUT_CONTRACT_INVALID.*width_cm and height_cm"):
        normalize_figure_spec(payload, tmp_path)


def test_verification_hard_gates_cannot_be_disabled(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Intensity\n0,1\n1,2\n", encoding="utf-8")
    payload = _manual_payload(source)
    payload["verification"] = {"profile": "standard", "require_reopen": False}
    with pytest.raises(OriginPlotError, match="E344_VERIFICATION_CONTRACT_INVALID.*require_reopen"):
        normalize_figure_spec(payload, tmp_path)


def test_unknown_verification_fields_are_rejected(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Intensity\n0,1\n1,2\n", encoding="utf-8")
    payload = _manual_payload(source)
    payload["verification"] = {"profile": "standard", "skip_binding": True}
    with pytest.raises(OriginPlotError, match="E344_VERIFICATION_CONTRACT_INVALID.*skip_binding"):
        normalize_figure_spec(payload, tmp_path)


def test_verification_contract_is_canonicalized_to_non_weakenable_gates(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Intensity\n0,1\n1,2\n", encoding="utf-8")
    spec = normalize_figure_spec(_manual_payload(source), tmp_path)
    assert spec.verification == {
        "profile": "standard",
        "require_reopen": True,
        "require_binding_readback": True,
        "require_origin_export": True,
    }
    assert spec.to_dict()["verification"] == spec.verification


def test_multi_panel_child_style_and_axis_use_the_same_contracts(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Intensity\n0,1\n1,2\n", encoding="utf-8")
    payload = {
        "schema": FIGURE_SPEC_SCHEMA,
        "source": {"file": str(source)},
        "data": {},
        "figure": {
            "id": "multi",
            "type": "multi_panel",
            "panels": [
                {
                    "id": "a",
                    "data": {"series": [{"id": "s1", "x": "Time", "y": "Intensity"}]},
                    "figure": {"type": "line", "x_axis": {"title": "Time", "scale": "log"}},
                    "style": {"series": {"s1": {"symbol_size_pt": 8}}},
                },
                {
                    "id": "b",
                    "data": {"series": [{"id": "s2", "x": "Time", "y": "Intensity"}]},
                    "figure": {"type": "scatter"},
                },
            ],
        },
    }
    with pytest.raises(OriginPlotError, match="E342_AXIS_CONTRACT_INVALID.*panels.0.*x_axis.scale"):
        normalize_figure_spec(payload, tmp_path)


def test_multi_panel_child_layout_is_rejected_while_it_is_not_compiled(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Intensity\n0,1\n1,2\n", encoding="utf-8")
    payload = {
        "schema": FIGURE_SPEC_SCHEMA,
        "source": {"file": str(source)},
        "data": {},
        "figure": {
            "id": "multi",
            "type": "multi_panel",
            "panels": [
                {
                    "data": {"series": [{"x": "Time", "y": "Intensity"}]},
                    "figure": {"type": "line"},
                    "layout": {"page": {"width_cm": 9.0, "height_cm": 6.0}},
                },
                {
                    "data": {"series": [{"x": "Time", "y": "Intensity"}]},
                    "figure": {"type": "scatter"},
                },
            ],
        },
    }
    with pytest.raises(OriginPlotError, match="E343_LAYOUT_CONTRACT_INVALID.*panel-specific layout"):
        normalize_figure_spec(payload, tmp_path)
