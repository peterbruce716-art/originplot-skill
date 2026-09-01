from __future__ import annotations

from pathlib import Path

from check_version_consistency import read_pyproject_version

ROOT = Path(__file__).resolve().parents[1]

REQUIRED = (
    "SKILL.md",
    "README.md",
    "CHANGELOG.md",
    "pyproject.toml",
)


def main() -> None:
    missing = [name for name in REQUIRED if not (ROOT / name).exists()]
    if missing:
        raise SystemExit(f"Missing required skill files: {missing}")

    version = read_pyproject_version()

    checks = {
        "required_files": True,
        "package_version": version,
        "skill_file": True,
    }
    print(f"Skill health OK: {checks}")


if __name__ == "__main__":
    main()
