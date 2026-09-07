from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from originplot.cli.main import main
from originplot.core.errors import OriginPlotError
from originplot.semantic.plan import build_figurespec


def source(tmp_path: Path, extra: str = "") -> Path:
    path = tmp_path / "data.csv"
    path.write_text(
        "Time,Stress A,Stress B"
        + extra
        + "\n0,100,200"
        + (",2" if extra else "")
        + "\n1,150,250"
        + (",3" if extra else "")
        + "\n"
    )
    return path


@pytest.mark.parametrize("kind", ["line", "scatter", "line_scatter"])
def test_all_recognized_xy_series_are_planned(tmp_path: Path, kind: str) -> None:
    spec = build_figurespec(source(tmp_path), plot_type=kind)
    assert [s["y"] for s in spec["data"]["series"]] == ["Stress A", "Stress B"]


def test_explicit_y_selects_only_requested_curve(tmp_path: Path) -> None:
    spec = build_figurespec(
        source(tmp_path), plot_type="line", mapping={"x": "Time", "y": "Stress B"}
    )
    assert [s["y"] for s in spec["data"]["series"]] == ["Stress B"]


def test_multiseries_error_mapping_requires_confirmation(tmp_path: Path) -> None:
    with pytest.raises(OriginPlotError, match="E330"):
        build_figurespec(source(tmp_path, ",SD"), plot_type="errorbar")


def test_missing_column_does_not_overwrite_existing_plan(tmp_path: Path) -> None:
    path = source(tmp_path)
    output = tmp_path / "plan.json"
    output.write_text("previous plan")
    assert (
        main(
            [
                "plan",
                str(path),
                "--plot-type",
                "line",
                "--x",
                "Time",
                "--y",
                "Missing",
                "--output",
                str(output),
            ]
        )
        == 1
    )
    assert output.read_text() == "previous plan"


def evidence(tmp_path: Path) -> dict:
    path = source(tmp_path)
    (tmp_path / "figure_spec.json").write_text(
        json.dumps(build_figurespec(path, plot_type="line"))
    )
    # Synthetic offline evidence exercises the verifier, not licensed Origin execution.
    (tmp_path / "figure.opju").write_bytes(b"synthetic project fixture")
    image = Image.new("RGB", (64, 64), "white")
    ImageDraw.Draw(image).line((4, 60, 60, 4), fill="black", width=3)
    for suffix in ("png", "tif", "pdf"):
        image.save(tmp_path / f"figure.{suffix}")
    names = (
        "figure.opju",
        "figure.png",
        "figure.pdf",
        "figure.tif",
        "figure_spec.json",
    )
    return {
        "schema": "originplot.origin_worker_result.v2",
        "mode": "live",
        "command_success": True,
        "live_origin_verified": True,
        "gate_results": {
            key: "pass"
            for key in (
                "opju_saved",
                "opju_reopened",
                "editable_plot_present",
                "worksheet_binding",
                "origin_export_nonblank",
                "origin_exports_complete",
                "demo_watermark_absent",
            )
        },
        "artifact_sha256": {
            name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
            for name in names
        },
    }


def verify(tmp_path: Path, record: object) -> int:
    (tmp_path / "verification.json").write_text(json.dumps(record))
    return main(["verify", str(tmp_path)])


def test_intact_recorded_artifacts_pass_offline_verification(tmp_path: Path) -> None:
    assert verify(tmp_path, evidence(tmp_path)) == 0


@pytest.mark.parametrize(
    "record",
    [[], None, "text", {"command_success": True, "live_origin_verified": False}],
)
def test_invalid_verification_records_fail_cleanly(
    tmp_path: Path, record: object
) -> None:
    evidence(tmp_path)
    assert verify(tmp_path, record) == 1


@pytest.mark.parametrize("field", ["command_success", "live_origin_verified"])
def test_success_flags_require_boolean_true(tmp_path: Path, field: str) -> None:
    record = evidence(tmp_path)
    record[field] = "false"
    assert verify(tmp_path, record) == 1


@pytest.mark.parametrize(
    "name",
    ["figure.opju", "figure.png", "figure.pdf", "figure.tif", "figure_spec.json"],
)
def test_modified_artifacts_are_rejected(tmp_path: Path, name: str) -> None:
    record = evidence(tmp_path)
    with (tmp_path / name).open("ab") as handle:
        handle.write(b"changed")
    assert verify(tmp_path, record) == 1


def test_missing_lifecycle_gate_fails(tmp_path: Path) -> None:
    record = evidence(tmp_path)
    del record["gate_results"]["worksheet_binding"]
    assert verify(tmp_path, record) == 1


@pytest.mark.parametrize("suffix", ["png", "tif", "pdf"])
def test_invalid_exports_fail_even_with_matching_hashes(
    tmp_path: Path, suffix: str
) -> None:
    record = evidence(tmp_path)
    name = f"figure.{suffix}"
    (tmp_path / name).write_bytes(b"invalid artifact")
    record["artifact_sha256"][name] = hashlib.sha256(b"invalid artifact").hexdigest()
    assert verify(tmp_path, record) == 1


def test_worker_records_hashes_for_final_artifacts(tmp_path: Path, monkeypatch) -> None:
    from originplot.runtime import worker
    from originplot.runtime.protocol import WORKER_TASK_SCHEMA

    result = evidence(tmp_path)
    expected = result.pop("artifact_sha256")
    # Origin cannot run in offline CI; only the native execution boundary is replaced.
    monkeypatch.setattr(
        worker, "execute_operation_plan", lambda *args, **kwargs: result
    )
    task = {
        "schema": WORKER_TASK_SCHEMA,
        "profile": {"name": "standard"},
        "output_dir": str(tmp_path),
        "figure_spec": str(tmp_path / "figure_spec.json"),
        "operation_plan": {
            "schema": "originplot.operation_plan.v1",
            "figure_id": "data",
            "plot_type": "line",
            "profile": "standard",
            "source": {},
            "operations": [],
        },
    }
    task_path = tmp_path / "task.json"
    task_path.write_text(json.dumps(task))
    actual = worker.run(task_path, admin_check=lambda: True)
    assert actual["command_success"] is True
    assert actual["artifact_sha256"] == expected
    assert main(["verify", str(tmp_path)]) == 0


def test_old_record_without_hashes_requires_new_evidence(tmp_path: Path) -> None:
    record = evidence(tmp_path)
    del record["artifact_sha256"]
    assert verify(tmp_path, record) == 1


def test_blank_image_rejected_even_with_current_hash(tmp_path: Path) -> None:
    record = evidence(tmp_path)
    path = tmp_path / "figure.png"
    Image.new("RGB", (64, 64), "white").save(path)
    record["artifact_sha256"][path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
    assert verify(tmp_path, record) == 1


@pytest.mark.parametrize(
    "name,data",
    [
        ("figure.pdf", b"%PDF-This is not a PDF\n%%EOF"),
        ("figure_spec.json", b'{"schema":"originplot.figurespec.v6"}'),
    ],
)
def test_structurally_invalid_artifacts_with_matching_hashes_fail(
    tmp_path: Path, name: str, data: bytes
) -> None:
    record = evidence(tmp_path)
    (tmp_path / name).write_bytes(data)
    record["artifact_sha256"][name] = hashlib.sha256(data).hexdigest()
    assert verify(tmp_path, record) == 1
