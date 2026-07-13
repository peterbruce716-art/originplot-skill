from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path
from typing import Any


REQUIRED_FILES = {
    "result.opju",
    "source_crop.png",
    "pre_save.png",
    "post_reopen.png",
    "inspection.json",
    "qa_report.json",
    "benchmark_actual.json",
    "semantic_benchmark_report.json",
    "deviation_ledger.json",
    "comparison_board.png",
    "figurespec.json",
    "compiled_ir.json",
    "operation_plan.json",
    "run_artifacts.json",
    "run_manifest.json",
}
IDENTITY_FIELDS = ("run_id", "figure_id", "skill_version")


def is_absolute_path_text(value: str) -> bool:
    text = str(value).strip()
    return bool(re.match(r"^[A-Za-z]:[\\/]", text) or text.startswith("/"))


def identity_consistency_failures(payloads: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    for field in IDENTITY_FIELDS:
        values: dict[str, str] = {}
        for name, payload in sorted(payloads.items()):
            value = payload.get(field)
            if value in {None, ""}:
                failures.append({"code": "identity_field_missing", "entry": name, "field": field})
            else:
                values[name] = str(value)
        unique = sorted(set(values.values()))
        if len(unique) > 1:
            failures.append(
                {
                    "code": "identity_mismatch",
                    "field": field,
                    "values": values,
                }
            )
    return failures


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_entries(path: Path) -> dict[str, bytes]:
    if path.is_file():
        with zipfile.ZipFile(path) as archive:
            return {name.replace("\\", "/"): archive.read(name) for name in archive.namelist() if not name.endswith("/")}
    root = path.resolve()
    return {item.relative_to(root).as_posix(): item.read_bytes() for item in root.rglob("*") if item.is_file()}


def json_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from json_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from json_strings(item)


def artifact_records(value: Any):
    if isinstance(value, dict):
        if {"path", "sha256", "exists"}.issubset(value.keys()):
            yield value
        for item in value.values():
            yield from artifact_records(item)
    elif isinstance(value, list):
        for item in value:
            yield from artifact_records(item)


def validate(path: Path) -> dict[str, Any]:
    entries = read_entries(path)
    basenames = {Path(name).name for name in entries}
    failures = []
    for required in sorted(REQUIRED_FILES):
        if required not in basenames:
            failures.append({"code": "missing_required_evidence_file", "file": required})
    run_artifacts = None
    report = None
    for name in sorted(entries):
        if "\\" in name:
            failures.append({"code": "backslash_entry", "entry": name})
        if is_absolute_path_text(name) or ".." in Path(name).parts:
            failures.append({"code": "unsafe_entry_path", "entry": name})
    json_payloads: dict[str, dict[str, Any]] = {}
    for name, data in entries.items():
        if Path(name).suffix.lower() != ".json":
            continue
        try:
            payload = json.loads(data.decode("utf-8-sig"))
        except Exception as exc:
            failures.append({"code": "json_parse_failed", "entry": name, "error": str(exc)})
            continue
        if not isinstance(payload, dict):
            failures.append({"code": "json_root_not_object", "entry": name})
            continue
        json_payloads[Path(name).name] = payload
        if Path(name).name == "run_artifacts.json":
            run_artifacts = payload
        if Path(name).name == "semantic_benchmark_report.json":
            report = payload
        for text in json_strings(payload):
            if is_absolute_path_text(text):
                failures.append({"code": "absolute_path_inside_json", "entry": name, "value": text})
            if "run" in text.lower() and ("../" in text or "..\\" in text):
                failures.append({"code": "external_run_reference_inside_json", "entry": name, "value": text})
        for record in artifact_records(payload):
            rec_path = str(record.get("path") or "")
            if record.get("provenance") != "live_same_run" or record.get("eligible_for_pass") is not True:
                failures.append({"code": "artifact_not_live_same_run", "entry": name, "path": rec_path})
            if is_absolute_path_text(rec_path):
                failures.append({"code": "absolute_artifact_record_path", "entry": name, "path": rec_path})
            rec_name = Path(rec_path).name
            matched = [entry for entry in entries if Path(entry).name == rec_name]
            if record.get("exists") and record.get("sha256") and matched and sha256_bytes(entries[matched[0]]) != record.get("sha256"):
                failures.append({"code": "sha256_mismatch", "entry": name, "path": rec_path})
    required_json_payloads = {
        name: json_payloads[name]
        for name in sorted(REQUIRED_FILES)
        if name.endswith(".json") and name in json_payloads
    }
    failures.extend(identity_consistency_failures(required_json_payloads))
    if run_artifacts:
        text = json.dumps(run_artifacts, ensure_ascii=False).lower()
        if "verified_seed_opju_copy" in text or "inherited_from_run" in text or "inherited_diagnostic" in text:
            failures.append({"code": "inherited_or_seed_evidence_package_not_pass_eligible"})
    if report and report.get("status") != "pass":
        failures.append({"code": "semantic_benchmark_not_pass", "status": report.get("status")})
    return {"schema": "originplot.benchmark_evidence_package_check.v1", "protocol": "v5.8.9-p18_live_same_run", "path": path.name, "entry_count": len(entries), "status": "ok" if not failures else "failed", "failures": failures}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a v5.5 live same-run OriginPlot evidence package.")
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
