from __future__ import annotations

import argparse
import json
import os
import zipfile
from pathlib import Path

try:
    from scripts.versioning import load_versions
    from scripts.package_policy import (
        EXCLUDED_FILE_NAMES,
        FORBIDDEN_ARTIFACT_SUFFIXES,
        contains_local_environment_path,
        is_excluded_directory_name,
        is_local_interpreter_binary,
    )
except ModuleNotFoundError:
    from versioning import load_versions
    from package_policy import (
        EXCLUDED_FILE_NAMES,
        FORBIDDEN_ARTIFACT_SUFFIXES,
        contains_local_environment_path,
        is_excluded_directory_name,
        is_local_interpreter_binary,
    )

SKIP_NAMES = {"FIGURESPEC_PROTOCOL.md", "FIGURESPEC_V4_PROTOCOL.md", "originplot_runtime_v4.py", "image_qa.py", "image_qa_v2.py", "image_qa_v3.py", "validate_shareable_package_v4.py", "validate_figurespec_v2.py", "origin_only_minimal_figurespec_v2.json", "compiled_ir_v4_example.json", "editable_reproduction_v4.json", "operation_plan_v4_example.json", "origin-2022-capabilities-v4.example.json", "adapter_modules_v5_1.example.json", "adapter_configs_v5_1.example.json"}
AUTHORIZED_SOURCE_PLACEHOLDER = "AUTHORIZED_LOCAL_SOURCE_REQUIRED"
AUTHORIZED_SOURCE_MARKER = "Marker file required for local source authorization contract.\n"
VERSIONS = load_versions()


def should_include(path: Path) -> bool:
    return (
        path.name not in SKIP_NAMES
        and path.name.casefold() not in EXCLUDED_FILE_NAMES
        and not contains_local_environment_path(path.as_posix())
        and not is_local_interpreter_binary(path.as_posix())
        and path.suffix.casefold() not in FORBIDDEN_ARTIFACT_SUFFIXES
    )


def iter_package_files(skill_dir: Path):
    for current, directory_names, file_names in os.walk(
        skill_dir,
        topdown=True,
        followlinks=False,
    ):
        current_path = Path(current)
        directory_names[:] = sorted(
            name
            for name in directory_names
            if not is_excluded_directory_name(name)
            and not (current_path / name).is_symlink()
        )
        for name in sorted(file_names):
            file = current_path / name
            if file.is_symlink():
                continue
            relative = file.relative_to(skill_dir)
            if file.is_file() and should_include(relative):
                yield file, relative


def package_payload(file: Path, relative: Path) -> bytes | None:
    if relative.parts[:2] != ("examples", "candidates") or relative.suffix.lower() != ".json":
        return None
    candidate = json.loads(file.read_text(encoding="utf-8-sig"))
    if "source_crop" not in candidate:
        return None
    candidate["source_crop"] = AUTHORIZED_SOURCE_PLACEHOLDER
    candidate["source_crop_policy"] = "supply_an_authorized_local_path_before_live_execution"
    return (json.dumps(candidate, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build_zip(skill_dir: Path, zip_out: Path) -> dict[str, object]:
    if not skill_dir.exists() or not skill_dir.is_dir():
        raise FileNotFoundError(f"OriginPlot skill directory does not exist: {skill_dir}")
    skill_dir = skill_dir.resolve()
    zip_out.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file, relative in iter_package_files(skill_dir):
            arcname = f"originplot-skill/{relative.as_posix()}"
            payload = package_payload(file, relative)
            if payload is None:
                archive.write(file, arcname=arcname)
            else:
                archive.writestr(arcname, payload)
            entries.append(arcname)
        marker_arcname = f"originplot-skill/{AUTHORIZED_SOURCE_PLACEHOLDER}"
        if marker_arcname not in entries:
            archive.writestr(marker_arcname, AUTHORIZED_SOURCE_MARKER.encode("utf-8"))
            entries.append(marker_arcname)
    return {
        "schema": "originplot.package_build.v5.5",
        **VERSIONS.as_dict(),
        "zip": str(zip_out),
        "entry_count": len(entries),
        "entries": entries,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build OriginPlot v5.5 shareable core package.")
    parser.add_argument("--skill-dir", required=True, type=Path)
    parser.add_argument("--zip-out", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        result = build_zip(args.skill_dir, args.zip_out)
    except FileNotFoundError as exc:
        result = {
            "schema": "originplot.package_build.v5.5",
            **VERSIONS.as_dict(),
            "status": "failed",
            "failures": [{"code": "source_skill_dir_missing", "message": str(exc)}],
        }
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 2
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "schema": "originplot.package_build.v5.5",
            **VERSIONS.as_dict(),
            "status": "failed",
            "failures": [{"code": "package_build_failed", "message": str(exc)}],
        }
        text = json.dumps(result, ensure_ascii=False, indent=2)
        if args.json_out:
            args.json_out.parent.mkdir(parents=True, exist_ok=True)
            args.json_out.write_text(text + "\n", encoding="utf-8")
        print(text)
        return 2
    result["status"] = "ok"
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
