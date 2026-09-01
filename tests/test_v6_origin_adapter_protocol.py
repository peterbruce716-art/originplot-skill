from __future__ import annotations

import json
from pathlib import Path

import pytest

from originplot.adapters.originpro import (
    _add_matrix,
    _add_xy,
    _all_exports_nonblank,
    _live_origin_verified,
    _set_legend,
    _template_for,
    _validate_operation_names,
)
from originplot.operation_plan import OperationPlan
from originplot.runtime.protocol import WORKER_TASK_SCHEMA, build_worker_task
from originplot.runtime.worker import run


def test_worker_protocol_carries_declarative_plan(tmp_path: Path) -> None:
    plan = OperationPlan(
        figure_id="demo",
        plot_type="line",
        source={"path": str(tmp_path / "data.csv"), "hash": "x"},
        profile="standard",
        operations=({"op": "create_graph", "name": "demo", "layers": 1},),
    )
    task = build_worker_task(
        profile={"name": "standard"},
        figure_spec=str(tmp_path / "figure.json"),
        output_dir=tmp_path / "out",
        operation_plan=plan.to_dict(),
    )
    assert task["schema"] == WORKER_TASK_SCHEMA
    assert task["worker_privilege"] == "administrator_required_for_origin"
    assert task["operation_plan"]["plot_type"] == "line"


def test_worker_fails_before_origin_when_not_elevated(tmp_path: Path) -> None:
    plan = OperationPlan(
        figure_id="demo",
        plot_type="line",
        source={"path": str(tmp_path / "data.csv")},
        profile="standard",
        operations=(),
    )
    task = build_worker_task(
        profile={"name": "standard"},
        figure_spec=str(tmp_path / "figure.json"),
        output_dir=tmp_path / "out",
        operation_plan=plan.to_dict(),
    )
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(task), encoding="utf-8")
    result = run(task_path, admin_check=lambda: False)
    assert result["error_code"] == "E120_ENVIRONMENT_MISMATCH"
    assert result["origin_attach_not_attempted"] is True


def test_adapter_rejects_unknown_operation_before_origin_execution() -> None:
    plan = OperationPlan(
        figure_id="demo",
        plot_type="line",
        source={"path": "data.csv"},
        profile="standard",
        operations=(
            {"op": "create_workbook"},
            {"op": "create_graph", "layers": 1},
            {"op": "add_xy_plot", "mapping": {"x": "X", "y": "Y"}},
            {"op": "set_axes"},
            {"op": "set_legend"},
            {"op": "set_page"},
            {"op": "export"},
            {"op": "typo_silent_operation"},
        ),
    )
    with pytest.raises(RuntimeError, match="E520_OPERATION_PLAN_INVALID.*typo_silent_operation"):
        _validate_operation_names(plan)


def test_live_origin_verified_requires_every_gate() -> None:
    passing = {"save": "pass", "reopen": "pass", "binding": "pass", "export": "pass"}
    assert _live_origin_verified(passing) is True
    failing = dict(passing)
    failing["binding"] = "failed"
    assert _live_origin_verified(failing) is False


def test_adapter_uses_reusable_selected_template_path() -> None:
    plan = OperationPlan(
        figure_id="demo",
        plot_type="line",
        source={"path": "data.csv"},
        profile="standard",
        metadata={"template_decision": {"selected": {"path": r"C:\\Templates\\paper.otpu", "reusable": True}}},
    )
    assert _template_for(plan) == r"C:\\Templates\\paper.otpu"


def test_adapter_falls_back_when_template_has_no_reusable_path() -> None:
    plan = OperationPlan(
        figure_id="demo",
        plot_type="stacked_bar",
        source={"path": "data.csv"},
        profile="standard",
        metadata={"template_decision": {"selected": {"detail_url": "https://example.invalid", "reusable": False}}},
    )
    assert _template_for(plan) == "COLUMN"


def test_export_gate_requires_png_pdf_and_tif(tmp_path: Path) -> None:
    for name in ("figure.png", "figure.pdf"):
        (tmp_path / name).write_bytes(b"nonempty")
    assert _all_exports_nonblank(tmp_path) is False
    (tmp_path / "figure.tif").write_bytes(b"nonempty")
    assert _all_exports_nonblank(tmp_path) is False


def test_errorbar_uses_native_origin_error_arguments() -> None:
    class Plot:
        color = None

        def set_float(self, *_args):
            return None

        def set_int(self, *_args):
            return None

    class Layer:
        def __init__(self) -> None:
            self.calls = []

        def add_plot(self, sheet, **kwargs):
            self.calls.append((sheet, kwargs))
            return Plot()

    class Writer:
        sheet = object()

        def __init__(self) -> None:
            self.calls = []
            self.mapping = {"X": 0, "Y": 1, "XErr": 2, "YErr": 3}

        def column(self, name, axis):
            self.calls.append((name, axis))
            return self.mapping[name]

    layer = Layer()
    writer = Writer()
    count = _add_xy(
        layer,
        writer,
        [{"X": 1, "Y": 2, "XErr": 0.1, "YErr": 0.2}],
        {
            "op": "add_xy_plot",
            "kind": "errorbar",
            "series_id": "s1",
            "mapping": {"x": "X", "y": "Y", "x_error": "XErr", "y_error": "YErr"},
            "style": {},
        },
    )
    assert count == 1
    assert writer.calls == [("X", "X"), ("Y", "Y"), ("XErr", "M"), ("YErr", "E")]
    assert layer.calls[0][1]["colxerr"] == 2
    assert layer.calls[0][1]["colyerr"] == 3
    assert layer.calls[0][1]["type"] == "y"


def test_legend_adapter_applies_visibility_and_frame() -> None:
    class Legend:
        def __init__(self) -> None:
            self.removed = False
            self.ints = []

        def remove(self) -> None:
            self.removed = True

        def set_int(self, name, value) -> None:
            self.ints.append((name, value))

    class Layer:
        def __init__(self) -> None:
            self.legend = Legend()

        def label(self, name):
            assert name == "Legend"
            return self.legend

    visible = Layer()
    _set_legend(visible, {"visible": True, "frame": False})
    assert visible.legend.removed is False
    assert ("showframe", 0) in visible.legend.ints

    hidden = Layer()
    _set_legend(hidden, {"visible": False})
    assert hidden.legend.removed is True


def test_heatmap_live_adapter_fails_closed_before_origin_plot_call() -> None:
    class Layer:
        def __init__(self) -> None:
            self.calls = 0

        def add_plot(self, *_args, **_kwargs):
            self.calls += 1
            raise AssertionError("heatmap must be blocked before Origin add_plot is called")

    class Writer:
        sheet = object()

        def column(self, name, _axis):
            return {"X": 0, "Y": 1, "Z": 2}[name]

    layer = Layer()
    with pytest.raises(RuntimeError, match="E524_HEATMAP_LIVE_UNVERIFIED"):
        _add_matrix(
            layer,
            Writer(),
            {
                "op": "add_matrix_plot",
                "kind": "heatmap",
                "mapping": {"x": "X", "y": "Y", "z": "Z"},
                "style": {},
            },
        )
    assert layer.calls == 0
