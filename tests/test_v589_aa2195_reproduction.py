from __future__ import annotations

import json
import unittest
from pathlib import Path

from tests import _v589_aa2195_reproduction_suite as _suite


# Preserve the full historical AA2195 regression suite byte-for-byte in the
# non-discovered module above. Re-export its helper surface because several
# focused regression modules import fakes directly from this canonical path.
# TestCase classes are localized so pytest/unittest collect the same suite from
# this file, while the two release-label assertions below are overridden for
# the 5.9.1 package revision. Contract/evidence identity remains 5.8.9-p18.
for _name, _obj in vars(_suite).items():
    if _name.startswith("__") or _name == "VersionContractTests":
        continue
    if isinstance(_obj, type) and issubclass(_obj, unittest.TestCase):
        globals()[_name] = type(_name, (_obj,), {"__module__": __name__})
    else:
        globals()[_name] = _obj

# Do not leave a TestCase class reachable through loop-temporary globals;
# pytest's unittest collector inspects module values as well as public names.
del _name, _obj


class VersionContractTests(_suite.VersionContractTests):
    def test_skill_documents_v589_authorized_attach_and_visual_closure(self) -> None:
        root = Path(__file__).resolve().parents[1]
        skill = (root / "SKILL.md").read_text(encoding="utf-8-sig")
        runtime = (root / "references" / "origin-runtime.md").read_text(encoding="utf-8-sig")

        self.assertIn("OriginPlot Skill v5.9.1", skill)
        self.assertIn("administrator privilege for the entire live lifecycle", skill)
        self.assertIn("E121_ATTACH_POLICY_VIOLATION", skill)
        self.assertIn("op.detach()", skill)
        self.assertIn("administrator-started Origin instance", runtime)

    def test_test_runner_reports_v589_p12_schema(self) -> None:
        root = Path(__file__).resolve().parents[1]
        runner = (root / "scripts" / "run_all_tests.py").read_text(encoding="utf-8-sig")
        versions = json.loads((root / "version.json").read_text(encoding="utf-8-sig"))
        self.assertIn("load_versions", runner)
        self.assertIn("VERSIONS.contract_version", runner)
        self.assertEqual("5.9.1", versions["release_version"])
        self.assertEqual("5.8.9-p18", versions["contract_version"])
        self.assertEqual("5.8.9-p18", versions["evidence_version"])


if __name__ == "__main__":
    unittest.main()
