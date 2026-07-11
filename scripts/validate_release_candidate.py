from __future__ import annotations

import argparse
import compileall
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
EXPECTED_SKILL_VERSION = "5.8.9-p14"
EXPECTED_MIN_TESTS = 117
REQUIRED_FIGURES = ("fig12", "fig15", "fig16")
RELEASE_GATE_ORDER = [
    "compileall",
    "run_all_tests",
    "random_directory_portability",
    "validate_shareable_package_v5",
    "absolute_path_scan",
    "cache_temp_artifact_scan",
    "report_version_consistency",
    "benchmark_evidence_packages",
    "live_readback_validation",
    "final_release_bundle_validation",
]
TEXT_SCAN_SUFFIXES = {".json", ".md", ".txt", ".yaml", ".yml"}
CACHE_PARTS = {"__pycache__", ".pytest_cache", "tmp_v5_validation", "local_python"}
CACHE_SUFFIXES = {".pyc", ".pyo"}
WINDOWS_ABSOLUTE_RE = re.compile(r"^[A-Za-z]:[\\/]")


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module: {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def release_status(gates: dict[str, dict[str, Any]]) -> str:
    if all(gates.get(name, {}).get("status") == "ok" for name in RELEASE_GATE_ORDER):
        return "release_ready_for_fig12_targeted_optimization"
    return "not_release_ready"


def run_process(command: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "returncode": completed.returncode,
    }


def compileall_gate(skill_root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="originplot_p12_compile_") as tmp:
        previous = os.environ.get("PYTHONPYCACHEPREFIX")
        os.environ["PYTHONPYCACHEPREFIX"] = str(Path(tmp) / "pycache")
        try:
            ok = compileall.compile_dir(str(skill_root), quiet=2, force=True)
        finally:
            if previous is None:
                os.environ.pop("PYTHONPYCACHEPREFIX", None)
            else:
                os.environ["PYTHONPYCACHEPREFIX"] = previous
    return {"status": "ok" if ok else "failed", "compiled": bool(ok)}


def parse_test_result(path: Path, process: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if path.exists():
        try:
            payload = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:
            payload = {"parse_error": f"{exc.__class__.__name__}: {exc}"}
    tests_run = int(payload.get("tests_run", 0) or 0)
    skipped = int(payload.get("skipped", 0) or 0)
    passed = (
        process["returncode"] == 0
        and payload.get("status") == "ok"
        and tests_run >= EXPECTED_MIN_TESTS
        and skipped == 0
        and not payload.get("test_errors")
    )
    return {
        "status": "ok" if passed else "failed",
        "tests_run": tests_run,
        "expected_min_tests": EXPECTED_MIN_TESTS,
        "skipped": skipped,
        "test_errors": payload.get("test_errors", []),
        "compile_failures": payload.get("compile_failures", []),
        "process": process,
    }


def run_all_tests_gate(skill_root: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="originplot_p12_tests_") as tmp:
        result_path = Path(tmp) / "run_all_tests.json"
        process = run_process(
            [
                sys.executable,
                str(skill_root / "scripts" / "run_all_tests.py"),
                "--expected-min-tests",
                str(EXPECTED_MIN_TESTS),
                "--json-out",
                str(result_path),
            ],
            cwd=skill_root,
        )
        return parse_test_result(result_path, process)


def portability_gate(skill_root: Path) -> dict[str, Any]:
    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {
            name
            for name in names
            if name in CACHE_PARTS or Path(name).suffix.lower() in CACHE_SUFFIXES
        }

    with tempfile.TemporaryDirectory(prefix="originplot_p12_portable_") as tmp:
        portable_root = Path(tmp) / "random-location" / "originplot-skill"
        portable_root.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(skill_root, portable_root, ignore=ignore)
        result_path = Path(tmp) / "portable_run_all_tests.json"
        env = dict(os.environ)
        env.pop("ORIGINPLOT_SKILL_ROOT", None)
        env["PYTHONPYCACHEPREFIX"] = str(Path(tmp) / "portable_pycache")
        process = run_process(
            [
                sys.executable,
                str(portable_root / "scripts" / "run_all_tests.py"),
                "--expected-min-tests",
                str(EXPECTED_MIN_TESTS),
                "--json-out",
                str(result_path),
            ],
            cwd=portable_root,
            env=env,
        )
        result = parse_test_result(result_path, process)
        result["random_directory_used"] = True
        result["originplot_skill_root_unset"] = True
        return result


def build_and_validate_shareable_gate(skill_root: Path) -> tuple[dict[str, Any], bytes]:
    builder = load_module("originplot_p12_package_builder", skill_root / "scripts" / "build_shareable_package.py")
    validator = load_module(
        "originplot_p12_package_validator", skill_root / "scripts" / "validate_shareable_package_v5.py"
    )
    with tempfile.TemporaryDirectory(prefix="originplot_p12_package_") as tmp:
        zip_path = Path(tmp) / "originplot-skill-p12.zip"
        build = builder.build_zip(skill_root, zip_path)
        validation = validator.validate(zip_path)
        data = zip_path.read_bytes()
    return {
        "status": "ok" if validation.get("status") == "ok" else "failed",
        "entry_count": build.get("entry_count"),
        "validation_failures": validation.get("failures", []),
    }, data


def iter_zip_text(zip_bytes: bytes):
    import io

    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            if name.endswith("/") or Path(name).suffix.lower() not in TEXT_SCAN_SUFFIXES:
                continue
            try:
                yield name, archive.read(name).decode("utf-8-sig")
            except UnicodeDecodeError:
                continue


def absolute_path_scan_gate(zip_bytes: bytes) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    for name, text in iter_zip_text(zip_bytes):
        for line_number, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip().strip("`\"'")
            if WINDOWS_ABSOLUTE_RE.match(stripped) or stripped.startswith("/Users/"):
                findings.append({"entry": name, "line": line_number})
            elif re.search(r"[A-Za-z]:[\\/]Users[\\/][^\\/\s]+", line):
                findings.append({"entry": name, "line": line_number})
    return {"status": "ok" if not findings else "failed", "findings": findings}


def cache_scan_gate(zip_bytes: bytes) -> dict[str, Any]:
    import io

    findings: list[str] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            parts = set(Path(name).parts)
            if parts.intersection(CACHE_PARTS) or Path(name).suffix.lower() in CACHE_SUFFIXES:
                findings.append(name)
    return {"status": "ok" if not findings else "failed", "findings": findings}


def report_version_gate(skill_root: Path, reports: list[Path]) -> dict[str, Any]:
    skill_text = (skill_root / "SKILL.md").read_text(encoding="utf-8-sig")
    failures: list[dict[str, Any]] = []
    if f"OriginPlot Skill v{EXPECTED_SKILL_VERSION}" not in skill_text:
        failures.append({"code": "skill_version_mismatch", "expected": EXPECTED_SKILL_VERSION})
    runner_text = (skill_root / "scripts" / "run_all_tests.py").read_text(encoding="utf-8-sig")
    if f"originplot.run_all_tests.v{EXPECTED_SKILL_VERSION}" not in runner_text:
        failures.append({"code": "runner_version_mismatch", "expected": EXPECTED_SKILL_VERSION})
    for report in reports:
        if not report.exists():
            failures.append({"code": "report_missing", "report": report.name})
            continue
        if EXPECTED_SKILL_VERSION not in report.read_text(encoding="utf-8-sig"):
            failures.append({"code": "report_version_mismatch", "report": report.name})
    return {"status": "ok" if not failures else "failed", "failures": failures}


def flatten_plot_records(readback: dict[str, Any]) -> list[dict[str, Any]]:
    root = readback.get("origin_object_readback", readback)
    pages = root.values() if isinstance(root, dict) else []
    records: list[dict[str, Any]] = []
    for page in pages:
        if not isinstance(page, dict):
            continue
        for layer in page.get("layers", []):
            records.extend(record for record in layer.get("plot_details", []) if isinstance(record, dict))
    return records


def validate_live_readback_payload(readback: dict[str, Any], *, figure_id: str) -> dict[str, Any]:
    plots = flatten_plot_records(readback)
    expected = 10 if figure_id == "fig15" else None
    required = [
        "plot_type_code",
        "plot_family",
        "visible",
        "x_dataset",
        "y_dataset",
        "data_workbook",
        "data_worksheet",
        "data_worksheet_index",
        "x_column",
        "y_column",
        "graph_plot_range",
    ]
    failures: list[dict[str, Any]] = []
    for index, plot in enumerate(plots):
        missing = [
            key
            for key in required
            if key not in plot
            or plot.get(key) is None
            or (key == "plot_family" and str(plot.get(key)).lower() == "unknown")
        ]
        if missing:
            failures.append({"plot_index": index, "missing_or_invalid": missing})
    if expected is not None and len(plots) != expected:
        failures.append({"code": "plot_count_mismatch", "expected": expected, "actual": len(plots)})
    return {
        "status": "ok" if not failures else "failed",
        "figure_id": figure_id,
        "plot_count": len(plots),
        "expected_plot_count": expected,
        "plot_failures": failures,
    }


def parse_evidence_args(values: list[str]) -> tuple[dict[str, Path], list[dict[str, Any]]]:
    mapping: dict[str, Path] = {}
    failures: list[dict[str, Any]] = []
    for value in values:
        if "=" not in value:
            failures.append({"code": "invalid_evidence_argument", "value": value})
            continue
        figure, raw_path = value.split("=", 1)
        if figure not in REQUIRED_FIGURES:
            failures.append({"code": "invalid_evidence_figure", "figure": figure})
            continue
        mapping[figure] = Path(raw_path).resolve()
    return mapping, failures


def benchmark_evidence_gate(skill_root: Path, evidence_dirs: dict[str, Path], parse_failures: list[dict[str, Any]]) -> dict[str, Any]:
    validator = load_module(
        "originplot_p12_evidence_validator", skill_root / "scripts" / "validate_benchmark_evidence_package.py"
    )
    results: dict[str, Any] = {}
    failures = list(parse_failures)
    for figure in REQUIRED_FIGURES:
        path = evidence_dirs.get(figure)
        if path is None:
            failures.append({"code": "evidence_directory_missing", "figure_id": figure})
            continue
        result = validator.validate(path)
        results[figure] = result
        if result.get("status") != "ok":
            failures.append({"code": "evidence_validation_failed", "figure_id": figure})
    return {"status": "ok" if not failures else "failed", "results": results, "failures": failures}


def live_readback_gate(evidence_dirs: dict[str, Path]) -> dict[str, Any]:
    fig15 = evidence_dirs.get("fig15")
    if fig15 is None:
        return {"status": "failed", "failures": [{"code": "fig15_canary_evidence_missing"}]}
    inspection = fig15 / "inspection.json"
    if not inspection.exists():
        return {"status": "failed", "failures": [{"code": "fig15_inspection_missing"}]}
    try:
        payload = json.loads(inspection.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"status": "failed", "failures": [{"code": "fig15_inspection_parse_failed", "error": str(exc)}]}
    return validate_live_readback_payload(payload, figure_id="fig15")


def final_release_bundle_gate(skill_root: Path, release_bundle: Path | None) -> dict[str, Any]:
    if release_bundle is None:
        return {"status": "failed", "failures": [{"code": "final_release_bundle_missing"}]}
    validator = load_module(
        "originplot_p14_release_bundle_validator", skill_root / "scripts" / "validate_release_bundle.py"
    )
    result = validator.validate_release_bundle(release_bundle)
    return {
        "status": "ok" if result.get("bundle_validation", {}).get("clean") else "failed",
        **result,
    }


def validate_release(
    *,
    skill_root: Path,
    evidence_values: list[str],
    reports: list[Path],
    release_bundle: Path | None = None,
) -> dict[str, Any]:
    skill_root = skill_root.resolve()
    gates: dict[str, dict[str, Any]] = {}
    gates["compileall"] = compileall_gate(skill_root)
    gates["run_all_tests"] = run_all_tests_gate(skill_root)
    gates["random_directory_portability"] = portability_gate(skill_root)
    share_gate, zip_bytes = build_and_validate_shareable_gate(skill_root)
    gates["validate_shareable_package_v5"] = share_gate
    gates["absolute_path_scan"] = absolute_path_scan_gate(zip_bytes)
    gates["cache_temp_artifact_scan"] = cache_scan_gate(zip_bytes)
    gates["report_version_consistency"] = report_version_gate(skill_root, reports)
    evidence_dirs, parse_failures = parse_evidence_args(evidence_values)
    gates["benchmark_evidence_packages"] = benchmark_evidence_gate(
        skill_root, evidence_dirs, parse_failures
    )
    gates["live_readback_validation"] = live_readback_gate(evidence_dirs)
    gates["final_release_bundle_validation"] = final_release_bundle_gate(skill_root, release_bundle)
    return {
        "schema": "originplot.release_candidate_validation.v1",
        "skill_version": EXPECTED_SKILL_VERSION,
        "release_status": release_status(gates),
        "gate_order": RELEASE_GATE_ORDER,
        "gates": gates,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate OriginPlot v5.8.9-p14 release readiness.")
    parser.add_argument("--skill-dir", type=Path, default=SKILL_ROOT)
    parser.add_argument(
        "--evidence-dir",
        action="append",
        default=[],
        metavar="FIGURE=PATH",
        help="Repeat for fig12, fig15, and fig16.",
    )
    parser.add_argument("--report", action="append", type=Path, default=[])
    parser.add_argument("--release-bundle", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = validate_release(
        skill_root=args.skill_dir,
        evidence_values=args.evidence_dir,
        reports=args.report,
        release_bundle=args.release_bundle,
    )
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["release_status"] == "release_ready_for_fig12_targeted_optimization" else 2


if __name__ == "__main__":
    raise SystemExit(main())
