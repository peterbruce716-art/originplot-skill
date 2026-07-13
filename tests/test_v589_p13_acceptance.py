from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class AcceptanceStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acceptance = load("p13_acceptance", "scripts/acceptance_hardening.py")

    def test_runtime_and_structure_do_not_promote_visual_baseline(self) -> None:
        status = self.acceptance.derive_release_status(True, True, False)
        self.assertTrue(status["runtime_release_ready"])
        self.assertTrue(status["structure_pass"])
        self.assertFalse(status["visual_baseline_promoted"])
        self.assertFalse(status["overall_release_pass"])
        self.assertFalse(status["pass_eligible"])
        self.assertTrue(status["pass_eligible_deprecated"])

    def test_provisional_visual_state_is_not_promoted(self) -> None:
        status = self.acceptance.derive_release_status(True, True, "provisional")
        self.assertEqual("provisional", status["visual_baseline_status"])
        self.assertFalse(status["visual_baseline_promoted"])
        self.assertFalse(status["overall_release_pass"])

    def test_all_three_true_are_required_for_overall_pass(self) -> None:
        self.assertTrue(self.acceptance.derive_release_status(True, True, True)["overall_release_pass"])
        self.assertFalse(self.acceptance.derive_release_status(False, True, True)["overall_release_pass"])
        self.assertFalse(self.acceptance.derive_release_status(True, False, True)["overall_release_pass"])


class RenderFingerprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acceptance = load("p13_fingerprint", "scripts/acceptance_hardening.py")

    def payload(self) -> dict:
        return {
            "candidate_id": "a",
            "run_id": "run-a",
            "timestamp": "now",
            "output_path": "C:/tmp/a",
            "requested_parameters": {"scale": 10.0},
            "effective_parameters": {"scale": 8.0, "sigma": 4.0},
            "effective_builder_route": {"route": "native", "scale": 8.0},
            "data_digest": "data-a",
            "geometry_table_version": "g1",
            "source_crop_sha256": "crop-a",
            "origin_version": "2022",
            "export_profile": {"width": 805, "height": 590},
            "template_ids": ["GID499", "GID459", "GID27"],
            "font_profile": "default-serif",
            "feature_flags": {"speed_mode": False},
        }

    def test_metadata_and_requested_values_do_not_change_fingerprint(self) -> None:
        left = self.payload()
        right = dict(left, candidate_id="b", run_id="run-b", timestamp="later", output_path="D:/elsewhere")
        right["requested_parameters"] = {"scale": 99.0}
        self.assertEqual(
            self.acceptance.render_parameter_fingerprint(left)["fingerprint"],
            self.acceptance.render_parameter_fingerprint(right)["fingerprint"],
        )

    def test_effective_parameter_or_data_changes_fingerprint(self) -> None:
        base = self.payload()
        changed = json.loads(json.dumps(base))
        changed["effective_parameters"]["scale"] = 7.0
        self.assertNotEqual(
            self.acceptance.render_parameter_fingerprint(base)["fingerprint"],
            self.acceptance.render_parameter_fingerprint(changed)["fingerprint"],
        )
        changed = json.loads(json.dumps(base))
        changed["data_digest"] = "data-b"
        self.assertNotEqual(
            self.acceptance.render_parameter_fingerprint(base)["fingerprint"],
            self.acceptance.render_parameter_fingerprint(changed)["fingerprint"],
        )

    def test_key_order_does_not_change_fingerprint(self) -> None:
        payload = self.payload()
        reordered = dict(reversed(list(payload.items())))
        self.assertEqual(
            self.acceptance.render_parameter_fingerprint(payload)["fingerprint"],
            self.acceptance.render_parameter_fingerprint(reordered)["fingerprint"],
        )


class ParameterNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acceptance = load("p13_normalize", "scripts/acceptance_hardening.py")

    def test_strict_mode_rejects_scale_above_five_thousand_row_limit(self) -> None:
        with self.assertRaisesRegex(ValueError, "fig12_matrix_resolution_scale.*0.6.*0.35.*0.5"):
            self.acceptance.normalize_fig12_parameters(
                {"fig12_matrix_resolution_scale": 0.6}, strict=True
            )

    def test_diagnostic_mode_records_requested_effective_and_clamp(self) -> None:
        result = self.acceptance.normalize_fig12_parameters(
            {"fig12_matrix_resolution_scale": 0.6}, strict=False
        )
        record = result["parameter_normalization"]["fig12_matrix_resolution_scale"]
        self.assertEqual(0.6, record["requested"])
        self.assertEqual(0.5, record["effective"])
        self.assertTrue(record["clamped"])
        self.assertEqual("above_maximum", record["reason"])
        self.assertFalse(result["promotion_eligible"])
        self.assertEqual(0.5, result["effective_parameters"]["fig12_matrix_resolution_scale"])

    def test_effective_route_contains_all_required_fig12_fields(self) -> None:
        result = self.acceptance.normalize_fig12_parameters({}, strict=True)
        required = {
            "fig12_matrix_resolution_scale", "fig12_matrix_smoothing_sigma",
            "fig12_matrix_mode", "fig12_y_minor_ticks", "fig12_panel_layout_offsets",
            "fig12_matrix_biases", "fig12_contour_label_size_offset",
            "fig12_mechanism_label_size_offset",
        }
        self.assertTrue(required.issubset(result["effective_parameters"]))
        self.assertEqual(0.5, result["effective_parameters"]["fig12_matrix_resolution_scale"])
        self.assertEqual(0.5, result["effective_parameters"]["fig12_matrix_smoothing_sigma"])

    def test_nested_legacy_label_offsets_are_normalized_to_explicit_effective_fields(self) -> None:
        result = self.acceptance.normalize_fig12_parameters({
            "fig12_label_size_offsets": {"contour": -0.3, "mechanism": -0.2}
        }, strict=True)
        effective = result["effective_parameters"]
        self.assertEqual(-0.3, effective["fig12_contour_label_size_offset"])
        self.assertEqual(-0.2, effective["fig12_mechanism_label_size_offset"])

    def test_absolute_label_sizes_are_normalized_and_recorded(self) -> None:
        result = self.acceptance.normalize_fig12_parameters({
            "fig12_label_sizes": {
                "panel": 12.0, "contour": 10.3, "mechanism": 14.2,
                "colorbar_title": 12.0, "colorbar_tick": 10.0,
            }
        }, strict=True)
        self.assertEqual(12.0, result["effective_parameters"]["fig12_label_sizes"]["panel"])
        self.assertFalse(result["parameter_normalization"]["fig12_label_sizes.panel"]["clamped"])

    def test_path_overlay_flag_requires_boolean_in_strict_mode(self) -> None:
        result = self.acceptance.normalize_fig12_parameters({}, strict=True)
        self.assertTrue(result["effective_parameters"]["fig12_path_overlays"])
        self.assertTrue(result["effective_parameters"]["fig12_axis_title_overlays"])
        self.assertEqual(11.0, result["effective_parameters"]["fig12_label_sizes"]["panel"])
        self.assertEqual(10.0, result["effective_parameters"]["fig12_label_sizes"]["mechanism"])
        result = self.acceptance.normalize_fig12_parameters({"fig12_path_overlays": True}, strict=True)
        self.assertTrue(result["effective_parameters"]["fig12_path_overlays"])
        with self.assertRaisesRegex(ValueError, "fig12_path_overlays must be boolean"):
            self.acceptance.normalize_fig12_parameters({"fig12_path_overlays": "true"}, strict=True)


class TargetVisualGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.acceptance = load("p13_visual_gates", "scripts/acceptance_hardening.py")

    def baseline_metrics(self) -> dict:
        return {
            "mae_0_1": 0.03979, "ssim_score": 0.77863, "layout_score": 0.94454,
            "edge_score": 0.74786, "color_score": 0.92316,
            "registration_shift": {"dx_px": 14.5, "dy_px": 0.0},
            "source_content_bbox": [23, 45, 802, 585],
            "actual_content_bbox": [53, 50, 801, 580],
            "source_nonwhite_ratio": 0.4, "actual_nonwhite_ratio": 0.4,
        }

    def test_fig12_requires_all_target_metrics_not_only_mae_and_layout(self) -> None:
        metrics = self.baseline_metrics()
        metrics["edge_score"] = 0.5
        gate = self.acceptance.evaluate_target_visual_gate("fig12", metrics)
        self.assertFalse(gate["visual_baseline_promoted"])
        self.assertIn("edge_score", gate["failures"])

    def test_fig12_near_threshold_margin_is_explicitly_reported(self) -> None:
        metrics = self.baseline_metrics()
        metrics.update({
            "mae_0_1": 0.0354722030,
            "ssim_score": 0.8015066981,
            "layout_score": 0.9924307822,
            "edge_score": 0.7452896833,
            "color_score": 0.9771269155,
            "registration_shift": {"dx_px": -0.5, "dy_px": -0.5},
            "source_nonwhite_ratio": 0.40,
            "actual_nonwhite_ratio": 0.40,
        })
        gate = self.acceptance.evaluate_target_visual_gate("fig12", metrics)
        self.assertTrue(gate["visual_baseline_promoted"])
        self.assertAlmostEqual(0.0002896833, gate["gate_margins"]["edge_score"], places=9)
        self.assertIn("edge_score", gate["near_threshold_metrics"])

    def test_fig15_requires_frozen_render_identity(self) -> None:
        metrics = self.baseline_metrics()
        metrics.update({"mae_0_1": 0.0325, "ssim_score": 0.8528, "layout_score": 0.9888,
                        "edge_score": 0.7559, "color_score": 0.9938,
                        "registration_shift": {"dx_px": 3.5, "dy_px": -0.5}})
        gate = self.acceptance.evaluate_target_visual_gate(
            "fig15", metrics, frozen_identity_recognized=False
        )
        self.assertFalse(gate["visual_baseline_promoted"])
        self.assertIn("frozen_render_identity_not_recognized", gate["failures"])

    def test_fig16_requires_frozen_render_identity_even_when_metrics_pass(self) -> None:
        metrics = self.baseline_metrics()
        metrics.update({"mae_0_1": 0.06591, "ssim_score": 0.69917, "layout_score": 0.99039,
                        "edge_score": 0.59916, "color_score": 0.95742,
                        "registration_shift": {"dx_px": 2.5, "dy_px": -0.5}})
        gate = self.acceptance.evaluate_target_visual_gate("fig16", metrics)
        self.assertEqual("not_promoted", gate["visual_baseline_status"])
        self.assertFalse(gate["visual_baseline_promoted"])
        self.assertIn("frozen_render_identity_not_recognized", gate["failures"])

        promoted = self.acceptance.evaluate_target_visual_gate(
            "fig16", metrics, fig16_frozen_identity_recognized=True
        )
        self.assertEqual("frozen_regression", promoted["baseline_role"])
        self.assertEqual("promoted", promoted["visual_baseline_status"])
        self.assertTrue(promoted["visual_baseline_promoted"])


class CandidateWorkerIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.worker = load("p13_candidate_worker", "scripts/origin_candidate_worker.py")

    def test_five_thousand_row_candidate_is_strict_and_consistent(self) -> None:
        candidate = {
            "fig12_matrix_resolution_scale": 0.5,
            "fig12_matrix_smoothing_sigma": 4.0,
            "fig12_y_minor_ticks": 0,
            "fig12_label_size_offsets": {"contour": -0.3, "mechanism": -0.2},
        }
        prepared = self.worker._prepare_candidate_for_build("fig12", candidate)
        self.assertEqual(0.5, prepared["candidate"]["fig12_matrix_resolution_scale"])
        self.assertTrue(prepared["parameter_normalization"]["promotion_eligible"])
        self.assertEqual(-0.3, prepared["candidate"]["fig12_label_size_offsets"]["contour"])

    def test_effective_builder_route_exports_p13_fig12_fields(self) -> None:
        route = self.worker._effective_builder_route({"builder_route": {
            "route": "native", "fig12_matrix_resolution_scale": 0.5,
            "fig12_matrix_smoothing_sigma": 4.0, "fig12_matrix_mode": "source_palette_digitized",
            "fig12_y_minor_ticks": 0, "fig12_panel_layout_offsets": {},
            "fig12_matrix_biases": {"0": -1.5}, "fig12_label_sizes": {"contour": 8.1, "mechanism": 11.0},
        }})
        self.assertEqual(0.5, route["fig12_matrix_resolution_scale"])
        self.assertEqual(4.0, route["fig12_matrix_smoothing_sigma"])
        self.assertEqual(-0.3, route["fig12_contour_label_size_offset"])
        self.assertEqual(-0.2, route["fig12_mechanism_label_size_offset"])

    def test_effective_builder_route_and_fingerprint_include_fig16_widths(self) -> None:
        route = self.worker._effective_builder_route({"builder_route": {
            "route": "gid399_stackcolumn_213_with_plot_derived_legend",
            "canvas_size": [720, 375],
            "page_size_inches": [7.2, 3.75],
            "fig16_column_gap_percent": 15.0,
            "fig16_group_frame_width": 0.5,
        }})
        self.assertEqual(15.0, route["fig16_column_gap_percent"])
        self.assertEqual(0.5, route["fig16_group_frame_width"])
        thin = self.worker.render_parameter_fingerprint(
            self.worker._render_identity_payload("fig16", route, "a" * 64)
        )["fingerprint"]
        thick_route = dict(route, fig16_group_frame_width=1.0)
        thick = self.worker.render_parameter_fingerprint(
            self.worker._render_identity_payload("fig16", thick_route, "a" * 64)
        )["fingerprint"]
        self.assertNotEqual(thin, thick)

    def test_live_evidence_run_id_uses_p15_prefix(self) -> None:
        run_id = self.worker.make_run_id("fig15", {"figure": "fig15"})
        self.assertTrue(run_id.startswith("p15-fig15-"), run_id)

    def test_relative_source_crop_resolves_from_candidate_directory_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            candidate_dir = Path(tmp) / "portable_job"
            source_dir = candidate_dir / "source"
            source_dir.mkdir(parents=True)
            source = source_dir / "fig12.png"
            source.write_bytes(b"png")
            candidate_path = candidate_dir / "fig12_candidate.json"
            candidate_path.write_text("{}", encoding="utf-8")
            resolved = self.worker._resolve_source_crop(
                {"source_crop": "source/fig12.png"}, candidate_path
            )
        self.assertEqual(source.resolve(), resolved)


class BundleValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.bundle = load("p13_bundle", "scripts/validate_release_bundle.py")

    def test_dirty_bundle_reports_cache_paths_and_broken_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "x.pyc").write_bytes(b"x")
            (root / "manifest.json").write_text(json.dumps({
                "windows": "C:/Users/example/file.json",
                "linux": "/home/example/file.json",
                "artifact": {"path": "missing.png", "exists": True},
            }), encoding="utf-8")
            result = self.bundle.validate_release_bundle(root)
        self.assertFalse(result["bundle_validation"]["clean"])
        self.assertGreater(result["bundle_validation"]["absolute_path_hits"], 0)
        self.assertGreater(result["bundle_validation"]["cache_artifact_hits"], 0)
        self.assertGreater(result["bundle_validation"]["broken_reference_hits"], 0)

    def test_clean_bundle_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "image.png").write_bytes(b"png")
            (root / "manifest.json").write_text(json.dumps({
                "artifact": {"path": "image.png", "exists": True}
            }), encoding="utf-8")
            result = self.bundle.validate_release_bundle(root)
        self.assertTrue(result["bundle_validation"]["clean"])
        self.assertTrue(result["bundle_validation"]["portable"])

    def test_nested_manifest_resolves_reference_from_its_own_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "fig12" / "evidence"
            evidence.mkdir(parents=True)
            (evidence / "post_reopen.png").write_bytes(b"png")
            (evidence / "run_artifacts.json").write_text(json.dumps({
                "artifact": {"path": "post_reopen.png", "exists": True}
            }), encoding="utf-8")
            result = self.bundle.validate_release_bundle(root)
        self.assertTrue(result["bundle_validation"]["clean"])

    def test_release_candidate_gate_requires_final_outer_bundle(self) -> None:
        release = load("p13_release_validator", "scripts/validate_release_candidate.py")
        self.assertIn("final_release_bundle_validation", release.RELEASE_GATE_ORDER)


class Fig12RoiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.roi = load("p13_roi", "scripts/fig12_roi.py")

    def test_roi_schema_has_all_required_regions(self) -> None:
        names = {item["name"] for item in self.roi.FIG12_ROIS["regions"]}
        self.assertEqual({
            "PSC_plot", "PSC_colorbar", "UC_plot", "UC_colorbar", "TR_plot",
            "TR_colorbar", "axis_titles", "mechanism_labels", "contour_labels",
        }, names)

    def test_roi_metrics_and_overlay_are_materialized(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = np.full((590, 805, 3), 255, dtype=np.uint8)
            actual = source.copy()
            source[100:150, 100:180] = 0
            actual[102:152, 104:184] = 0
            Image.fromarray(source).save(root / "source.png")
            Image.fromarray(actual).save(root / "actual.png")
            result = self.roi.evaluate_fig12_rois(
                root / "source.png", root / "actual.png", root / "overlay.png"
            )
            self.assertTrue((root / "overlay.png").exists())
        self.assertEqual("originplot.fig12_roi_metrics.v1", result["schema"])
        self.assertEqual(9, len(result["regions"]))
        self.assertIn("bbox_center_error_px", result["regions"][0]["metrics"])
        self.assertIn("edge_alignment", result["regions"][0]["metrics"])
        self.assertIn("boundary_f1", result["regions"][0]["metrics"])
        self.assertIn("chamfer_distance_px", result["regions"][0]["metrics"])
        self.assertIn("color_region_iou", result["regions"][0]["metrics"])
        self.assertEqual([], result["deferred_metrics"])

    def test_roi_boxes_match_current_three_panel_layout(self) -> None:
        regions = {item["name"]: item for item in self.roi.FIG12_ROIS["regions"]}
        self.assertEqual([98, 53, 323, 270], regions["PSC_plot"]["bbox"])
        self.assertEqual([488, 53, 715, 270], regions["UC_plot"]["bbox"])
        self.assertEqual([284, 321, 510, 546], regions["TR_plot"]["bbox"])
        self.assertEqual(6, len(regions["axis_titles"]["boxes"]))
        self.assertEqual(9, len(regions["mechanism_labels"]["boxes"]))
        self.assertEqual(15, len(regions["contour_labels"]["boxes"]))


if __name__ == "__main__":
    unittest.main()
