from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


class ReleaseVersionModelTests(unittest.TestCase):
    def test_version_source_declares_release_contract_and_evidence(self) -> None:
        path = ROOT / "version.json"
        self.assertTrue(path.is_file(), "version.json must be the canonical version source")
        self.assertEqual(
            {
                "release_version": "5.9.0",
                "contract_version": "5.8.9-p18",
                "evidence_version": "5.8.9-p18",
            },
            json.loads(path.read_text(encoding="utf-8-sig")),
        )

    def test_version_loader_exposes_strict_canonical_values(self) -> None:
        path = ROOT / "scripts" / "versioning.py"
        self.assertTrue(path.is_file(), "scripts/versioning.py must load version.json")
        versioning = load_module("originplot_versioning_test", path)
        versions = versioning.load_versions(ROOT)
        self.assertEqual("5.9.0", versions.release_version)
        self.assertEqual("5.8.9-p18", versions.contract_version)
        self.assertEqual("5.8.9-p18", versions.evidence_version)

    def test_active_version_consumers_import_the_canonical_loader(self) -> None:
        for relative in (
            "scripts/run_all_tests.py",
            "scripts/origin_candidate_worker.py",
            "scripts/materialize_live_evidence.py",
            "scripts/inspect_official_templates.py",
            "scripts/validate_release_candidate.py",
            "scripts/build_shareable_package.py",
            "scripts/validate_shareable_package_v5.py",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8-sig")
            self.assertIn("load_versions", text, relative)

    def test_offline_ci_uses_release_version_in_package_name(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "offline-ci.yml").read_text(encoding="utf-8")
        self.assertIn("originplot-skill-v5.9.0.zip", workflow)
        self.assertNotIn("originplot-skill-v5.8.9-p14.zip", workflow)

    def test_shareable_package_contains_version_source_and_reports_release(self) -> None:
        builder = load_module(
            "originplot_versioned_package_builder_test",
            ROOT / "scripts" / "build_shareable_package.py",
        )
        with tempfile.TemporaryDirectory() as tmp:
            archive_path = Path(tmp) / "originplot-skill.zip"
            result = builder.build_zip(ROOT, archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                packaged = json.loads(archive.read("originplot-skill/version.json"))
        self.assertEqual("5.9.0", result["release_version"])
        self.assertEqual("5.8.9-p18", result["contract_version"])
        self.assertEqual("5.8.9-p18", result["evidence_version"])
        self.assertEqual("5.9.0", packaged["release_version"])

    def test_public_evidence_keeps_original_contract_version(self) -> None:
        evidence = json.loads(
            (ROOT / "references" / "aa2195-release-evidence.json").read_text(encoding="utf-8")
        )
        self.assertEqual("5.9.0", evidence["release_version"])
        self.assertEqual("5.8.9-p18", evidence["skill_version"])
        self.assertNotEqual("5.9.0", evidence["skill_version"])
        self.assertEqual("fresh_extract", evidence["batch"]["source_data_policy"])
        self.assertTrue(evidence["batch"]["same_run_fresh_source_verified"])
        self.assertEqual("batch_started", evidence["batch"]["origin_launch_mode"])

    def test_shareable_validator_requires_version_and_package_policy_runtime(self) -> None:
        validator = load_module(
            "originplot_versioned_package_validator_requirements",
            ROOT / "scripts" / "validate_shareable_package_v5.py",
        )
        self.assertTrue(
            {
                "originplot-skill/scripts/versioning.py",
                "originplot-skill/scripts/package_policy.py",
                "originplot-skill/scripts/validate_public_evidence_index.py",
            }.issubset(validator.REQUIRED)
        )


if __name__ == "__main__":
    unittest.main()
