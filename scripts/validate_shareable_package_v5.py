from __future__ import annotations

import argparse
import json
import os
import re
import stat
import zipfile
from pathlib import Path

try:
    from scripts.versioning import load_versions
    from scripts.validate_public_evidence_index import validate as validate_public_evidence_index
    from scripts.package_policy import (
        EXCLUDED_DIRECTORY_NAMES,
        EXCLUDED_FILE_NAMES,
        FORBIDDEN_ARTIFACT_SUFFIXES,
        contains_local_environment_path,
        is_local_interpreter_binary,
    )
except ModuleNotFoundError:
    from versioning import load_versions
    from validate_public_evidence_index import validate as validate_public_evidence_index
    from package_policy import (
        EXCLUDED_DIRECTORY_NAMES,
        EXCLUDED_FILE_NAMES,
        FORBIDDEN_ARTIFACT_SUFFIXES,
        contains_local_environment_path,
        is_local_interpreter_binary,
    )

VERSIONS = load_versions()
REQUIRED = {"originplot-skill/version.json", "originplot-skill/README.md", "originplot-skill/LICENSE", "originplot-skill/SKILL.md", "originplot-skill/FIGURESPEC_V5_5_LIVE_SEMANTIC_CLOSURE_PROTOCOL.md", "originplot-skill/scripts/operation_maturity.py", "originplot-skill/scripts/visual_evidence_engine.py", "originplot-skill/scripts/semantic_figure_benchmark.py", "originplot-skill/scripts/validate_benchmark_evidence_package.py", "originplot-skill/scripts/materialize_live_evidence.py", "originplot-skill/scripts/build_combined_review_package.py", "originplot-skill/scripts/run_all_tests.py", "originplot-skill/scripts/audit_dependencies.py", "originplot-skill/builders/base.py", "originplot-skill/builders/registry.py", "originplot-skill/builders/generic/line_builder.py", "originplot-skill/references/current-contract.md", "originplot-skill/references/origin-runtime.md", "originplot-skill/references/visual-qa.md", "originplot-skill/references/aa2195-benchmark.md", "originplot-skill/requirements-core.txt", "originplot-skill/requirements-origin.txt", "originplot-skill/requirements-dev.txt", "originplot-skill/.github/workflows/offline-ci.yml", "originplot-skill/examples/public_demo/generate_source.py", "originplot-skill/examples/public_demo/figure_spec.json", "originplot-skill/examples/public_demo/candidate.json", "originplot-skill/schemas/inspection-v2.schema.json", "originplot-skill/operation_registry/operation_maturity_v1.json"}
REQUIRED |= {
    "originplot-skill/P14_IMPLEMENTATION_REPORT.md",
    "originplot-skill/p14_gap_analysis.md",
    "originplot-skill/scripts/inspect_official_templates.py",
    "originplot-skill/examples/template_search/aa2195_official_template_search.json",
    "originplot-skill/references/aa2195-release-evidence.json",
    "originplot-skill/references/figure-contract-and-style.md",
    "originplot-skill/references/materials-figure-qa.md",
    "originplot-skill/assets/journal_style_profiles.json",
    "originplot-skill/schemas/publication-contract-v1.schema.json",
    "originplot-skill/examples/publication_contract.example.json",
    "originplot-skill/scripts/validate_publication_contract.py",
    "originplot-skill/scripts/validate_public_evidence_index.py",
    "originplot-skill/scripts/versioning.py",
    "originplot-skill/scripts/package_policy.py",
    "originplot-skill/tests/test_publication_contract.py",
}
OFFICIAL_RESEARCH_URLS = {
    "https://www.originlab.com/www/products/GraphGallery.aspx?s=0&sort=Newest",
    "https://docs.originlab.com/zh/",
    "https://www.originlab.com/videos/index.aspx?CID=11",
    "https://docs.originlab.com/quick-help/graphing/zh/",
}
SKIP_PARTS = EXCLUDED_DIRECTORY_NAMES
SKIP_NAMES = {"FIGURESPEC_PROTOCOL.md", "FIGURESPEC_V4_PROTOCOL.md", "originplot_runtime_v4.py", "image_qa.py", "image_qa_v2.py", "image_qa_v3.py", "validate_figurespec_v2.py", "origin_only_minimal_figurespec_v2.json", "compiled_ir_v4_example.json", "editable_reproduction_v4.json", "operation_plan_v4_example.json", "origin-2022-capabilities-v4.example.json", "adapter_modules_v5_1.example.json", "adapter_configs_v5_1.example.json"}
FORBIDDEN_FRAGMENTS = {"__pycache__", ".pytest_cache", "tmp_v5_validation", "originplot_runtime_v4.py", "image_qa.py", "image_qa_v2.py", "image_qa_v3.py", "validate_figurespec_v2.py", "FIGURESPEC_V4_PROTOCOL.md", "FIGURESPEC_PROTOCOL.md", "adapters/local_python"}
FORBIDDEN_SUFFIXES = FORBIDDEN_ARTIFACT_SUFFIXES


def collect_entries(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    entries: list[str] = []
    failures: list[dict[str, str]] = []
    if not path.exists():
        return entries, [{"code": "package_path_missing", "path": str(path)}]
    if path.is_symlink():
        return entries, [{"code": "forbidden_directory_symlink", "entry": str(path)}]
    if path.is_file():
        try:
            with zipfile.ZipFile(path) as archive:
                seen: set[str] = set()
                for info in archive.infolist():
                    raw_name = getattr(info, "orig_filename", info.filename)
                    normalized = raw_name.replace("\\", "/")
                    if raw_name != normalized:
                        failures.append({"code": "backslash_zip_entry", "entry": raw_name})
                    path_segments = normalized.split("/")
                    if info.is_dir() and path_segments[-1:] == [""]:
                        path_segments = path_segments[:-1]
                    if "." in path_segments:
                        failures.append({"code": "unsafe_dot_path_segment", "entry": normalized})
                    if "" in path_segments:
                        failures.append({"code": "unsafe_empty_path_segment", "entry": normalized})
                    canonical = "/".join(
                        segment for segment in path_segments if segment not in {"", "."}
                    ).casefold()
                    if canonical in seen:
                        failures.append({"code": "duplicate_archive_entry", "entry": normalized})
                    else:
                        seen.add(canonical)
                    unix_mode = (info.external_attr >> 16) & 0xFFFF
                    file_type = stat.S_IFMT(unix_mode)
                    if stat.S_ISLNK(unix_mode) or info.external_attr & 0x400:
                        failures.append({"code": "forbidden_zip_symlink", "entry": normalized})
                    elif file_type and not (stat.S_ISREG(unix_mode) or stat.S_ISDIR(unix_mode)):
                        failures.append({"code": "forbidden_non_regular_zip_entry", "entry": normalized})
                    if not info.is_dir():
                        entries.append(normalized)
        except (OSError, zipfile.BadZipFile) as exc:
            failures.append({"code": "invalid_archive", "path": str(path), "message": str(exc)})
        return entries, failures

    root = path.resolve()
    for current, directory_names, file_names in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        retained_directories: list[str] = []
        for name in sorted(directory_names):
            item = current_path / name
            rel = item.relative_to(root).as_posix()
            if item.is_symlink():
                failures.append({"code": "forbidden_directory_symlink", "entry": rel})
                continue
            if contains_local_environment_path(rel):
                failures.append({"code": "forbidden_local_environment_path", "entry": rel})
                continue
            retained_directories.append(name)
        directory_names[:] = retained_directories
        for name in sorted(file_names):
            item = current_path / name
            rel = item.relative_to(root).as_posix()
            if item.is_symlink():
                failures.append({"code": "forbidden_directory_symlink", "entry": rel})
                continue
            if contains_local_environment_path(rel):
                failures.append({"code": "forbidden_local_environment_path", "entry": rel})
                continue
            if is_local_interpreter_binary(rel):
                failures.append({"code": "forbidden_local_interpreter_binary", "entry": rel})
            if item.is_file():
                entries.append(f"originplot-skill/{rel}")
    return entries, failures


def read_entry(path: Path, entry: str) -> bytes:
    if path.is_file():
        with zipfile.ZipFile(path) as archive:
            matches = [
                info
                for info in archive.infolist()
                if getattr(info, "orig_filename", info.filename).replace("\\", "/") == entry
            ]
            if len(matches) != 1:
                raise OSError(f"Archive entry is missing or ambiguous: {entry}")
            return archive.read(matches[0])
    relative = entry.removeprefix("originplot-skill/")
    root = path.resolve()
    candidate = root
    for part in Path(relative).parts:
        candidate = candidate / part
        if candidate.is_symlink():
            raise OSError(f"Refusing to follow package symlink: {relative}")
    resolved = candidate.resolve(strict=True)
    resolved.relative_to(root)
    return resolved.read_bytes()


def validate(path: Path):
    raw_entries, failures = collect_entries(path)
    entries = sorted(set(raw_entries))
    entry_set = set(entries)
    for required in sorted(REQUIRED):
        if required not in entry_set:
            failures.append({"code": "missing_required_entry", "entry": required})
    for entry in entries:
        if "\\" in entry:
            failures.append({"code": "backslash_zip_entry", "entry": entry})
        if re.match(r"^[A-Za-z]:", entry) or entry.startswith("/"):
            failures.append({"code": "absolute_path_entry", "entry": entry})
        if ".." in entry.replace("\\", "/").split("/"):
            failures.append({"code": "unsafe_path_traversal", "entry": entry})
        if not entry.startswith("originplot-skill/"):
            failures.append({"code": "missing_top_level_originplot_skill_dir", "entry": entry})
        if contains_local_environment_path(entry):
            failures.append({"code": "forbidden_local_environment_path", "entry": entry})
        if is_local_interpreter_binary(entry):
            failures.append({"code": "forbidden_local_interpreter_binary", "entry": entry})
        if Path(entry).name.casefold() in EXCLUDED_FILE_NAMES:
            failures.append({"code": "forbidden_local_file_name", "entry": entry})
        if Path(entry).suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append({"code": "forbidden_artifact_suffix", "entry": entry})
        for fragment in FORBIDDEN_FRAGMENTS:
            if fragment.lower() in entry.lower():
                failures.append({"code": "forbidden_artifact_fragment", "entry": entry, "fragment": fragment})
    record_entry = "originplot-skill/examples/template_search/aa2195_official_template_search.json"
    if record_entry in entry_set:
        try:
            record = json.loads(read_entry(path, record_entry).decode("utf-8-sig"))
            urls = {
                str(item.get("url"))
                for item in record.get("official_sources", [])
                if isinstance(item, dict)
            }
            for url in sorted(OFFICIAL_RESEARCH_URLS - urls):
                failures.append({"code": "missing_official_research_url", "entry": record_entry, "url": url})
        except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            failures.append({"code": "invalid_template_search_record", "entry": record_entry, "message": str(exc)})
    skill_entry = "originplot-skill/SKILL.md"
    if skill_entry in entry_set:
        try:
            skill_text = read_entry(path, skill_entry).decode("utf-8-sig")
            for url in sorted(OFFICIAL_RESEARCH_URLS):
                if url not in skill_text:
                    failures.append({"code": "missing_official_research_url", "entry": skill_entry, "url": url})
        except (OSError, UnicodeDecodeError) as exc:
            failures.append({"code": "invalid_skill_document", "entry": skill_entry, "message": str(exc)})
    evidence_index_entry = "originplot-skill/references/aa2195-release-evidence.json"
    if evidence_index_entry in entry_set:
        try:
            evidence_index = json.loads(read_entry(path, evidence_index_entry).decode("utf-8-sig"))
            evidence_result = validate_public_evidence_index(evidence_index)
            for failure in evidence_result["failures"]:
                failures.append(
                    {
                        "code": "invalid_public_evidence_index",
                        "entry": evidence_index_entry,
                        "detail": failure,
                    }
                )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            failures.append({"code": "invalid_public_evidence_index", "entry": evidence_index_entry, "message": str(exc)})
    for figure in ("fig3", "fig12", "fig14", "fig15", "fig16"):
        candidate_entry = f"originplot-skill/examples/candidates/{figure}.json"
        if candidate_entry not in entry_set:
            continue
        try:
            candidate = json.loads(read_entry(path, candidate_entry).decode("utf-8-sig"))
            if not isinstance(candidate, dict):
                raise ValueError("Candidate JSON must be an object")
            if candidate.get("source_crop") != "AUTHORIZED_LOCAL_SOURCE_REQUIRED":
                failures.append({"code": "packaged_source_path_not_sanitized", "entry": candidate_entry})
        except (KeyError, OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append({"code": "invalid_candidate_json", "entry": candidate_entry, "message": str(exc)})
    version_entry = "originplot-skill/version.json"
    if version_entry in entry_set:
        try:
            packaged_versions = json.loads(read_entry(path, version_entry).decode("utf-8-sig"))
            if packaged_versions != VERSIONS.as_dict():
                failures.append({"code": "version_source_mismatch", "entry": version_entry})
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            failures.append({"code": "invalid_version_source", "entry": version_entry, "message": str(exc)})
    return {
        "schema": "originplot.shareable_package_check.v5.5",
        **VERSIONS.as_dict(),
        "path": str(path),
        "entry_count": len(entries),
        "status": "ok" if not failures else "failed",
        "failures": failures,
    }


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
