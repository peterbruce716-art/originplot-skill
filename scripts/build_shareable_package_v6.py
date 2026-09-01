from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

ROOT_FILES = {
    "SKILL.md",
    "README.md",
    "LICENSE",
    "version.json",
    "originplot.cmd",
    "pyproject.toml",
    "requirements-core.txt",
    "requirements-origin.txt",
}

RUNTIME_FILES = {
    "schemas/figurespec-v6.schema.json",
    "schemas/capabilities-v6.schema.json",
    "schemas/doctor-v3.schema.json",
    "schemas/operation-plan-v1.schema.json",
    "schemas/origin-worker-task-v2.schema.json",
    "schemas/origin-worker-result-v2.schema.json",
}

PRODUCT_PREFIXES = ("originplot/",)


def should_include(path: Path, root: Path) -> bool:
    relative = path.relative_to(root).as_posix()
    if relative in ROOT_FILES or relative in RUNTIME_FILES:
        return True
    return any(relative.startswith(prefix) for prefix in PRODUCT_PREFIXES)


def build(skill_dir: Path, zip_out: Path) -> None:
    skill_dir = skill_dir.resolve()
    zip_out = zip_out.resolve()
    zip_out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(skill_dir.rglob("*")):
            if path.is_file() and path.resolve() != zip_out and should_include(path, skill_dir):
                archive.write(path, path.relative_to(skill_dir).as_posix())


def main() -> int:
    parser = argparse.ArgumentParser(description="Build the compact OriginPlot v6 runtime package.")
    parser.add_argument("--skill-dir", type=Path, required=True)
    parser.add_argument("--zip-out", type=Path, required=True)
    args = parser.parse_args()
    build(args.skill_dir, args.zip_out)
    print(args.zip_out.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
