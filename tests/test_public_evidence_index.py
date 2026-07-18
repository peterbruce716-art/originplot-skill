from __future__ import annotations

import importlib.util
import json
import math
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INDEX_PATH = ROOT / "references" / "aa2195-release-evidence.json"
VALIDATOR_PATH = ROOT / "scripts" / "validate_public_evidence_index.py"


def load_validator():
    if not VALIDATOR_PATH.is_file():
        raise AssertionError("scripts/validate_public_evidence_index.py is required")
    spec = importlib.util.spec_from_file_location("originplot_public_evidence_validator_test", VALIDATOR_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {VALIDATOR_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fresh_index() -> dict:
    return json.loads(INDEX_PATH.read_text(encoding="utf-8-sig"))


class PublicEvidenceIndexTests(unittest.TestCase):
    def test_index_declares_public_verification_limits(self) -> None:
        payload = fresh_index()
        self.assertEqual("maintainer_attested_index", payload.get("verification_level"))
        self.assertIs(False, payload.get("public_artifacts_reproducible"))
        self.assertIs(False, payload.get("independent_pixel_verification_possible"))
        self.assertEqual(
            "copyrighted_or_authorized_assets_not_redistributed",
            payload.get("reason"),
        )

    def test_canonical_index_passes_machine_validation_without_live_promotion(self) -> None:
        validator = load_validator()

        result = validator.validate(fresh_index())

        self.assertEqual("ok", result["status"], result["failures"])
        self.assertEqual("maintainer_attested_index", result["verification_level"])
        self.assertIs(False, result["live_origin_verified"])
        self.assertIs(False, result["pass_eligible"])
        self.assertIs(False, result["independent_pixel_verification_possible"])

    def test_duplicate_figure_is_rejected(self) -> None:
        validator = load_validator()
        payload = fresh_index()
        payload["routes"][1]["figure"] = "fig3"

        result = validator.validate(payload)

        self.assertIn("duplicate_or_incomplete_figure_set", {item["code"] for item in result["failures"]})

    def test_invalid_sha256_is_rejected(self) -> None:
        validator = load_validator()
        payload = fresh_index()
        payload["routes"][0]["manifest_sha256"] = "not-a-sha256"

        result = validator.validate(payload)

        self.assertIn("invalid_sha256", {item["code"] for item in result["failures"]})

    def test_nonfinite_metric_is_rejected(self) -> None:
        validator = load_validator()
        payload = fresh_index()
        payload["routes"][0]["metrics"]["mae_0_1"] = math.nan

        result = validator.validate(payload)

        self.assertIn("invalid_metric", {item["code"] for item in result["failures"]})

    def test_incomplete_fig16_boundary_audit_is_rejected(self) -> None:
        validator = load_validator()
        payload = fresh_index()
        fig16 = next(route for route in payload["routes"] if route["figure"] == "fig16")
        fig16["bar_boundary"]["actual_segment_count"] = 20

        result = validator.validate(payload)

        self.assertIn("incomplete_fig16_boundary_audit", {item["code"] for item in result["failures"]})

    def test_missing_batch_attestation_is_rejected(self) -> None:
        validator = load_validator()
        payload = fresh_index()
        payload.pop("batch")

        result = validator.validate(payload)

        self.assertIn("invalid_batch_attestation", {item["code"] for item in result["failures"]})

    def test_fresh_batch_requires_same_run_source_and_batch_started_origin(self) -> None:
        validator = load_validator()
        payload = fresh_index()
        payload["batch"]["same_run_fresh_source_verified"] = False

        result = validator.validate(payload)

        self.assertIn("invalid_batch_attestation", {item["code"] for item in result["failures"]})

        payload = fresh_index()
        payload["batch"]["origin_launch_mode"] = "preexisting_visible"
        result = validator.validate(payload)
        self.assertIn("invalid_batch_attestation", {item["code"] for item in result["failures"]})

    def test_malformed_run_id_is_rejected(self) -> None:
        validator = load_validator()
        payload = fresh_index()
        payload["routes"][0]["run_id"] = "x"

        result = validator.validate(payload)

        self.assertIn("invalid_run_id", {item["code"] for item in result["failures"]})

    def test_incomplete_metric_contract_is_rejected(self) -> None:
        validator = load_validator()
        payload = fresh_index()
        payload["routes"][0]["metrics"] = {"unknown": 0.0}

        result = validator.validate(payload)

        self.assertIn("invalid_metric_set", {item["code"] for item in result["failures"]})

    def test_missing_route_attestation_status_is_rejected(self) -> None:
        validator = load_validator()
        payload = fresh_index()
        payload["routes"][0].pop("status")

        result = validator.validate(payload)

        self.assertIn("invalid_route_attestation", {item["code"] for item in result["failures"]})

    def test_boolean_fig16_boundary_error_is_rejected(self) -> None:
        validator = load_validator()
        payload = fresh_index()
        fig16 = next(route for route in payload["routes"] if route["figure"] == "fig16")
        fig16["bar_boundary"]["max_abs_boundary_error_px"] = False

        result = validator.validate(payload)

        self.assertIn("incomplete_fig16_boundary_audit", {item["code"] for item in result["failures"]})

    def test_non_object_payload_returns_structured_failure(self) -> None:
        validator = load_validator()

        result = validator.validate([])

        self.assertEqual("failed", result["status"])
        self.assertEqual("invalid_payload_type", result["failures"][0]["code"])


if __name__ == "__main__":
    unittest.main()
