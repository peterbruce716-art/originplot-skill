from __future__ import annotations

import json
import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock, patch

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
    def test_standard_dry_run_rejects_generic_line_without_figure_spec(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(OriginPlotError, "generic_line requires --figure-spec"):
                execute(
                    profile=resolve_profile(),
                    figure=None,
                    builder="generic_line",
                    figure_spec_path=None,
                    candidate_path=None,
                    output_dir=Path(tmp),
                    live=False,
                )

    def test_quick_dry_run_rejects_empty_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(OriginPlotError, "supported builder"):
                execute(
                    profile=resolve_profile("quick"),
                    figure=None,
                    builder=None,
                    figure_spec_path=None,
                    candidate_path=None,
                    output_dir=Path(tmp),
                    live=False,
                )

    def test_figurespec_loads_and_validates_csv_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.csv").write_text("time,value\n0,1\n1,2\n", encoding="utf-8")
            spec = {
                "schema": "originplot.figurespec.v5",
                "figure": {"id": "line", "title": "Test line"},
                "data": [{"id": "d", "source": "data.csv", "roles": {"x": "time", "y": "value"}}],
                "page": {"size_mm": [120, 80]},
                "layers": [{"x": {"label": "Time"}, "y": {"label": "Value"}}],
                "plots": [{"data_ref": "d", "type": "line", "map": {"x": "time", "y": "value"}}],
                "annotations": [],
            }
            spec_path = root / "figure_spec.json"
            spec_path.write_text(json.dumps(spec), encoding="utf-8")
            payload = load_figure_spec(spec_path)
            self.assertEqual([0.0, 1.0], payload["x"])
            self.assertEqual("value", payload["y_name"])
            self.assertEqual("Test line", payload["title"])
            self.assertEqual("Time", payload["x_label"])
            self.assertEqual("Value", payload["y_label"])
            self.assertEqual([120.0, 80.0], payload["page_size_mm"])

    def test_standard_dry_run_redacts_local_template_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.csv").write_text("time,value\n0,1\n1,2\n", encoding="utf-8")
            spec_path = root / "figure_spec.json"
            spec_path.write_text(json.dumps({
                "schema": "originplot.figurespec.v5",
                "figure": {"id": "line"},
                "data": [{"id": "d", "source": "data.csv", "roles": {"x": "time", "y": "value"}}],
                "layers": [{"x": {"label": "Time"}, "y": {"label": "Value"}}],
                "plots": [{"data_ref": "d", "type": "line", "map": {"x": "time", "y": "value"}}],
            }), encoding="utf-8")
            local_path = str(Path.home() / "Documents" / "OriginLab" / "User Files" / "private-template.otpu")
            with patch("originplot.controller._local_candidates", return_value=[{
                "id": "private-template", "source": "local", "path": local_path, "reusable": True
            }]):
                result = execute(
                    profile=resolve_profile("standard"),
                    figure=None,
                    builder="generic_line",
                    figure_spec_path=spec_path,
                    candidate_path=None,
                    output_dir=root / "out",
                    live=False,
                )
            serialized = json.dumps(result, ensure_ascii=False)
            self.assertNotIn(local_path, serialized)
            self.assertNotIn("path", result["template_decision"]["selected"])

    def test_non_admin_live_controller_launches_elevated_worker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.csv").write_text("time,value\n0,1\n1,2\n", encoding="utf-8")
            spec_path = root / "figure_spec.json"
            spec_path.write_text(json.dumps({
                "schema": "originplot.figurespec.v5",
                "figure": {"id": "line"},
                "data": [{"id": "d", "source": "data.csv", "roles": {"x": "time", "y": "value"}}],
                "layers": [{"x": {"label": "Time"}, "y": {"label": "Value"}}],
                "plots": [{"data_ref": "d", "type": "line", "map": {"x": "time", "y": "value"}}],
            }), encoding="utf-8")
            output = root / "out"
            output.mkdir()
            summary = {
                "profile": "quick", "command_success": True, "live_origin_verified": True,
                "structure_pass": True, "visual_pass": False, "gate_results": HARD_GATE_RESULTS,
            }
            completed = Mock(returncode=0, stdout="", stderr="")
            def complete_worker(*_args, **_kwargs):
                (output / "candidate_summary.json").write_text(json.dumps(summary), encoding="utf-8")
                return completed
            with patch("originplot.controller.is_administrator", return_value=False), patch(
                "originplot.controller.subprocess.run", side_effect=complete_worker
            ) as runner:
                execute(
                    profile=resolve_profile("quick"),
                    figure=None,
                    builder="generic_line",
                    figure_spec_path=spec_path,
                    candidate_path=None,
                    output_dir=output,
                    live=True,
                )
            command = runner.call_args.args[0]
            self.assertIn("-File", command)
            self.assertTrue(any("run_origin_profile_worker_elevated.ps1" in str(item) for item in command))
            task = json.loads((output / "origin_worker_task.json").read_text(encoding="utf-8"))
            self.assertIsNone(task["candidate"])

    def test_failed_live_worker_does_not_reuse_stale_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.csv").write_text("time,value\n0,1\n1,2\n", encoding="utf-8")
            spec_path = root / "figure_spec.json"
            spec_path.write_text(json.dumps({
                "schema": "originplot.figurespec.v5",
                "figure": {"id": "line"},
                "data": [{"id": "d", "source": "data.csv", "roles": {"x": "time", "y": "value"}}],
                "layers": [{"x": {"label": "Time"}, "y": {"label": "Value"}}],
                "plots": [{"data_ref": "d", "type": "line", "map": {"x": "time", "y": "value"}}],
            }), encoding="utf-8")
            output = root / "out"
            output.mkdir()
            stale = {
                "profile": "quick", "command_success": True, "live_origin_verified": True,
                "structure_pass": True, "visual_pass": False, "gate_results": HARD_GATE_RESULTS,
            }
            (output / "candidate_summary.json").write_text(json.dumps(stale), encoding="utf-8")
            failed = Mock(returncode=1, stdout="", stderr="UAC elevation was cancelled")
            with patch("originplot.controller.is_administrator", return_value=False), patch(
                "originplot.controller.subprocess.run", return_value=failed
            ):
                result = execute(
                    profile=resolve_profile("quick"),
                    figure=None,
                    builder="generic_line",
                    figure_spec_path=spec_path,
                    candidate_path=None,
                    output_dir=output,
                    live=True,
                )
            self.assertFalse(result.get("live_origin_verified", False))
            self.assertEqual("E525_ORIGIN_WORKER_FAILED", result["error_code"])

    def test_generic_worker_save_reopen_binding_and_export(self) -> None:
        class FakePlot:
            lt_range = "[line_Data]Sheet1!(time,value)"

        class FakeLayer:
            def __init__(self) -> None:
                self.plots = []
                self.axes = {"x": Mock(title=""), "y": Mock(title="")}

            def add_plot(self, *_args, **_kwargs):
                plot = FakePlot()
                self.plots.append(plot)
                return plot

            def plot_list(self):
                return self.plots

            def rescale(self):
                return None

            def axis(self, name):
                return self.axes[name]

        class FakePage:
            def __init__(self, name: str) -> None:
                self.lname = name
                self.name = name
                self.layer = FakeLayer()
                self.show = False
                self.commands = []

            def __getitem__(self, _index):
                return self.layer

            def save_fig(self, path, **_kwargs):
                from PIL import Image

                Image.new("RGB", (64, 64), "white").save(path)

            def get_float(self, name):
                return {"resx": 100.0, "resy": 100.0}[name]

            def lt_exec(self, command):
                self.commands.append(command)

        class FakeSheet:
            def from_list(self, *_args, **_kwargs):
                return None

        class FakeBook:
            def __getitem__(self, _index):
                return FakeSheet()

        class FakeOrigin:
            def __init__(self) -> None:
                self.graphs = []
                self.session_events = None

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
                if self.session_events != ["enter1", "exit1", "enter2"]:
                    raise AssertionError("reopen must occur in a new attached session")
                return True

            def pages(self, page_type=None):
                return self.graphs if page_type == "g" else self.graphs

        session_events = []

        @contextmanager
        def fake_session(_op):
            phase = len([event for event in session_events if event.startswith("enter")]) + 1
            session_events.append(f"enter{phase}")
            try:
                yield {"origin_pid": 42, "phase": phase}
            finally:
                session_events.append(f"exit{phase}")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            task = {
                "schema": "originplot.origin_worker_task.v1",
                "profile": resolve_profile("quick").to_dict(),
                "builder": "generic_line",
                "output_dir": str(root),
                "data_payload": {
                    "figure_id": "line", "title": "Test line", "x_label": "Time", "y_label": "Value",
                    "page_size_mm": [120.0, 80.0], "x_name": "time", "y_name": "value",
                    "x": [0.0, 1.0], "y": [1.0, 2.0],
                },
            }
            task_path = root / "task.json"
            task_path.write_text(json.dumps(task), encoding="utf-8")
            fake_origin = FakeOrigin()
            fake_origin.session_events = session_events
            result = run_profile_worker(task_path, op_module=fake_origin, session_factory=fake_session, admin_check=lambda: True)
            self.assertTrue(result["command_success"])
            self.assertTrue(result["build_success"])
            self.assertTrue(result["reopen_success"])
            self.assertEqual(1, result["editable_plot_count"])
            self.assertTrue(result["worksheet_binding_ok"])
            self.assertTrue(result["export_nonblank"])
            self.assertFalse(result["demo_watermark_detected"])
            self.assertEqual("pass", result["gate_results"]["worksheet_binding"])
            self.assertEqual(["enter1", "exit1", "enter2", "exit2"], session_events)
            self.assertEqual("Test line", fake_origin.graphs[0].lname)
            self.assertEqual("Time", fake_origin.graphs[0].layer.axes["x"].title)
            self.assertEqual("Value", fake_origin.graphs[0].layer.axes["y"].title)
            self.assertTrue(any("page.width=" in command for command in fake_origin.graphs[0].commands))
            self.assertTrue((root / "candidate.opju").is_file())
            self.assertTrue((root / "candidate_export.png").is_file())

    def test_aa2195_config_is_complete(self) -> None:
        config = load_config()
        self.assertEqual(["GID399", "GID1652"], config["templates"]["fig16"])
        self.assertEqual(21, config["routes"]["fig16_segment_count"])
        self.assertEqual([1, 2, 3], config["routes"]["fig14_marker_shapes"])


if __name__ == "__main__":
    unittest.main()
