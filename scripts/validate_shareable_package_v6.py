from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path

REQUIRED = {
    "SKILL.md",
    "README.md",
    "LICENSE",
    "version.json",
    "originplot.cmd",
    "pyproject.toml",
    "requirements-core.txt",
    "requirements-origin.txt",
    "originplot/cli/main.py",
    "originplot/controller.py",
    "originplot/spec/io.py",
    "originplot/semantic/inspect.py",
    "originplot/builders/registry.py",
    "originplot/adapters/originpro.py",
    "originplot/runtime/origin_session.py",
    "scripts/origin_profile_worker.py",
    "scripts/run_origin_profile_worker_elevated.ps1",
    "scripts/search_official_templates.py",
    "capabilities/origin-2022-v6.json",
    "capabilities/origin-2024-v6.json",
    "capabilities/origin-2026-v6.json",
    "schemas/figurespec-v6.schema.json",
    "schemas/capabilities-v6.schema.json",
    "schemas/doctor-v3.schema.json",
    "schemas/operation-plan-v1.schema.json",
    "schemas/origin-worker-task-v2.schema.json",
    "schemas/origin-worker-result-v2.schema.json",
}

BANNED_SUFFIXES = {
    ".opju",
    ".opj",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".xlsx",
    ".xls",
    ".csv",
}

BANNED_PREFIXES = (
    "benchmarks/",
    "adapters/",
    "builders/",
    "runtime/",
    "references/",
    "examples/candidates/",
)

BANNED_FILES = {
    "scripts/origin_candidate_worker.py",
    "scripts/originplot_compile_v5.py",
    "scripts/originplot_runtime_v5.py",
    "scripts/validate_shareable_package_v5.py",
    "schemas/capabilities-v5.schema.json",
    "schemas/figurespec-v5.schema.json",
    "schemas/operation-plan-v5.schema.json",
    "schemas/run-manifest-v5.schema.json",
    "capabilities/origin-2022-v5.json",
    "capabilities/origin-2022.json",
    "capabilities/origin-2024.json",
    "capabilities/origin-2026.json",
}


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    with zipfile.ZipFile(path, "r") as archive:
        names = set(archive.namelist())
        missing = sorted(REQUIRED - names)
        if missing:
            errors.append("missing required v6 package files: " + ", ".join(missing))

        banned_binary = sorted(name for name in names if Path(name).suffix.lower() in BANNED_SUFFIXES)
        if banned_binary:
            errors.append("forbidden generated/private data files: " + ", ".join(banned_binary[:10]))

        legacy_prefix = sorted(name for name in names if name.startswith(BANNED_PREFIXES))
        if legacy_prefix:
            errors.append("default v6 package contains benchmark/legacy roots: " + ", ".join(legacy_prefix[:10]))

        legacy_files = sorted(BANNED_FILES & names)
        if legacy_files:
            errors.append("default v6 package contains legacy files: " + ", ".join(legacy_files))

        if any("-v5" in Path(name).name.lower() for name in names):
            errors.append("default v6 package must not ship v5-named contracts")

        if "version.json" in names:
            version = json.loads(archive.read("version.json").decode("utf-8"))
            if version.get("version") != "6.0.0":
                errors.append("package version must be 6.0.0")
            if (version.get("benchmark_evidence") or {}).get("aa2195") != "5.8.9-p18":
                errors.append("AA2195 historical evidence identity must remain recorded in version metadata")

        for profile in (
            "capabilities/origin-2022-v6.json",
            "capabilities/origin-2024-v6.json",
            "capabilities/origin-2026-v6.json",
        ):
            if profile not in names:
                continue
            payload = json.loads(archive.read(profile).decode("utf-8"))
            if payload.get("schema") != "originplot.capabilities.v6":
                errors.append(f"{profile} must use originplot.capabilities.v6")
            if payload.get("live_evidence_primitives") != []:
                errors.append(f"{profile} must not promote live evidence in the offline package")
            authorization = payload.get("authorization") or {}
            if authorization.get("origin_worker") != "administrator_required":
                errors.append(f"{profile} must preserve administrator-only Origin workers")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, required=True)
    args = parser.parse_args()
    errors = validate(args.path)
    if errors:
        print("\n".join(errors))
        return 1
    print("OriginPlot v6 compact shareable package validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
