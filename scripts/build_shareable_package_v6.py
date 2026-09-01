from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

EXCLUDED_DIRS = {".git", ".venv", ".editaplot-venv", "__pycache__", ".pytest_cache", "outputs", ".worktrees"}
EXCLUDED_SUFFIXES = {".opju", ".opj", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".xlsx", ".xls", ".csv"}


def should_include(path: Path, root: Path) -> bool:
    relative = path.relative_to(root)
    if any(part in EXCLUDED_DIRS for part in relative.parts):
        return False
    if path.suffix.lower() in EXCLUDED_SUFFIXES:
        return False
    return True


def build(skill_dir: Path, zip_out: Path) -> None:
    skill_dir = skill_dir.resolve()
    zip_out = zip_out.resolve()
    zip_out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_file() and should_include(path, skill_dir) and path.resolve() != zip_out:
                archive.write(path, path.relative_to(skill_dir).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skill-dir", type=Path, required=True)
    parser.add_argument("--zip-out", type=Path, required=True)
    args = parser.parse_args()
    build(args.skill_dir, args.zip_out)
    print(args.zip_out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
