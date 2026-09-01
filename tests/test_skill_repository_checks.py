from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def run_repository_check(
    script: str, *, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script)],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_release_versions_are_consistent() -> None:
    result = run_repository_check("check_version_consistency.py")

    assert result.returncode == 0, result.stdout + result.stderr


def test_skill_health_does_not_require_python_311_tomllib(tmp_path: Path) -> None:
    # A shadow module makes any accidental tomllib import fail on Python 3.12,
    # reproducing the supported Python 3.10 environment in a version-neutral way.
    (tmp_path / "tomllib.py").write_text(
        'raise RuntimeError("tomllib is unavailable on Python 3.10")\n',
        encoding="utf-8",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        value for value in (str(tmp_path), env.get("PYTHONPATH")) if value
    )

    result = run_repository_check("check_skill_health.py", env=env)

    assert result.returncode == 0, result.stdout + result.stderr
