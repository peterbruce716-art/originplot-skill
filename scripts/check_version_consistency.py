from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        raise RuntimeError("Missing project version in pyproject.toml")
    return match.group(1)


def read_changelog_version() -> str:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    match = re.search(r"^##\s+([0-9]+\.[0-9]+\.[0-9]+)", text, re.MULTILINE)
    if not match:
        raise RuntimeError("Missing changelog release version")
    return match.group(1)


def read_skill_version() -> str:
    text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    match = re.search(r"OriginPlot Skill v([0-9]+\.[0-9]+\.[0-9]+)", text)
    if not match:
        raise RuntimeError("Missing SKILL version")
    return match.group(1)


def read_version_json_release() -> str:
    """Return the release version that scripts/versioning.py exposes.

    This file also carries the retained AA2195 benchmark evidence identity,
    which is deliberately independent of the product version and is therefore
    not compared here.
    """
    payload = json.loads((ROOT / "version.json").read_text(encoding="utf-8-sig"))
    version = payload.get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("Missing release version in version.json")
    return version


def main() -> None:
    versions = {
        "pyproject": read_pyproject_version(),
        "changelog": read_changelog_version(),
        "skill": read_skill_version(),
        "version_json": read_version_json_release(),
    }
    if len(set(versions.values())) != 1:
        raise SystemExit(f"Version mismatch: {versions}")
    print(f"Version consistency OK: {next(iter(versions.values()))}")


if __name__ == "__main__":
    main()
