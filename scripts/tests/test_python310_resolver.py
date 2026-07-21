from __future__ import annotations

import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PWSH = Path(r"C:\Program Files\PowerShell\7\pwsh.exe")
RESOLVER = ROOT / "scripts" / "resolve_python310.ps1"


class Python310ResolverTests(unittest.TestCase):
    def test_resolves_supported_install_without_py_launcher_registration(self) -> None:
        completed = subprocess.run(
            [
                str(PWSH),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(RESOLVER),
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertEqual(0, completed.returncode, completed.stderr)
        resolved = Path(completed.stdout.strip())
        self.assertTrue(resolved.is_file(), completed.stdout)
        version = subprocess.run(
            [str(resolved), "-c", "import platform; print(platform.python_version())"],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        ).stdout.strip()
        self.assertTrue(version.startswith("3.10."), version)

    def test_rejects_explicit_non_python310(self) -> None:
        completed = subprocess.run(
            [
                str(PWSH),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(RESOLVER),
                "-PythonExe",
                r"C:\Python314\python.exe",
            ],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("E120_ENVIRONMENT_MISMATCH", completed.stderr)


if __name__ == "__main__":
    unittest.main()
