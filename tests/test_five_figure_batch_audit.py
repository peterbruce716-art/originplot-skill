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
