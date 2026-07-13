from __future__ import annotations

import unittest
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from builders.morphology_ratios import validate_morphology_ratio_contracts


def _contract() -> dict[str, object]:
    return {
        "morphology_id": "nested_series_widths",
        "scope_id": "panel_b",
        "metric": "median_visible_bar_width_px",
        "reference_item": "B",
        "expected_ratios": {"B": 1.0, "D": 0.72, "F": 0.52},
        "tolerance": 0.06,
        "ordered_descending": ["B", "D", "F"],
        "audit_stage": "postreopen_final_export",
    }


def _measurements(widths: dict[str, float]) -> list[dict[str, object]]:
    return [
        {
            "scope_id": "panel_b",
            "morphology_id": "nested_series_widths",
            "metric": "median_visible_bar_width_px",
            "item": item,
            "value": value,
        }
        for item, value in widths.items()
    ]


class MorphologyRatioContractTests(unittest.TestCase):
    def test_accepts_postexport_measurements_within_tolerance(self) -> None:
        result = validate_morphology_ratio_contracts(_measurements({"B": 35, "D": 25, "F": 18}), [_contract()])
        self.assertEqual("ok", result["status"])

    def test_rejects_missing_explicit_contract(self) -> None:
        result = validate_morphology_ratio_contracts([], [])
        self.assertEqual("failed", result["status"])
        self.assertIn("morphology_ratio_contracts", str(result["mismatches"]))

    def test_rejects_missing_postexport_measurement(self) -> None:
        result = validate_morphology_ratio_contracts(_measurements({"B": 35, "D": 25}), [_contract()])
        self.assertEqual("failed", result["status"])
        self.assertIn("measurement", str(result["mismatches"]))

    def test_rejects_out_of_tolerance_ratio(self) -> None:
        result = validate_morphology_ratio_contracts(_measurements({"B": 35, "D": 18, "F": 10}), [_contract()])
        self.assertEqual("failed", result["status"])
        self.assertIn("ratio_tolerance", str(result["mismatches"]))

    def test_rejects_declared_order_violation(self) -> None:
        result = validate_morphology_ratio_contracts(_measurements({"B": 35, "D": 25, "F": 26}), [_contract()])
        self.assertEqual("failed", result["status"])
        self.assertIn("ordered_descending", str(result["mismatches"]))


if __name__ == "__main__":
    unittest.main()
