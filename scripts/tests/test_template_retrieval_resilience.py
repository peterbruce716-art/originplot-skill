import importlib.util
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "retrieve_official_template.py"
SPEC = importlib.util.spec_from_file_location("retrieve_official_template", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class TemplateRetrievalTests(unittest.TestCase):
    def test_official_host_allowlist(self):
        self.assertTrue(MODULE.is_allowed_url("https://blog.originlab.com/ftp/example.zip"))
        self.assertTrue(MODULE.is_allowed_url("https://d2.example.cloudfront.net/example.zip"))
        self.assertFalse(MODULE.is_allowed_url("http://originlab.com/example.zip"))
        self.assertFalse(MODULE.is_allowed_url("https://example.com/example.zip"))

    def test_valid_origin_archive(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "candidate.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("candidate.opju", b"test")
            result = MODULE.validate_archive(archive)
            self.assertEqual(result["project_members"], ["candidate.opju"])
            self.assertEqual(len(result["sha256"]), 64)

    def test_rejects_archive_without_origin_project(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "candidate.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("readme.txt", "not a project")
            with self.assertRaisesRegex(ValueError, "no Origin project"):
                MODULE.validate_archive(archive)

    def test_rejects_unsafe_member(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / "candidate.zip"
            with zipfile.ZipFile(archive, "w") as handle:
                handle.writestr("../candidate.opju", b"test")
            with self.assertRaisesRegex(ValueError, "unsafe ZIP member"):
                MODULE.validate_archive(archive)


if __name__ == "__main__":
    unittest.main()
