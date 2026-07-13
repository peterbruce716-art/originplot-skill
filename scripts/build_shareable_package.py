from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


SKIP_PARTS = {"__pycache__", ".pytest_cache", ".git", "tmp_v5_validation", "local_python", "runs", "comparison_boards", "outputs", "data", "raw_data", "private"}
SKIP_NAMES = {"FIGURESPEC_PROTOCOL.md", "FIGURESPEC_V4_PROTOCOL.md", "originplot_runtime_v4.py", "image_qa.py", "image_qa_v2.py", "image_qa_v3.py", "validate_shareable_package_v4.py", "validate_figurespec_v2.py", "origin_only_minimal_figurespec_v2.json", "compiled_ir_v4_example.json", "editable_reproduction_v4.json", "operation_plan_v4_example.json", "origin-2022-capabilities-v4.example.json", "adapter_modules_v5_1.example.json", "adapter_configs_v5_1.example.json"}
AUTHORIZED_SOURCE_PLACEHOLDER = "AUTHORIZED_LOCAL_SOURCE_REQUIRED"
AUTHORIZED_SOURCE_MARKER = "Marker file required for local source authorization contract.\n"


def should_include(path: Path) -> bool:
    forbidden_suffixes = {".pyc", ".pyo", ".opju", ".opj", ".ogwu", ".oggu", ".xlsx", ".xls", ".csv", ".pdf", ".png", ".jpg", ".jpeg", ".zip", ".rar", ".lck", ".log", ".env"}
    suffix_allowed = path.suffix.lower() not in forbidden_suffixes
    return path.name not in SKIP_NAMES and not any(part in SKIP_PARTS for part in path.parts) and suffix_allowed


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
    skill_dir = skill_dir.resolve()
    zip_out.parent.mkdir(parents=True, exist_ok=True)
    entries = []
    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file in sorted(skill_dir.rglob("*")):
            relative = file.relative_to(skill_dir)
            if not file.is_file() or not should_include(relative):
                continue
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
    return {"schema": "originplot.package_build.v5.5", "zip": str(zip_out), "entry_count": len(entries), "entries": entries}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build OriginPlot v5.5 shareable core package.")
    parser.add_argument("--skill-dir", required=True, type=Path)
    parser.add_argument("--zip-out", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = build_zip(args.skill_dir, args.zip_out)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
