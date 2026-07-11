from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark_materializer import materialize  # noqa: E402
from scripts.validate_benchmark_evidence_package import validate  # noqa: E402
from runtime.artifact_manifest import same_run_failures  # noqa: E402


class EvidenceLinkedV54Tests(unittest.TestCase):
    def test_materializer_uses_inspection_not_inline_actual(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            files = {}
            for name, payload in {
                "inspection": {"graph_pages": [{"layers": 2, "layer_details": [{"plots": 1}, {"plots": 1}]}], "workbooks": [{}], "matrices": [], "objects": [{"role": "panel_label"}, {"role": "panel_label"}]},
                "qa_report": {"status": "pass"},
                "run_artifacts": {"schema": "originplot.artifacts.v1", "run_id": "run_test"},
                "figurespec": {"figure_id": "fig15"},
            }.items():
                path = root / f"{name}.json"
                path.write_text(json.dumps(payload), encoding="utf-8")
                files[name] = path
            actual = materialize(
                recipe={"figure_id": "fig15", "recipe": "recipe.schematic.dual_panel_curve.v1", "actual": {"structure": {"graph_pages": 99}}},
                inspection=json.loads(files["inspection"].read_text()),
                qa_report=json.loads(files["qa_report"].read_text()),
                run_artifacts=json.loads(files["run_artifacts"].read_text()),
                figurespec=json.loads(files["figurespec"].read_text()),
                source_files=files,
            )
            self.assertEqual(actual["structure"]["graph_pages"], 1)
            self.assertEqual(actual["structure"]["layers"], 2)
            self.assertEqual(actual["objects"], [{"role": "panel_label", "count": 2}])

    def test_same_run_rejects_wrong_run_and_seed_pass_eligibility(self) -> None:
        payload = {
            "schema": "originplot.artifacts.v1",
            "run_id": "run_a",
            "post_reopen_export": {"path": "post.png", "exists": True, "sha256": "x", "run_id": "run_b"},
            "project": {"path": "result.opju", "exists": True, "sha256": "y", "inherited_from_run": "run_seed", "eligible_for_pass": True},
        }
        codes = {item["code"] for item in same_run_failures(payload)}
        self.assertIn("ARTIFACT_RUN_ID_MISMATCH", codes)
        self.assertIn("INHERITED_ARTIFACT_ELIGIBLE_FOR_PASS", codes)

    def test_evidence_package_validator_requires_core_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source_crop.png").write_bytes(b"x")
            result = validate(root)
            self.assertEqual(result["status"], "failed")
            codes = {item["code"] for item in result["failures"]}
            self.assertIn("missing_required_evidence_file", codes)


if __name__ == "__main__":
    unittest.main()
