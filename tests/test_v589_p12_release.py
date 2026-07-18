from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image
from PIL import ImageDraw


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class PortableRootRegressionTests(unittest.TestCase):
    def test_legacy_regression_modules_default_to_their_package_root(self) -> None:
        original = os.environ.pop("ORIGINPLOT_SKILL_ROOT", None)
        try:
            for filename in [
                "test_v589_p7_regressions.py",
                "test_v589_p8_regressions.py",
                "test_v589_p9_regressions.py",
            ]:
                module = load_module(
                    f"portable_{Path(filename).stem}",
                    ROOT / "tests" / filename,
                )
                self.assertEqual(ROOT.resolve(), module.SKILL_ROOT)
        finally:
            if original is not None:
                os.environ["ORIGINPLOT_SKILL_ROOT"] = original

    def test_run_all_tests_preserves_p13_baseline_count(self) -> None:
        runner = load_module(
            "originplot_run_all_tests_p12_minimum_test",
            ROOT / "scripts" / "run_all_tests.py",
        )
        self.assertEqual(165, runner.EXPECTED_MIN_TESTS)


class CanonicalSourceCropTests(unittest.TestCase):
    def test_fig12_canonical_crop_removes_declared_paper_text_band(self) -> None:
        canonical = load_module(
            "originplot_fig12_canonical_source_test",
            ROOT / "builders" / "aa2195" / "source_reference.py",
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / "source.png"
            output = root / "canonical.png"
            image = Image.new("RGB", (805, 590), "white")
            draw = ImageDraw.Draw(image)
            draw.rectangle((20, 2, 240, 12), fill="black")
            draw.rectangle((98, 55, 322, 271), fill="#fcbf6e")
            image.save(source)

            result = canonical.canonicalize_fig12_source_crop(source, output)

            cleaned = Image.open(output).convert("RGB")
            self.assertEqual((805, 590), cleaned.size)
            self.assertEqual((255, 255, 255), cleaned.getpixel((30, 8)))
            self.assertEqual((252, 191, 110), cleaned.getpixel((100, 60)))
            self.assertEqual("canonical_source_crop", result["status"])
            self.assertEqual([0, 0, 805, 40], result["excluded_paper_text_band"])


class ReleaseValidatorContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.release = load_module(
            "originplot_release_validator_p12_test",
            ROOT / "scripts" / "validate_release_candidate.py",
        )
        cls.evidence = load_module(
            "originplot_evidence_validator_p12_test",
            ROOT / "scripts" / "validate_benchmark_evidence_package.py",
        )

    def test_release_plan_contains_every_p12_gate_in_order(self) -> None:
        self.assertEqual(
            [
                "compileall",
                "run_all_tests",
                "random_directory_portability",
                "validate_shareable_package_v5",
                "absolute_path_scan",
                "cache_temp_artifact_scan",
                "report_version_consistency",
                "benchmark_evidence_packages",
                "live_readback_validation",
                "final_release_bundle_validation",
            ],
            self.release.RELEASE_GATE_ORDER,
        )

    def test_release_status_fails_closed_when_any_gate_fails(self) -> None:
        gates = {name: {"status": "ok"} for name in self.release.RELEASE_GATE_ORDER}
        self.assertEqual(
            "release_ready_for_fig12_targeted_optimization",
            self.release.release_status(gates),
        )
        gates["absolute_path_scan"] = {"status": "failed"}
        self.assertEqual("not_release_ready", self.release.release_status(gates))

    def test_release_process_record_does_not_persist_machine_paths(self) -> None:
        result = self.release.run_process(
            [sys.executable, "-c", "import os; print(os.getcwd())"],
            cwd=ROOT,
        )
        self.assertEqual({"returncode": 0}, result)

    def test_windows_absolute_path_detection_requires_separator_after_colon(self) -> None:
        self.assertTrue(self.evidence.is_absolute_path_text(r"C:\Users\example\file.json"))
        self.assertTrue(self.evidence.is_absolute_path_text("D:/portable/file.json"))
        self.assertFalse(self.evidence.is_absolute_path_text("H: Hardening level"))
        self.assertFalse(self.evidence.is_absolute_path_text("S: Softening level"))

    def test_identity_consistency_requires_run_figure_and_skill_version(self) -> None:
        payloads = {
            "inspection.json": {
                "run_id": "run-p12-canary",
                "figure_id": "fig15",
                "skill_version": "5.8.9-p18",
            },
            "qa_report.json": {
                "run_id": "run-p12-canary",
                "figure_id": "fig15",
                "skill_version": "5.8.9-p18",
            },
        }
        self.assertEqual([], self.evidence.identity_consistency_failures(payloads))
        payloads["qa_report.json"]["figure_id"] = "fig16"
        failures = self.evidence.identity_consistency_failures(payloads)
        self.assertEqual("identity_mismatch", failures[0]["code"])
        self.assertEqual("figure_id", failures[0]["field"])

    def test_live_readback_gate_requires_ten_complete_fig15_plots(self) -> None:
        plot = {
            "plot_type_code": 200,
            "plot_family": "line",
            "visible": True,
            "x_dataset": "Book2_A",
            "y_dataset": "Book2_B",
            "data_workbook": "Book2",
            "data_worksheet": "Sheet1",
            "data_worksheet_index": 0,
            "x_column": "A",
            "y_column": "B",
            "graph_plot_range": "[Graph1]1!1",
        }
        readback = {
            "origin_object_readback": {
                "Fig15_source_calibrated_two_layer": {
                    "layers": [
                        {"plot_details": [dict(plot) for _ in range(5)]},
                        {"plot_details": [dict(plot) for _ in range(5)]},
                    ]
                }
            }
        }
        result = self.release.validate_live_readback_payload(readback, figure_id="fig15")
        self.assertEqual("ok", result["status"])
        self.assertEqual(10, result["plot_count"])
        readback["origin_object_readback"]["Fig15_source_calibrated_two_layer"]["layers"][0][
            "plot_details"
        ][0]["data_workbook"] = None
        result = self.release.validate_live_readback_payload(readback, figure_id="fig15")
        self.assertEqual("failed", result["status"])
        self.assertIn("data_workbook", result["plot_failures"][0]["missing_or_invalid"])


class EvidenceDirectoryContractTests(unittest.TestCase):
    def test_shareable_package_requires_live_evidence_materializer(self) -> None:
        validator = load_module(
            "originplot_shareable_validator_p12_test",
            ROOT / "scripts" / "validate_shareable_package_v5.py",
        )
        self.assertIn(
            "originplot-skill/scripts/materialize_live_evidence.py",
            validator.REQUIRED,
        )

    def test_p12_required_evidence_file_set_is_exactly_the_standard_fifteen(self) -> None:
        validator = load_module(
            "originplot_evidence_validator_required_set_test",
            ROOT / "scripts" / "validate_benchmark_evidence_package.py",
        )
        self.assertEqual(
            {
                "result.opju",
                "source_crop.png",
                "pre_save.png",
                "post_reopen.png",
                "inspection.json",
                "qa_report.json",
                "benchmark_actual.json",
                "semantic_benchmark_report.json",
                "deviation_ledger.json",
                "comparison_board.png",
                "figurespec.json",
                "compiled_ir.json",
                "operation_plan.json",
                "run_artifacts.json",
                "run_manifest.json",
            },
            validator.REQUIRED_FILES,
        )

    def test_validator_rejects_missing_identity_fields(self) -> None:
        validator = load_module(
            "originplot_evidence_validator_missing_identity_test",
            ROOT / "scripts" / "validate_benchmark_evidence_package.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in validator.REQUIRED_FILES:
                path = root / name
                if path.suffix == ".json":
                    path.write_text(json.dumps({"schema": "test"}), encoding="utf-8")
                else:
                    path.write_bytes(b"test")
            result = validator.validate(root)
        codes = {failure["code"] for failure in result["failures"]}
        self.assertIn("identity_field_missing", codes)

    def test_materializer_creates_self_contained_valid_standard_evidence(self) -> None:
        materializer = load_module(
            "originplot_live_evidence_materializer_test",
            ROOT / "scripts" / "materialize_live_evidence.py",
        )
        validator = load_module(
            "originplot_evidence_validator_materialized_test",
            ROOT / "scripts" / "validate_benchmark_evidence_package.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.png"
            pre = root / "pre.png"
            post = root / "post.png"
            opju = root / "candidate.opju"
            for path, color in [(source, "white"), (pre, "white"), (post, "white")]:
                Image.new("RGB", (32, 24), color).save(path)
            opju.write_bytes(b"editable-origin-project")
            output = root / "evidence"
            result = materializer.materialize_standard_evidence(
                output_dir=output,
                run_id="run-p12-test",
                figure_id="fig15",
                skill_version="5.8.9-p18",
                source_crop=source,
                opju=opju,
                pre_save=pre,
                post_reopen=post,
                inspection={"origin_object_readback": {}},
                visual_metrics={
                    "pass_eligible": True,
                    "release_status": {
                        "runtime_release_ready": True,
                        "structure_pass": True,
                        "visual_baseline_status": "promoted",
                        "visual_baseline_promoted": True,
                        "overall_release_pass": True,
                    },
                    "mae_0_1": 0.01,
                    "rmse_0_1": 0.02,
                    "ssim_score": 0.99,
                    "layout_score": 0.99,
                    "edge_score": 0.99,
                    "color_score": 0.99,
                    "blocking_reasons": [],
                },
                route={
                    "route": "worksheet_semantic_reconstruction",
                    "candidate_params": {
                        "source_crop": str(source),
                        "project_root": str(root),
                        "label": "H: Hardening level",
                    },
                },
            )
            self.assertEqual("ok", result["status"])
            self.assertEqual(validator.REQUIRED_FILES, {path.name for path in output.iterdir()})
            for path in output.glob("*.json"):
                payload = json.loads(path.read_text(encoding="utf-8-sig"))
                self.assertEqual("run-p12-test", payload["run_id"])
                self.assertEqual("fig15", payload["figure_id"])
                self.assertEqual("5.8.9-p18", payload["skill_version"])
                self.assertNotIn(str(root), json.dumps(payload))
            validation = validator.validate(output)
            self.assertEqual("ok", validation["status"], validation["failures"])


if __name__ == "__main__":
    unittest.main()
