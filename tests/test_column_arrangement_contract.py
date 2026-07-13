from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ColumnArrangementContractTests(unittest.TestCase):
    def test_skill_requires_per_layer_arrangement_modes(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for token in ("side_by_side", "cumulative_stack", "nested_overlap"):
            self.assertIn(token, skill)
        self.assertIn("share the zero baseline", skill)

    def test_contract_requires_native_cap_narrower_than_column(self) -> None:
        contract = (ROOT / "references" / "current-contract.md").read_text(encoding="utf-8")
        self.assertIn("native error-cap width control", contract)
        self.assertIn("strictly narrower than the corresponding visible column", contract)

    def test_skill_requires_explicit_postexport_morphology_ratio_audit(self) -> None:
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for token in (
            "morphology_ratio_contracts",
            "expected_ratios",
            "reference_item",
            "post-reopen final export",
        ):
            self.assertIn(token, skill)
        self.assertIn("Missing declarations, missing measurements, and out-of-tolerance ratios", skill)


if __name__ == "__main__":
    unittest.main()
