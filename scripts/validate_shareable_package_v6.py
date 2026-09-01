from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

REQUIRED = {
    "SKILL.md",
    "README.md",
    "version.json",
    "originplot.cmd",
    "originplot/cli/main.py",
    "originplot/spec/io.py",
    "originplot/semantic/inspect.py",
    "originplot/builders/registry.py",
    "originplot/adapters/originpro.py",
    "originplot/runtime/origin_session.py",
    "benchmarks/aa2195/README.md",
}
BANNED_SUFFIXES = {".opju", ".opj", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".xlsx", ".xls", ".csv"}


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    with zipfile.ZipFile(path, "r") as archive:
        names = set(archive.namelist())
        missing = sorted(REQUIRED - names)
        if missing:
            errors.append("missing required package files: " + ", ".join(missing))
        banned = sorted(name for name in names if Path(name).suffix.lower() in BANNED_SUFFIXES)
        if banned:
            errors.append("forbidden generated/private data files: " + ", ".join(banned[:10]))
        if any(name.startswith("builders/aa2195/") for name in names):
            errors.append("AA2195 must not remain under product builders/")
        if any(name.startswith("FIGURESPEC_V5") for name in names):
            errors.append("v5 protocol documents must not remain at package root")
        if "version.json" in names:
            version = json.loads(archive.read("version.json").decode("utf-8"))
            if version.get("version") != "6.0.0":
                errors.append("package version must be 6.0.0")
            if (version.get("benchmark_evidence") or {}).get("aa2195") != "5.8.9-p18":
                errors.append("AA2195 historical evidence identity must be retained")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, required=True)
    args = parser.parse_args()
    errors = validate(args.path)
    if errors:
        print("\n".join(errors))
        return 1
    print("OriginPlot v6 shareable package validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
