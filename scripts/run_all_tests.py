from __future__ import annotations

import argparse
import json
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXPECTED_MIN_TESTS = 165


CRITICAL_SCRIPTS = [
    "scripts/benchmark_materializer.py",
    "scripts/visual_evidence_engine.py",
    "scripts/semantic_figure_benchmark.py",
    "scripts/validate_benchmark_evidence_package.py",
    "scripts/build_shareable_package.py",
    "scripts/build_combined_review_package.py",
    "scripts/validate_shareable_package_v5.py",
    "scripts/validate_release_candidate.py",
    "scripts/validate_release_bundle.py",
    "scripts/acceptance_hardening.py",
    "scripts/fig12_roi.py",
    "scripts/audit_dependencies.py",
    "scripts/validate_publication_contract.py",
    "scripts/inspect_official_templates.py",
    "scripts/retrieve_official_template.py",
    "scripts/search_official_templates.py",
    "scripts/operation_maturity.py",
    "scripts/originplot_runtime_v5.py",
    "runtime/artifact_manifest.py",
    "adapters/inspection/adapter.py",
    "scripts/origin_calibration_probe.py",
    "scripts/origin_calibration_inspect_worker.py",
    "scripts/origin_candidate_worker.py",
    "scripts/extract_aa2195_fresh_source_bundle.py",
    "scripts/reextract_validated_source_bundle.py",
    "scripts/build_validated_data_reuse_record.py",
    "scripts/materialize_live_evidence.py",
    "scripts/visual_qa.py",
    "scripts/audit_five_figure_batch.py",
    "builders/aa2195/__init__.py",
    "builders/aa2195/session.py",
    "builders/aa2195/geometry.py",
    "builders/aa2195/source_reference.py",
    "builders/aa2195/fresh_source_data.py",
    "builders/aa2195/fig12_builder.py",
    "builders/aa2195/fig15_builder.py",
    "builders/aa2195/fig16_builder.py",
    "builders/aa2195/readback.py",
    "builders/base.py",
    "builders/registry.py",
    "builders/generic/line_builder.py",
]


def compile_scripts():
    failures = []
    for rel in CRITICAL_SCRIPTS:
        path = ROOT / rel
        try:
            compile(path.read_text(encoding="utf-8-sig"), str(path), "exec")
        except Exception as exc:
            failures.append({"script": rel, "error": str(exc)})
    return failures


def discover_suite():
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for directory in [ROOT / "tests", ROOT / "scripts" / "tests"]:
        if directory.exists():
            suite.addTests(loader.discover(str(directory), pattern="test*.py", top_level_dir=str(ROOT)))
    return suite


def run_unittest():
    suite = discover_suite()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    errors = [str(item[1]) for item in result.errors + result.failures]
    return result.testsRun, len(result.skipped), errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OriginPlot v5.8.9-p18 full test suite.")
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--expected-min-tests", type=int, default=EXPECTED_MIN_TESTS)
    args = parser.parse_args()
    compile_failures = compile_scripts()
    tests_run, skipped, test_errors = run_unittest()
    discovery_failures = []
    if tests_run < args.expected_min_tests:
        discovery_failures.append({"code": "TEST_DISCOVERY_INCOMPLETE", "expected_min_tests": args.expected_min_tests, "actual": tests_run})
    payload = {"schema": "originplot.run_all_tests.v5.8.9-p18", "skill_version": "5.8.9-p18", "status": "ok" if not compile_failures and not test_errors and skipped == 0 and not discovery_failures else "failed", "compile_failures": compile_failures, "tests_run": tests_run, "expected_min_tests": args.expected_min_tests, "skipped": skipped, "test_errors": test_errors, "discovery_failures": discovery_failures}
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if payload["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
