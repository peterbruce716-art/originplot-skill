from __future__ import annotations

import json
from pathlib import Path

from originplot.adapters.originpro import _all_exports_nonblank, _template_for
from originplot.operation_plan import OperationPlan
from originplot.runtime.protocol import WORKER_TASK_SCHEMA, build_worker_task
from scripts.origin_profile_worker import run


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
    # Raster files must be real images, so arbitrary bytes are correctly rejected.
    assert _all_exports_nonblank(tmp_path) is False
