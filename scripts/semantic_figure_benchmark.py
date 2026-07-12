from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.artifact_manifest import has_seed_fallback, same_run_failures  # noqa: E402
from scripts.visual_evidence_engine import evaluate as evaluate_visual  # noqa: E402


REPORT_SCHEMA = "originplot.semantic_figure_benchmark_report.v1"
LEDGER_SCHEMA = "originplot.deviation_ledger.v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def resolve_path(base: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base / path).resolve()


def exact_score(expected: Any, actual: Any) -> float:
    return 1.0 if expected == actual else 0.0


def compare_counts(expected: dict[str, Any], actual: dict[str, Any], category: str, critical_keys: set[str] | None = None):
    checks, blocking, nonblocking = [], [], []
    critical_keys = critical_keys or set()
    for key, expected_value in expected.items():
        if key in {"visual_thresholds", "critical_style", "decorative_style", "required_objects", "rois"}:
            continue
        if not isinstance(expected_value, (int, float, bool, str)):
            continue
        actual_value = actual.get(key)
        score = exact_score(expected_value, actual_value)
        checks.append(score)
        if score < 1.0:
            item = {"category": category, "code": f"{category.upper()}_{key.upper()}_MISMATCH", "expected": expected_value, "actual": actual_value}
            (blocking if category != "style" or key in critical_keys else nonblocking).append(item)
    return (sum(checks) / len(checks) if checks else 1.0), blocking, nonblocking


def semantic_coverage(expected_objects: list[dict[str, Any]], actual_objects: list[dict[str, Any]]):
    actual_by_role = {}
    for item in actual_objects:
        role = str(item.get("role") or "")
        if role:
            actual_by_role[role] = actual_by_role.get(role, 0) + int(item.get("count", 1) or 0)
    total_expected = total_matched = 0
    deviations = []
    for item in expected_objects:
        role = str(item.get("role") or "")
        expected_count = int(item.get("expected_count") or 0)
        actual_count = int(actual_by_role.get(role, 0))
        total_expected += expected_count
        total_matched += min(expected_count, actual_count)
        if actual_count < expected_count:
            deviations.append({"category": "semantic", "code": "MISSING_REQUIRED_OBJECTS", "expected": {"role": role, "count": expected_count}, "actual": {"role": role, "count": actual_count}})
    return (total_matched / total_expected if total_expected else 1.0), deviations


def recipe_blocking(recipe: str, expected: dict[str, Any], actual: dict[str, Any]):
    structure = actual.get("structure", {}) if isinstance(actual.get("structure"), dict) else {}
    expected_structure = expected.get("structure", {}) if isinstance(expected.get("structure"), dict) else {}
    deviations = []
    if recipe == "recipe.contour.discrete_three_panel.v1" and structure.get("graph_pages") != expected_structure.get("graph_pages", 1):
        deviations.append({"category": "structure", "code": "WRONG_GRAPH_PAGE_COUNT_FOR_CONTOUR_RECIPE", "expected": expected_structure.get("graph_pages", 1), "actual": structure.get("graph_pages")})
    if recipe == "recipe.bar.grouped_stacked_three_panel.v1" and not structure.get("grouped_stacked_column_implemented", False):
        deviations.append({"category": "plot_family", "code": "PLOT_FAMILY_NOT_IMPLEMENTED", "expected": "grouped_stacked_column", "actual": structure.get("plot_family", "unknown")})
    return deviations


def path_chain_failures(spec: dict[str, Any], base_dir: Path):
    failures = []
    for field in ["source_image"]:
        value = str(spec.get(field) or "")
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            failures.append({"category": "evidence", "code": "NON_SELF_CONTAINED_PATH", "field": field, "path": value})
    for item in spec.get("exports", []):
        value = str(item.get("path") or "")
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            failures.append({"category": "evidence", "code": "NON_SELF_CONTAINED_PATH", "field": "exports.path", "path": value})
        if not resolve_path(base_dir, value).exists():
            failures.append({"category": "evidence", "code": "MISSING_EXPORT_IMAGE", "path": value})
    return failures


def live_same_run_failures(actual: dict[str, Any], run_artifacts: dict[str, Any]):
    failures = []
    if has_seed_fallback(run_artifacts):
        failures.append({"category": "evidence", "code": "SEED_OPJU_FALLBACK_USED"})
    for failure in same_run_failures(run_artifacts):
        failures.append({"category": "evidence", **failure})
    text = json.dumps(run_artifacts, ensure_ascii=False).lower()
    if "inherited_from_run" in text or "inherited_diagnostic" in text:
        failures.append({"category": "evidence", "code": "INHERITED_DIAGNOSTIC_NOT_PASS_ELIGIBLE"})
    if run_artifacts and actual.get("run_id") and run_artifacts.get("run_id") and actual.get("run_id") != run_artifacts.get("run_id"):
        failures.append({"category": "evidence", "code": "ACTUAL_RUN_ID_MISMATCH", "expected": run_artifacts.get("run_id"), "actual": actual.get("run_id")})
    return failures


def benchmark_v55(spec: dict[str, Any], actual: dict[str, Any], run_artifacts: dict[str, Any], base_dir: Path, out_dir: Path):
    expected = spec.get("expected", {}) if isinstance(spec.get("expected"), dict) else {}
    recipe = str(spec.get("recipe") or actual.get("recipe") or "")
    figure_id = str(spec.get("figure_id") or actual.get("figure_id") or "figure")
    critical_style = set(str(item) for item in expected.get("critical_style", []))
    blocking, non_blocking = [], []
    scores = {}
    for category in ["structure", "data", "geometry", "style"]:
        score, b, nb = compare_counts(expected.get(category, {}), actual.get(category, {}), category, critical_style)
        scores[f"{category}_score"] = score
        blocking.extend(b)
        non_blocking.extend(nb)
    sem_score, sem_devs = semantic_coverage(expected.get("required_objects", []), actual.get("objects", []))
    scores["semantic_coverage"] = sem_score
    blocking.extend(sem_devs)
    blocking.extend(recipe_blocking(recipe, expected, actual))
    blocking.extend(path_chain_failures(spec, base_dir))
    blocking.extend(live_same_run_failures(actual, run_artifacts))
    exports = spec.get("exports", [])
    visual = {"status": "failed", "score": 0.0, "artifacts": {}, "roi_results": []}
    if exports and not any(item.get("code") == "MISSING_EXPORT_IMAGE" for item in blocking):
        visual, visual_devs = evaluate_visual(resolve_path(base_dir, str(spec["source_image"])), resolve_path(base_dir, str(exports[0]["path"])), out_dir, expected.get("visual_thresholds", {}), spec.get("rois") or expected.get("rois") or [])
        blocking.extend(visual_devs)
    scores["visual_score"] = visual.get("score", 0.0)
    threshold_semantic = float((expected.get("visual_thresholds") or {}).get("semantic_coverage", 1.0))
    if sem_score < threshold_semantic:
        blocking.append({"category": "semantic", "code": "SEMANTIC_COVERAGE_BELOW_THRESHOLD", "expected": threshold_semantic, "actual": sem_score})
    status = "pass" if not blocking and visual.get("status") == "pass" else "failed"
    if any(item.get("code") in {"SEED_OPJU_FALLBACK_USED", "INHERITED_DIAGNOSTIC_NOT_PASS_ELIGIBLE"} for item in blocking):
        status = "incomplete"
    report = {"schema": REPORT_SCHEMA, "protocol": "originplot.semantic_figure_benchmark.v1+live_semantic_closure.v5.5", "figure_id": figure_id, "recipe": recipe, "run_id": actual.get("run_id") or run_artifacts.get("run_id"), "status": status, "scores": scores, "visual": visual, "actual_source": actual.get("actual_source", {}), "blocking_failures": [item.get("code") for item in blocking], "non_blocking_failures": [item.get("code") for item in non_blocking]}
    ledger = {"schema": LEDGER_SCHEMA, "figure_id": figure_id, "recipe": recipe, "run_id": report["run_id"], "blocking": blocking, "non_blocking": non_blocking}
    return {"report": report, "ledger": ledger}


def benchmark(spec: dict[str, Any], *args):
    # Backward-compatible v5.3 unit-test signature: benchmark(spec, base_dir, out_dir)
    if len(args) == 2 and isinstance(args[0], Path):
        base_dir, out_dir = args
        actual = spec.get("actual", {}) if isinstance(spec.get("actual"), dict) else {}
        return benchmark_v55(spec, actual, {}, base_dir, out_dir)
    if len(args) == 4:
        actual, run_artifacts, base_dir, out_dir = args
        return benchmark_v55(spec, actual, run_artifacts, base_dir, out_dir)
    raise TypeError("benchmark expects (spec, base_dir, out_dir) or (spec, actual, run_artifacts, base_dir, out_dir)")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run OriginPlot v5.5 live semantic closure benchmark.")
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--actual", type=Path)
    parser.add_argument("--run-artifacts", type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--report-out", type=Path)
    parser.add_argument("--ledger-out", type=Path)
    parser.add_argument("--allow-inline-actual", action="store_true")
    args = parser.parse_args()
    spec = read_json(args.benchmark)
    if args.actual:
        actual = read_json(args.actual)
    elif args.allow_inline_actual:
        actual = spec.get("actual", {}) if isinstance(spec.get("actual"), dict) else {}
    else:
        raise SystemExit("v5.5 production benchmark requires --actual generated by benchmark_materializer.py")
    run_artifacts = read_json(args.run_artifacts) if args.run_artifacts else {}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    result = benchmark_v55(spec, actual, run_artifacts, args.benchmark.parent.resolve(), args.out_dir.resolve())
    report_path = args.report_out or args.out_dir / "semantic_benchmark_report.json"
    ledger_path = args.ledger_out or args.out_dir / "deviation_ledger.json"
    write_json(report_path, result["report"])
    write_json(ledger_path, result["ledger"])
    print(json.dumps({"status": result["report"]["status"], "report": str(report_path), "ledger": str(ledger_path)}, ensure_ascii=False, indent=2))
    return 0 if result["report"]["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())
