from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np

from builders.aa2195.fresh_source_data import load_fresh_figure_data
from scripts import extract_aa2195_fresh_source_bundle, origin_candidate_worker


class FreshSourceGateTests(unittest.TestCase):
    @staticmethod
    def _write_bundle(root: Path) -> tuple[Path, Path, dict[str, object]]:
        crop = root / "fig3_source.png"
        crop.write_bytes(b"same-run-source-crop")
        data = {"method": "fresh_test", "panels": []}
        crop_sha = hashlib.sha256(crop.read_bytes()).hexdigest()
        data_sha = origin_candidate_worker._stable_digest(data)
        payload = {
            "schema": "originplot.aa2195_fresh_source_bundle.v1",
            "fresh_extraction": True,
            "source_pdf": {"sha256": "a" * 64},
            "bundle_data_sha256": "b" * 64,
            "figures": {
                "fig3": {
                    "source_crop": crop.name,
                    "source_crop_sha256": crop_sha,
                    "data_sha256": data_sha,
                    "data": data,
                }
            },
        }
        manifest = root / "source_bundle.json"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        return crop, manifest, payload

    def test_worker_and_builder_accept_matching_same_run_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crop, manifest, payload = self._write_bundle(root)
            candidate_path = root / "fig3.json"
            candidate = {
                "figure": "fig3",
                "source_crop": crop.name,
                "source_data_manifest": manifest.name,
                "fresh_source_required": True,
            }
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            gate = origin_candidate_worker._validate_fresh_source_gate(
                "fig3", candidate, candidate_path, crop
            )
            record = load_fresh_figure_data(
                {"_runtime_source_crop": str(crop), "_runtime_data_manifest": str(manifest)},
                "fig3",
            )

        self.assertEqual("pass", gate["status"])
        self.assertEqual(payload["figures"]["fig3"]["data_sha256"], record["data_sha256"])

    def test_worker_rejects_crop_hash_mismatch_before_origin(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crop, manifest, _ = self._write_bundle(root)
            candidate_path = root / "fig3.json"
            candidate = {
                "figure": "fig3",
                "source_crop": crop.name,
                "source_data_manifest": manifest.name,
                "fresh_source_required": True,
            }
            crop.write_bytes(b"mutated-inherited-crop")
            with self.assertRaisesRegex(ValueError, "crop hash mismatch"):
                origin_candidate_worker._validate_fresh_source_gate(
                    "fig3", candidate, candidate_path, crop
                )

    def test_worker_accepts_quality_validated_reuse_with_matching_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crop, manifest, payload = self._write_bundle(root)
            reuse_record = root / "validated_data_reuse.json"
            reuse_record.write_text(json.dumps({
                "schema": "originplot.aa2195_validated_data_reuse.v1",
                "status": "ok",
                "source_bundle_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                "source_bundle_data_sha256": payload["bundle_data_sha256"],
                "figures": {"fig3": {
                    "run_id": "p18-fig3-validated",
                    "provenance": "live_same_run",
                    "structure_pass": True,
                    "visual_pass": True,
                    "live_origin_verified": True,
                    "overall_release_pass": True,
                    "data_sha256": payload["figures"]["fig3"]["data_sha256"],
                    "source_crop_sha256": payload["figures"]["fig3"]["source_crop_sha256"],
                }},
            }), encoding="utf-8")
            candidate_path = root / "fig3.json"
            candidate = {
                "figure": "fig3",
                "source_crop": crop.name,
                "source_data_manifest": manifest.name,
                "source_data_policy": "validated_reuse",
                "source_reuse_record": reuse_record.name,
            }
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            gate = origin_candidate_worker._validate_source_data_gate(
                "fig3", candidate, candidate_path, crop
            )
            loaded = load_fresh_figure_data({
                "_runtime_source_crop": str(crop),
                "_runtime_data_manifest": str(manifest),
                "_runtime_source_data_policy": "validated_reuse",
            }, "fig3")

        self.assertEqual("validated_reuse", gate["policy"])
        self.assertEqual("pass", gate["reuse_validation"])
        self.assertEqual("validated_reuse", loaded["source_data_policy"])

    def test_worker_rejects_reuse_without_prior_visual_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crop, manifest, payload = self._write_bundle(root)
            reuse_record = root / "validated_data_reuse.json"
            reuse_record.write_text(json.dumps({
                "schema": "originplot.aa2195_validated_data_reuse.v1",
                "status": "ok",
                "source_bundle_manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest(),
                "source_bundle_data_sha256": payload["bundle_data_sha256"],
                "figures": {"fig3": {
                    "provenance": "live_same_run",
                    "structure_pass": True,
                    "visual_pass": False,
                    "live_origin_verified": True,
                    "overall_release_pass": True,
                    "data_sha256": payload["figures"]["fig3"]["data_sha256"],
                    "source_crop_sha256": payload["figures"]["fig3"]["source_crop_sha256"],
                }},
            }), encoding="utf-8")
            candidate = {
                "figure": "fig3",
                "source_crop": crop.name,
                "source_data_manifest": manifest.name,
                "source_data_policy": "validated_reuse",
                "source_reuse_record": reuse_record.name,
            }
            candidate_path = root / "fig3.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "quality gates did not pass"):
                origin_candidate_worker._validate_source_data_gate(
                    "fig3", candidate, candidate_path, crop
                )

    def test_worker_accepts_hash_linked_fig14_validated_crop_reextract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            crop = root / "fig14_source.png"
            crop.write_bytes(b"validated-fig14-source-crop")
            crop_sha = hashlib.sha256(crop.read_bytes()).hexdigest()
            parent_data = {"method": "legacy_fig14_extraction", "series": {}}
            parent_data_sha = origin_candidate_worker._stable_digest(parent_data)
            corrected_data = {
                "method": "fresh_source_crop_color_marker_and_component_errorbar_digitization",
                "series": {"PSC": {"y": [0.04], "err": [0.01]}},
            }
            corrected_data_sha = origin_candidate_worker._stable_digest(corrected_data)
            reuse = {
                "schema": "originplot.aa2195_validated_data_reuse.v1",
                "status": "ok",
                "source_bundle_manifest_sha256": "c" * 64,
                "source_bundle_data_sha256": "d" * 64,
                "figures": {"fig14": {
                    "run_id": "p17-fig14-parent",
                    "provenance": "live_same_run",
                    "structure_pass": True,
                    "visual_pass": True,
                    "live_origin_verified": True,
                    "overall_release_pass": True,
                    "data_sha256": parent_data_sha,
                    "source_crop_sha256": crop_sha,
                }},
            }
            reuse_path = root / "validated_data_reuse.json"
            reuse_path.write_text(json.dumps(reuse), encoding="utf-8")
            manifest = {
                "schema": "originplot.aa2195_fresh_source_bundle.v1",
                "fresh_extraction": False,
                "validated_crop_reextract": True,
                "source_data_policy": "validated_crop_reextract",
                "reextracted_figures": ["fig14"],
                "parent_source_bundle_manifest_sha256": "c" * 64,
                "parent_source_bundle_data_sha256": "d" * 64,
                "source_reuse_record_sha256": hashlib.sha256(reuse_path.read_bytes()).hexdigest(),
                "bundle_data_sha256": "e" * 64,
                "figures": {"fig14": {
                    "source_crop": crop.name,
                    "source_crop_sha256": crop_sha,
                    "data_policy": "validated_crop_reextract",
                    "parent_data_sha256": parent_data_sha,
                    "data_sha256": corrected_data_sha,
                    "data": corrected_data,
                }},
            }
            manifest_path = root / "source_bundle.json"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            candidate = {
                "figure": "fig14",
                "source_crop": crop.name,
                "source_data_manifest": manifest_path.name,
                "source_data_policy": "validated_crop_reextract",
                "source_reuse_record": reuse_path.name,
            }
            candidate_path = root / "fig14.json"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")

            gate = origin_candidate_worker._validate_source_data_gate(
                "fig14", candidate, candidate_path, crop
            )
            loaded = load_fresh_figure_data({
                "_runtime_source_crop": str(crop),
                "_runtime_data_manifest": str(manifest_path),
                "_runtime_source_data_policy": "validated_crop_reextract",
            }, "fig14")

        self.assertEqual("pass", gate["status"])
        self.assertEqual("validated_crop_reextract", gate["policy"])
        self.assertTrue(gate["reextracted_from_validated_crop"])
        self.assertEqual("validated_crop_reextract", loaded["source_data_policy"])
        self.assertEqual(corrected_data_sha, loaded["data_sha256"])

    def test_extractor_does_not_import_inherited_aa2195_data_tables(self) -> None:
        root = Path(__file__).resolve().parents[1]
        text = (root / "scripts" / "extract_aa2195_fresh_source_bundle.py").read_text(encoding="utf-8")
        self.assertNotIn("from builders.aa2195.fig3_data", text)
        self.assertNotIn("from builders.aa2195.fig14_builder", text)
        self.assertIn("fresh_pdf_vector_path_centerline_digitization", text)

    def test_fig14_error_extent_does_not_merge_series_at_same_x(self) -> None:
        rgb = np.full((150, 80, 3), 255, dtype=np.uint8)
        x = 40
        for marker_y, top, bottom in ((35, 25, 45), (75, 60, 90), (115, 103, 127)):
            rgb[top:bottom + 1, x - 1:x + 2] = 0
            rgb[top:top + 2, x - 6:x + 7] = 0
            rgb[bottom - 1:bottom + 1, x - 6:x + 7] = 0
            rgb[marker_y - 4:marker_y + 5, x - 4:x + 5] = (220, 70, 70)

        top, bottom = extract_aa2195_fresh_source_bundle._fig14_error_extent(rgb, x, 75.0)

        self.assertEqual(60.0, top)
        self.assertEqual(90.0, bottom)

    def test_fig14_first_marker_ignores_legend_symbol_at_same_x(self) -> None:
        mask = np.zeros((150, 80), dtype=bool)
        x = 40
        mask[20:27, x - 4:x + 5] = True
        mask[108:117, x - 4:x + 5] = True

        center = extract_aa2195_fresh_source_bundle._fig14_marker_center(mask, x, None)

        self.assertAlmostEqual(112.0, center)

    def test_fig14_error_magnitude_uses_visible_side_when_marker_occludes_other_side(self) -> None:
        error = extract_aa2195_fresh_source_bundle._fig14_error_magnitude(
            marker_y=75.0,
            error_top=82.0,
            error_bottom=90.0,
            axis_height=100.0,
        )

        self.assertAlmostEqual(0.06, error)


if __name__ == "__main__":
    unittest.main()
