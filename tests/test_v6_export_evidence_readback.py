from __future__ import annotations

from copy import deepcopy
import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts import origin_candidate_worker as worker


@pytest.fixture
def mock_live_readback(tmp_path, monkeypatch):
    candidate = {"figure": "fig3", "export_supersample": 4}
    source_opju = tmp_path / "mock_source.opju"
    source_png = tmp_path / "mock_source.png"
    source_opju.write_bytes(b"mock project; not an Origin file")
    source_png.write_bytes(b"mock raster; visual scoring is mocked")
    definition = SimpleNamespace(
        builder_id="fig3", supports_live=True, validate_plan=Mock(return_value={})
    )
    monkeypatch.setattr(worker, "read_candidate", Mock(return_value=candidate))
    monkeypatch.setattr(worker, "resolve_builder", Mock(return_value=definition))
    monkeypatch.setattr(worker, "require_template_search_record", Mock(return_value={}))
    monkeypatch.setattr(worker, "_resolve_source_crop", Mock(return_value=None))
    monkeypatch.setattr(
        worker,
        "_validate_fresh_source_gate",
        Mock(
            return_value={
                "status": "pass",
                "policy": "validated_reuse",
                "manifest_path": "mock_manifest.json",
                "data_sha256": "a" * 64,
            }
        ),
    )
    monkeypatch.setattr(worker, "is_admin", Mock(return_value=True))
    monkeypatch.setattr(
        worker, "evaluate_visual_metrics", Mock(side_effect=lambda **kwargs: {})
    )
    monkeypatch.setattr(worker, "materialize_standard_evidence", Mock(return_value={}))

    def run(name, export_evidence=None):
        fig_result = {
            "status": "post_reopen_built",
            "opju_path": str(source_opju),
            "origin_rendered_exports": [
                {"phase": phase, "path": str(source_png)}
                for phase in ("pre_save", "post_reopen")
            ],
            "origin_candidate_hard_gate": {"status": "pass"},
            "builder_route": {
                "route": "mock_live",
                "canvas_size": [100, 80],
                "export_supersample": 4,
            },
        }
        if export_evidence is not None:
            fig_result["origin_export_evidence"] = deepcopy(export_evidence)
        builder = SimpleNamespace(
            build_origin_figure=Mock(
                return_value={
                    "status": "built",
                    "per_figure": {"fig3": fig_result},
                }
            )
        )
        monkeypatch.setattr(worker, "_load_aa2195_builder", Mock(return_value=builder))
        output_dir = tmp_path / name
        manifest = worker.run_live("fig3", tmp_path / "candidate.json", output_dir)
        assert manifest["command_success"] is True, manifest
        readback = json.loads(
            (output_dir / "candidate_readback.json").read_text(encoding="utf-8")
        )
        return readback, manifest

    return run


def test_nondefault_export_evidence_survives_persisted_readback(mock_live_readback):
    evidence = {
        phase: {
            "supersample": 4,
            "export_width": 400,
            "rendered_size": [400, native_height],
            "resampled": True,
            "resampled_to": [100, 80],
        }
        for phase, native_height in (("pre_save", 318), ("post_reopen", 322))
    }
    readback, manifest = mock_live_readback("with_evidence", evidence)
    assert readback["origin_export_evidence"] == evidence

    baseline, baseline_manifest = mock_live_readback("without_evidence")
    for field in (
        "candidate_sha256",
        "effective_builder_route",
        "source_data_gate",
        "fresh_source_gate",
        "render_identity",
        "target_visual_gate",
        "release_status",
    ):
        assert readback[field] == baseline[field], field
    for field in (
        "status",
        "command_success",
        "structure_pass",
        "visual_pass",
        "live_origin_verified",
        "pass_eligible",
        "overall_status",
    ):
        assert manifest[field] == baseline_manifest[field], field


def test_missing_export_evidence_defaults_to_empty_record(mock_live_readback):
    readback, _ = mock_live_readback("legacy_builder")
    assert readback["origin_export_evidence"] == {}
