from __future__ import annotations

import json
from pathlib import Path

import originplot.controller as controller_module
from originplot.cli.main import main
from originplot.controller import execute
from originplot.core.profiles import resolve_profile


def test_cli_plan_with_explicit_mapping(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("A,B,C\n0,1,9\n1,2,10\n", encoding="utf-8")
    output = tmp_path / "plan.json"
    code = main(["plan", str(source), "--plot-type", "line", "--x", "A", "--y", "B", "--output", str(output)])
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["schema"] == "originplot.figurespec.v6"
    assert payload["data"]["series"][0]["x"] == "A"


def test_cli_plan_resolves_confirmed_reference_style_below_user_style(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Time,Signal\n0,1\n1,2\n", encoding="utf-8")
    reference = tmp_path / "reference-style.json"
    reference.write_text(json.dumps({"series": {"series_1": {"color": "#333333"}}, "legend": {"visible": False}, "phase": "FCC"}), encoding="utf-8")
    user_style = tmp_path / "user-style.json"
    user_style.write_text(json.dumps({"series": {"series_1": {"color": "#444444", "line_width_pt": 2.0}}}), encoding="utf-8")
    output = tmp_path / "plan.json"
    code = main(
        [
            "plan", str(source), "--plot-type", "line", "--x", "Time", "--y", "Signal",
            "--reference-style-json", str(reference), "--style-json", str(user_style), "--output", str(output),
        ]
    )
    assert code == 0
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["style"]["series"]["series_1"]["color"] == "#444444"
    assert payload["style"]["legend"]["visible"] is False
    assert any(item["path"] == "phase" for item in payload["style_audit"]["rejected"])


def test_controller_dry_run_dispatches_without_generic_line_special_case(tmp_path: Path) -> None:
    source = tmp_path / "data.csv"
    source.write_text("Category,Stress\nA,1\nB,2\n", encoding="utf-8")
    spec = tmp_path / "bar.json"
    spec.write_text(
        json.dumps(
            {
                "schema": "originplot.figurespec.v6",
                "source": {"file": str(source)},
                "data": {"series": [{"category": "Category", "y": "Stress"}]},
                "figure": {"id": "bars", "type": "bar"},
                "verification": {"profile": "quick"},
            }
        ),
        encoding="utf-8",
    )
    result = execute(profile=resolve_profile("quick"), figure_spec_path=spec, output_dir=tmp_path / "out", live=False)
    assert result["command_success"] is True
    assert result["builder"] == "bar"
    assert (tmp_path / "out" / "operation_plan.json").is_file()


def test_controller_blocks_live_heatmap_before_worker_launch(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "matrix.csv"
    source.write_text("X,Y,Z\n0,0,1\n1,0,2\n0,1,3\n1,1,4\n", encoding="utf-8")
    spec = tmp_path / "heatmap.json"
    spec.write_text(
        json.dumps(
            {
                "schema": "originplot.figurespec.v6",
                "source": {"file": str(source)},
                "data": {"matrix": {"x": "X", "y": "Y", "z": "Z"}},
                "figure": {"id": "hm", "type": "heatmap"},
                "verification": {"profile": "standard"},
            }
        ),
        encoding="utf-8",
    )

    class Decision:
        def to_dict(self):
            return {"policy": "builtin", "selected": None, "candidates": []}

    monkeypatch.setattr(controller_module, "choose_templates", lambda *args, **kwargs: Decision())

    def forbidden_worker(*_args, **_kwargs):
        raise AssertionError("live heatmap must be blocked before the Origin worker launches")

    monkeypatch.setattr(controller_module, "_run_profile_worker", forbidden_worker)
    result = execute(profile=resolve_profile("standard"), figure_spec_path=spec, output_dir=tmp_path / "out", live=True)
    assert result["command_success"] is False
    assert result["error_code"] == "E524_HEATMAP_LIVE_UNVERIFIED"
    assert result["live_origin_verified"] is False
