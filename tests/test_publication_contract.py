from __future__ import annotations

import copy
import importlib.util
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "scripts" / "validate_publication_contract.py"
SPEC = importlib.util.spec_from_file_location("validate_publication_contract", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class PublicationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = json.loads((ROOT / "examples" / "publication_contract.example.json").read_text(encoding="utf-8"))

    def codes(self, report):
        return {item["code"] for item in report["errors"]}

    def test_example_passes(self):
        report = MODULE.validate(copy.deepcopy(self.valid))
        self.assertEqual("ok", report["status"])
        self.assertEqual(2, report["panel_count"])

    def test_rejects_unmapped_panel_and_source(self):
        contract = copy.deepcopy(self.valid)
        contract["panels"].append({"id": "c", "kind": "image", "question": "Where is deformation localized?"})
        report = MODULE.validate(contract)
        self.assertEqual("failed", report["status"])
        self.assertIn("E054_HIERARCHY_COVERAGE", self.codes(report))
        self.assertIn("E067_SOURCE_COVERAGE", self.codes(report))

    def test_rejects_incomplete_quantitative_statistics(self):
        contract = copy.deepcopy(self.valid)
        contract["statistics_and_uncertainty"][1].pop("n_definition")
        report = MODULE.validate(contract)
        self.assertIn("E084_STATISTICS_FIELDS", self.codes(report))

    def test_rejects_color_only_publication_profile(self):
        contract = copy.deepcopy(self.valid)
        contract["accessibility"]["non_color_encoding"] = False
        report = MODULE.validate(contract)
        self.assertIn("E091_ACCESSIBILITY_FAIL", self.codes(report))

    def test_source_fidelity_reports_accessibility_warning(self):
        contract = copy.deepcopy(self.valid)
        contract["style_profile"] = "source_fidelity"
        contract["target_journal"] = "source reference"
        contract.pop("journal_requirements")
        contract["acceptance_tracks"] = {"source_fidelity": True, "publication_style": False}
        contract["accessibility"]["grayscale_legible"] = False
        report = MODULE.validate(contract)
        self.assertEqual("ok", report["status"])
        self.assertIn("W091_SOURCE_ACCESSIBILITY", {item["code"] for item in report["warnings"]})

    def test_image_panel_requires_raster_export(self):
        contract = copy.deepcopy(self.valid)
        contract["panels"][0]["kind"] = "mixed"
        report = MODULE.validate(contract)
        self.assertIn("E103_RASTER_EXPORT", self.codes(report))

    def test_custom_profile_requires_complete_tokens(self):
        contract = copy.deepcopy(self.valid)
        contract["style_profile"] = "custom"
        contract["custom_style_tokens"] = {"font_family": "Times New Roman"}
        report = MODULE.validate(contract)
        self.assertIn("E021_CUSTOM_STYLE", self.codes(report))

    def test_materials_profile_routes_to_domain_qa(self):
        contract = copy.deepcopy(self.valid)
        contract["domain_profile"] = "materials_ebsd"
        report = MODULE.validate(contract)
        self.assertEqual("ok", report["status"])
        self.assertIn("W130_MATERIALS_QA", {item["code"] for item in report["warnings"]})

    def test_shareable_validator_requires_publication_contract_surface(self):
        validator = (ROOT / "scripts" / "validate_shareable_package_v5.py").read_text(encoding="utf-8")
        for relative in (
            "schemas/publication-contract-v1.schema.json",
            "examples/publication_contract.example.json",
            "scripts/validate_publication_contract.py",
            "references/materials-figure-qa.md",
        ):
            self.assertIn(f'originplot-skill/{relative}', validator)


if __name__ == "__main__":
    unittest.main()
