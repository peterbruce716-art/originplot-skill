from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    required = [
        ROOT / "SKILL.md",
        ROOT / "README.md",
        ROOT / "pyproject.toml",
        ROOT / "CHANGELOG.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"Missing required project files: {missing}")

    forbidden = []
    for path in ROOT.rglob("*"):
        if path.is_file() and path.name in {".DS_Store", "Thumbs.db"}:
            forbidden.append(str(path.relative_to(ROOT)))

    if forbidden:
        raise SystemExit(f"Repository hygiene failure: {forbidden}")

    print("Skill repository hygiene OK")


if __name__ == "__main__":
    main()
