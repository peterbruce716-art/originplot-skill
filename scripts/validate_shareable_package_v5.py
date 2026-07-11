from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path


REQUIRED = {"originplot-skill/README.md", "originplot-skill/LICENSE", "originplot-skill/SKILL.md", "originplot-skill/FIGURESPEC_V5_5_LIVE_SEMANTIC_CLOSURE_PROTOCOL.md", "originplot-skill/scripts/operation_maturity.py", "originplot-skill/scripts/visual_evidence_engine.py", "originplot-skill/scripts/semantic_figure_benchmark.py", "originplot-skill/scripts/validate_benchmark_evidence_package.py", "originplot-skill/scripts/materialize_live_evidence.py", "originplot-skill/scripts/build_combined_review_package.py", "originplot-skill/scripts/run_all_tests.py", "originplot-skill/schemas/inspection-v2.schema.json", "originplot-skill/operation_registry/operation_maturity_v1.json"}
SKIP_PARTS = {"__pycache__", ".pytest_cache", "tmp_v5_validation", "local_python", "runs", "comparison_boards"}
SKIP_NAMES = {"FIGURESPEC_PROTOCOL.md", "FIGURESPEC_V4_PROTOCOL.md", "originplot_runtime_v4.py", "image_qa.py", "image_qa_v2.py", "image_qa_v3.py", "validate_figurespec_v2.py", "origin_only_minimal_figurespec_v2.json", "compiled_ir_v4_example.json", "editable_reproduction_v4.json", "operation_plan_v4_example.json", "origin-2022-capabilities-v4.example.json", "adapter_modules_v5_1.example.json", "adapter_configs_v5_1.example.json"}
FORBIDDEN_FRAGMENTS = {"__pycache__", ".pytest_cache", "tmp_v5_validation", "originplot_runtime_v4.py", "image_qa.py", "image_qa_v2.py", "image_qa_v3.py", "validate_figurespec_v2.py", "FIGURESPEC_V4_PROTOCOL.md", "FIGURESPEC_PROTOCOL.md", "adapters/local_python"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".opju", ".opj", ".xlsx", ".xls", ".pdf", ".png", ".jpg", ".jpeg", ".lck", ".log"}


def iter_entries(path: Path):
    if path.is_file():
        with zipfile.ZipFile(path) as archive:
            for name in archive.namelist():
                if not name.endswith("/"):
                    yield name.replace("\\", "/")
    else:
        root = path.resolve()
        for item in root.rglob("*"):
            if item.is_file():
                rel = item.relative_to(root).as_posix()
                rel_lower = rel.lower()
                if any(fragment.lower() in rel_lower for fragment in {"__pycache__", ".pytest_cache"}):
                    continue
                if item.suffix.lower() in {".pyc", ".pyo"}:
                    continue
                if any(part in SKIP_PARTS for part in item.relative_to(root).parts):
                    continue
                if item.name in SKIP_NAMES:
                    continue
                yield f"originplot-skill/{rel}" if not rel.startswith("originplot-skill/") else rel


def validate(path: Path):
    entries = sorted(set(iter_entries(path)))
    failures = []
    entry_set = set(entries)
    for required in sorted(REQUIRED):
        if required not in entry_set:
            failures.append({"code": "missing_required_entry", "entry": required})
    for entry in entries:
        if "\\" in entry:
            failures.append({"code": "backslash_zip_entry", "entry": entry})
        if re.match(r"^[A-Za-z]:", entry) or entry.startswith("/"):
            failures.append({"code": "absolute_path_entry", "entry": entry})
        if not entry.startswith("originplot-skill/"):
            failures.append({"code": "missing_top_level_originplot_skill_dir", "entry": entry})
        if Path(entry).suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append({"code": "forbidden_artifact_suffix", "entry": entry})
        for fragment in FORBIDDEN_FRAGMENTS:
            if fragment.lower() in entry.lower():
                failures.append({"code": "forbidden_artifact_fragment", "entry": entry, "fragment": fragment})
    return {"schema": "originplot.shareable_package_check.v5.5", "path": str(path), "entry_count": len(entries), "status": "ok" if not failures else "failed", "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an OriginPlot v5.5 shareable core package.")
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = validate(args.path)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
