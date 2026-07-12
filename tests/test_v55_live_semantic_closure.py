from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from scripts.operation_maturity import normalize, validate_plan
from scripts.visual_evidence_engine import evaluate
from scripts.validate_benchmark_evidence_package import validate


class LiveSemanticClosureV55Tests(unittest.TestCase):
    def test_operation_maturity_requires_all_five_columns(self) -> None:
        matrix = normalize([{"operation_id": "object.text.create", "registry": True, "adapter_implemented": True, "doctor_verified": False, "inspector_readback": False, "integration_test": False}])
        result = validate_plan({"operations": [{"operation_id": "object.text.create"}]}, matrix)
        self.assertEqual("failed", result["status"])
        self.assertEqual("implemented_unverified", result["failures"][0]["status"])

    def test_visual_engine_reports_roi_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "source.png"
            exp = root / "export.png"
            img = Image.new("RGB", (120, 80), "white")
            draw = ImageDraw.Draw(img)
            draw.rectangle((10, 10, 110, 70), outline="black", width=2)
            draw.line((20, 60, 100, 20), fill="blue", width=3)
            img.save(src)
            img.save(exp)
            visual, deviations = evaluate(src, exp, root / "evidence", {"page": {"min_ssim": 0.9, "min_edge_f1": 0.9, "max_mae": 0.02}, "panels": {"min_ssim": 0.9, "min_edge_f1": 0.9, "max_mae": 0.02}, "max_bbox_delta": 0.05}, [{"id": "panel_a", "role": "panel", "source_bbox_norm": [0, 0, 1, 1]}])
            self.assertEqual([], deviations)
            self.assertEqual("pass", visual["status"])
            self.assertEqual(1, len(visual["roi_results"]))

    def test_evidence_validator_rejects_inherited_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ["source_crop.png", "result.opju", "pre_save.png", "post_reopen.png", "registered_export.png", "alpha_overlay.png", "absolute_diff.png", "edge_overlay.png", "comparison_board.png"]:
                (root / name).write_bytes(b"x")
            for name in ["figurespec.json", "compiled_ir.json", "operation_plan.json", "inspection.json", "qa_report.json", "benchmark_actual.json", "deviation_ledger.json", "run_manifest.json"]:
                (root / name).write_text("{}", encoding="utf-8")
            (root / "semantic_benchmark_report.json").write_text(json.dumps({"status": "pass"}), encoding="utf-8")
            (root / "run_artifacts.json").write_text(json.dumps({"schema": "originplot.artifacts.v1", "run_id": "run_a", "project": {"path": "result.opju", "exists": True, "sha256": "bad", "provenance": "inherited_diagnostic", "eligible_for_pass": False}}), encoding="utf-8")
            result = validate(root)
            codes = {item["code"] for item in result["failures"]}
            self.assertIn("artifact_not_live_same_run", codes)


if __name__ == "__main__":
    unittest.main()
