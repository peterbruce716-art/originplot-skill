from __future__ import annotations

from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


CHECKS = [
    ("version", "check_version_consistency.py"),
    ("health", "check_skill_health.py"),
    ("hygiene", "check_skill_hygiene.py"),
]


def main() -> None:
    failed = []
    for name, script in CHECKS:
        path = ROOT / "scripts" / script
        if not path.exists():
            failed.append(f"missing:{script}")
            continue
        result = subprocess.run([sys.executable, str(path)], cwd=ROOT)
        if result.returncode != 0:
            failed.append(name)

    if failed:
        raise SystemExit(f"Skill doctor failed: {', '.join(failed)}")

    print("OriginPlot skill doctor: OK")


if __name__ == "__main__":
    main()
