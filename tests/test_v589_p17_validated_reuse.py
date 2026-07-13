from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build_validated_data_reuse_record import build_reuse_record
from scripts.reextract_validated_source_bundle import reextract_bundle


FIGURES = ("fig3", "fig12", "fig14", "fig15", "fig16")


def _stable_digest(value: object) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class ValidatedReuseRecordTests(unittest.TestCase):
    def _write_batch(self, root: Path) -> Path:
        bundle_dir = root / "source_bundle"
        bundle_dir.mkdir(parents=True)
        figure_records = {}
        gates = {}
        for figure in FIGURES:
            crop = bundle_dir / f"{figure}_source.png"
            crop.write_bytes(f"crop-{figure}".encode("ascii"))
            data = {"figure": figure, "values": [1, 2, 3]}
            record = {
                "source_crop": crop.name,
                "source_crop_sha256": hashlib.sha256(crop.read_bytes()).hexdigest(),
                "data_sha256": _stable_digest(data),
                "data": data,
            }
            figure_records[figure] = record
            gates[figure] = {
                "status": "pass",
                "policy": "fresh_extract",
                "data_sha256": record["data_sha256"],
                "source_crop_sha256": record["source_crop_sha256"],
            }
        bundle_digest = _stable_digest({
            figure: {
                "source_crop_sha256": figure_records[figure]["source_crop_sha256"],
                "data_sha256": figure_records[figure]["data_sha256"],
            }
            for figure in FIGURES
        })
        manifest = bundle_dir / "source_bundle.json"
        manifest.write_text(json.dumps({
            "schema": "originplot.aa2195_fresh_source_bundle.v1",
            "fresh_extraction": True,
            "source_pdf": {"sha256": "a" * 64},
            "bundle_data_sha256": bundle_digest,
            "figures": figure_records,
        }), encoding="utf-8")
        (root / "five_figure_batch_audit.json").write_text(
            json.dumps({"status": "pass", "findings": []}), encoding="utf-8"
        )
        (root / "live_validation_status.json").write_text(json.dumps({
            "status": "completed",
            "source_bundle_manifest": str(manifest),
        }), encoding="utf-8")
        for figure in FIGURES:
            evidence = root / figure / "evidence"
            evidence.mkdir(parents=True)
            (root / figure / "candidate_manifest.json").write_text(json.dumps({
                "structure_pass": True,
                "visual_pass": True,
                "live_origin_verified": True,
            }), encoding="utf-8")
            (root / figure / "candidate_readback.json").write_text(
                json.dumps({"source_data_gate": gates[figure]}), encoding="utf-8"
            )
            (evidence / "run_manifest.json").write_text(json.dumps({
                "run_id": f"p18-{figure}-validated",
                "provenance": "live_same_run",
                "release_status": {"overall_release_pass": True},
            }), encoding="utf-8")
        return manifest

    def test_builds_reuse_record_only_from_fully_promoted_batch(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = self._write_batch(root)
            expected_manifest_sha256 = hashlib.sha256(manifest.read_bytes()).hexdigest()
            result = build_reuse_record(root)
        self.assertEqual("ok", result["status"])
        self.assertEqual(expected_manifest_sha256, result["source_bundle_manifest_sha256"])
        self.assertEqual(set(FIGURES), set(result["figures"]))
        self.assertIn("opju", result["forbidden_reuse"])

    def test_rejects_batch_with_failed_figure_visual_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_batch(root)
            path = root / "fig14" / "candidate_manifest.json"
            payload = json.loads(path.read_text(encoding="utf-8"))
            payload["visual_pass"] = False
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "quality gates did not pass"):
                build_reuse_record(root)

    def test_validated_crop_reextract_changes_only_fig14_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._write_batch(root)
            reuse_path = root / "validated_data_reuse.json"
            reuse = build_reuse_record(root)
            reuse_path.write_text(json.dumps(reuse), encoding="utf-8")
            output = root / "reextracted"
            corrected = {
                "method": "fresh_source_crop_color_marker_and_component_errorbar_digitization",
                "temperature": [250.0],
                "series": {"PSC": {"y": [0.04], "err": [0.01]}},
            }
            with patch(
                "scripts.reextract_validated_source_bundle._extract_fig14_data",
                return_value=corrected,
            ):
                result = reextract_bundle(reuse_path, output)

        self.assertTrue(result["validated_crop_reextract"])
        self.assertEqual(["fig14"], result["reextracted_figures"])
        self.assertEqual("validated_crop_reextract", result["figures"]["fig14"]["data_policy"])
        self.assertNotEqual(
            result["figures"]["fig14"]["parent_data_sha256"],
            result["figures"]["fig14"]["data_sha256"],
        )
        for figure in ("fig3", "fig12", "fig15", "fig16"):
            self.assertEqual("validated_reuse", result["figures"][figure]["data_policy"])
            self.assertEqual(
                result["figures"][figure]["parent_data_sha256"],
                result["figures"][figure]["data_sha256"],
            )

    def test_live_runner_exposes_all_source_data_policies(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "scripts" / "run_five_figure_live_batch.ps1").read_text(encoding="utf-8-sig")
        self.assertIn('[ValidateSet("fresh_extract", "validated_reuse", "validated_crop_reextract")]', text)
        self.assertIn("[string]$ReuseBatchRoot = $null", text)
        self.assertIn("build_validated_data_reuse_record.py", text)
        self.assertIn("reextract_validated_source_bundle.py", text)
        self.assertIn("validated_source_data_reuse_verified", text)
        self.assertIn("validated_crop_reextract_verified", text)
        self.assertIn("Copy-Item -LiteralPath $priorManifest", text)


if __name__ == "__main__":
    unittest.main()
