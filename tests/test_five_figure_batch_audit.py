import json
import tempfile
import unittest
from pathlib import Path

from scripts.audit_five_figure_batch import audit_batch


class FiveFigureBatchAuditTests(unittest.TestCase):
    def test_live_batch_runner_keeps_one_origin_pid_and_runs_audit(self):
        root = Path(__file__).resolve().parents[1]
        text = (root / "scripts" / "run_five_figure_live_batch.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('$figures = @("fig3", "fig12", "fig14", "fig15", "fig16")', text)
        self.assertIn("$pidStable", text)
        self.assertIn("audit_five_figure_batch.py", text)
        self.assertIn("[string]$SkillRoot = $null", text)
        self.assertIn('if (-not $SkillRoot) { $SkillRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath) }', text)
        self.assertIn("E126_STALE_OUTPUT_ROOT", text)
        self.assertIn("Get-ChildItem -LiteralPath $OutputRoot -Force", text)
        self.assertIn("fresh_output_root_verified = $true", text)
        self.assertLess(text.index("E126_STALE_OUTPUT_ROOT"), text.index("Get-Process -Name Origin64"))

    def _write_batch(self, root: Path, *, visual_pass: bool = True, shared_pid: bool = True) -> None:
        pid_values = [23780] * 5 if shared_pid else [23780, 23781, 23780, 23780, 23780]
        (root / "live_validation_status.json").write_text(json.dumps({"runs": [
            {"figure": figure, "visible_origin_pid": pid_values[index], "exit_code": 0, "pid_stable": True}
            for index, figure in enumerate(("fig3", "fig12", "fig14", "fig15", "fig16"))
        ]}), encoding="utf-8")
        for figure in ("fig3", "fig12", "fig14", "fig15", "fig16"):
            evidence = root / figure / "evidence"
            evidence.mkdir(parents=True)
            (root / figure / "candidate_manifest.json").write_text(json.dumps({
                "skill_version": "5.8.9-p14", "live_origin_verified": True,
                "structure_pass": True, "visual_pass": visual_pass,
            }), encoding="utf-8")
            (root / figure / "candidate_readback.json").write_text(json.dumps({
                "origin_object_readback_validation": {
                    "source_geometry_group_validation": {"status": "ok"},
                    "subplot_worksheet_validation": {"status": "ok"},
                    "legend_plot_reference_validation": {"status": "not_required"},
                }
            }), encoding="utf-8")
            (evidence / "run_manifest.json").write_text(json.dumps({
                "run_id": f"p14-{figure}-test", "provenance": "live_same_run",
                "release_status": {"overall_release_pass": visual_pass},
            }), encoding="utf-8")

    def test_accepts_complete_shared_origin_batch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_batch(root)
            self.assertEqual("pass", audit_batch(root)["status"])

    def test_rejects_pid_drift_and_visual_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_batch(root, visual_pass=False, shared_pid=False)
            result = audit_batch(root)
            self.assertEqual("fail", result["status"])
            self.assertIn("ORIGIN_PID_NOT_SHARED", {item["code"] for item in result["findings"]})
            self.assertIn("FIGURE_GATE_FAILED", {item["code"] for item in result["findings"]})

    def test_rejects_missing_source_geometry_group_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_batch(root)
            (root / "fig12" / "candidate_readback.json").write_text(json.dumps({
                "origin_object_readback_validation": {
                    "source_geometry_group_validation": {"status": "failed"}
                }
            }), encoding="utf-8")
            result = audit_batch(root)
            self.assertEqual("fail", result["status"])
            self.assertIn("SOURCE_GEOMETRY_GROUP_FAILED", {item["code"] for item in result["findings"]})

    def test_rejects_missing_subplot_worksheet_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_batch(root)
            readback_path = root / "fig15" / "candidate_readback.json"
            readback = json.loads(readback_path.read_text(encoding="utf-8"))
            readback["origin_object_readback_validation"]["subplot_worksheet_validation"] = {"status": "failed"}
            readback_path.write_text(json.dumps(readback), encoding="utf-8")
            result = audit_batch(root)
            self.assertEqual("fail", result["status"])
            self.assertIn("SUBPLOT_WORKSHEET_BINDING_FAILED", {item["code"] for item in result["findings"]})

    def test_rejects_missing_plot_derived_legend_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_batch(root)
            readback_path = root / "fig3" / "candidate_readback.json"
            readback = json.loads(readback_path.read_text(encoding="utf-8"))
            readback["origin_object_readback_validation"]["legend_plot_reference_validation"] = {"status": "failed"}
            readback_path.write_text(json.dumps(readback), encoding="utf-8")
            result = audit_batch(root)
            self.assertEqual("fail", result["status"])
            self.assertIn("PLOT_DERIVED_LEGEND_FAILED", {item["code"] for item in result["findings"]})
