from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

from originplot.benchmarks.aa2195.config import load_config
from originplot.controller import execute
from originplot.core.errors import OriginPlotError, ProfileConfigurationError
from originplot.core.figure_spec import load_figure_spec
from originplot.core.profiles import resolve_profile
from originplot.core.result import gate_plan, normalize_live_result
from originplot.template.policy import apply_template_policy
from scripts.origin_profile_worker import run as run_profile_worker


HARD_GATE_RESULTS = {
    "opju_saved": "pass",
    "opju_reopened": "pass",
    "editable_plot_present": "pass",
    "worksheet_binding": "pass",
    "origin_export_nonblank": "pass",
    "demo_watermark_absent": "pass",
}


class ProfileResolutionTests(unittest.TestCase):
    def test_standard_is_default(self) -> None:
        profile = resolve_profile()
        self.assertEqual("standard", profile.name)
        self.assertEqual("auto", profile.template_policy)
        self.assertEqual("visual", profile.evidence_level)
        self.assertEqual("basic", profile.visual_qa)

    def test_quick_skips_templates_and_full_evidence(self) -> None:
        profile = resolve_profile("quick")
        self.assertEqual("skip", profile.template_policy)
        self.assertEqual("basic", profile.evidence_level)
        self.assertEqual("not_required", gate_plan(profile)["release_evidence"])

    def test_release_cannot_be_weakened(self) -> None:
        with self.assertRaises(ProfileConfigurationError):
            resolve_profile("release", visual_qa="basic")

    def test_quick_completed_is_never_release_eligible(self) -> None:
        result = normalize_live_result(
            resolve_profile("quick"),
            {"command_success": True, "live_origin_verified": True, "structure_pass": True, "visual_pass": False, "gate_results": HARD_GATE_RESULTS},
        )
        self.assertEqual("completed", result["overall_status"])
        self.assertFalse(result["pass_eligible"])

    def test_missing_hard_gate_cannot_complete(self) -> None:
        result = normalize_live_result(
            resolve_profile("quick"),
            {"command_success": True, "live_origin_verified": True, "structure_pass": True, "gate_results": {}},
        )
        self.assertEqual("incomplete", result["overall_status"])
        self.assertIn("opju_saved", result["failed_gates"])


class TemplatePolicyTests(unittest.TestCase):
    def test_skip_does_not_call_search(self) -> None:
        search = Mock(side_effect=AssertionError("must not be called"))
        result = apply_template_policy(
            "skip", max_candidates=3, local_search=search, gallery_search=search
        )
        self.assertEqual("not_required", result.status)
        search.assert_not_called()

    def test_auto_is_bounded(self) -> None:
        search = Mock(return_value=[{"id": index} for index in range(10)])
        result = apply_template_policy("auto", max_candidates=3, local_search=search)
        self.assertEqual(3, len(result.candidates))

    def test_auto_network_failure_falls_back(self) -> None:
        result = apply_template_policy(
            "auto",
            max_candidates=3,
            gallery_search=Mock(side_effect=OSError("offline")),
        )
        self.assertEqual("native_fallback", result.status)
        self.assertTrue(result.warnings)

    def test_strict_missing_record_fails_closed(self) -> None:
        with self.assertRaises(OriginPlotError):
            apply_template_policy("strict", max_candidates=0)


class ControllerTests(unittest.TestCase):
    def test_standard_dry_run_stays_non_live(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(
                profile=resolve_profile(),
                figure=None,
                builder="generic_line",
                figure_spec_path=None,
                candidate_path=None,
                output_dir=Path(tmp),
                live=False,
            )
            self.assertEqual("standard", result["profile"])
            self.assertEqual("planned_not_executed", result["overall_status"])
            self.assertFalse(result["live_origin_verified"])
            self.assertTrue((Path(tmp) / "candidate_summary.json").is_file())

    def test_figurespec_loads_and_validates_csv_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.csv").write_text("time,value\n0,1\n1,2\n", encoding="utf-8")
            spec = {
                "schema": "originplot.figurespec.v5",
                "figure": {"id": "line"},
                "data": [{"id": "d", "source": "data.csv", "roles": {"x": "time", "y": "value"}}],
                "layers": [{"x": {"label": "Time"}, "y": {"label": "Value"}}],
                "plots": [{"data_ref": "d", "type": "line", "map": {"x": "time", "y": "value"}}],
            }
            spec_path = root / "figure_spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            payload = load_figure_spec(spec_path)
            self.assertEqual([0.0, 1.0], payload["x"])
            self.assertEqual("value", payload["y_name"])

    def test_generic_worker_save_reopen_binding_and_export(self) -> None:
        class FakePlot:
            lt_range = "[line_Data]Sheet1!(time,value)"

        class FakeLayer:
            def __init__(self) -> None:
                self.plots = []

            def add_plot(self, *_args, **_kwargs):
                plot = FakePlot()
                self.plots.append(plot)
                return plot

            def plot_list(self):
                return self.plots

            def rescale(self):
                return None

        class FakePage:
            def __init__(self, name: str) -> None:
                self.lname = name
                self.name = name
                self.layer = FakeLayer()
                self.show = False

            def __getitem__(self, _index):
                return self.layer

            def save_fig(self, path, **_kwargs):
                from PIL import Image

                Image.new("RGB", (64, 64), "white").save(path)

        class FakeSheet:
            def from_list(self, *_args, **_kwargs):
                return None

        class FakeBook:
            def __getitem__(self, _index):
                return FakeSheet()

        class FakeOrigin:
            def __init__(self) -> None:
                self.graphs = []

            def new(self, **_kwargs):
                return True

            def new_book(self, *_args, **_kwargs):
                return FakeBook()

            def new_graph(self, lname, **_kwargs):
                page = FakePage(lname)
                self.graphs = [page]
                return page

            def save(self, path):
                Path(path).write_bytes(b"OPJU")
                return True

            def open(self, *_args, **_kwargs):
                return True

            def pages(self, page_type=None):
                return self.graphs if page_type == "g" else self.graphs

        @contextmanager
        def fake_session(_op):
            yield {"origin_pid": 42}

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = {
                "schema": "originplot.origin_worker_task.v1",
                "profile": resolve_profile("quick").to_dict(),
                "builder": "generic_line",
                "output_dir": str(root),
                "data_payload": {"figure_id": "line", "x_name": "time", "y_name": "value", "x": [0.0, 1.0], "y": [1.0, 2.0]},
            }
            task_path = root / "task.json"
            task_path.write_text(json.dumps(task), encoding="utf-8")
            result = run_profile_worker(task_path, op_module=FakeOrigin(), session_factory=fake_session, admin_check=lambda: True)
            self.assertTrue(result["command_success"])
            self.assertTrue(result["build_success"])
            self.assertTrue(result["reopen_success"])
            self.assertEqual(1, result["editable_plot_count"])
            self.assertTrue(result["worksheet_binding_ok"])
            self.assertTrue(result["export_nonblank"])
            self.assertFalse(result["demo_watermark_detected"])
            self.assertEqual("pass", result["gate_results"]["worksheet_binding"])
            self.assertTrue((root / "candidate.opju").is_file())
            self.assertTrue((root / "candidate_export.png").is_file())

    def test_aa2195_config_is_complete(self) -> None:
        config = load_config()
        self.assertEqual(["GID399", "GID1652"], config["templates"]["fig16"])
        self.assertEqual(21, config["routes"]["fig16_segment_count"])
        self.assertEqual([1, 2, 3], config["routes"]["fig14_marker_shapes"])


if __name__ == "__main__":
    unittest.main()
