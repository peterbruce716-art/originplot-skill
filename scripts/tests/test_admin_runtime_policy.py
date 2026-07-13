import importlib.util
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1]


def load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, SCRIPT_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class AdminRuntimePolicyTests(unittest.TestCase):
    def test_admin_preflight_passes_only_when_elevated(self):
        module = load_module("assert_admin_preflight", "assert_admin_preflight.py")
        self.assertEqual("ok", module.build_record(True)["status"])
        failed = module.build_record(False)
        self.assertEqual("failed", failed["status"])
        self.assertEqual("E120_ENVIRONMENT_MISMATCH", failed["error_code"])
        self.assertEqual(
            "restart_entire_workflow_in_elevated_powershell", failed["action"]
        )

    def test_demo_watermark_requires_clean_full_restart(self):
        module = load_module("assert_admin_preflight_restart", "assert_admin_preflight.py")
        directive = module.demo_restart_directive(
            "E122_ORIGIN_DEMO_EXPORT_BLOCKED", python_is_admin=True
        )
        self.assertTrue(directive["current_run_invalidated"])
        self.assertEqual("administrator_preflight", directive["restart_from"])
        self.assertTrue(directive["new_run_id_required"])
        self.assertTrue(directive["clean_output_root_required"])
        self.assertFalse(directive["reuse_current_run_artifacts"])
        self.assertEqual(1, directive["max_full_elevated_restarts"])

    def test_non_watermark_error_has_no_restart_directive(self):
        module = load_module("assert_admin_preflight_other", "assert_admin_preflight.py")
        self.assertIsNone(
            module.demo_restart_directive("E400_STRUCTURE_MISMATCH", python_is_admin=True)
        )


if __name__ == "__main__":
    unittest.main()
