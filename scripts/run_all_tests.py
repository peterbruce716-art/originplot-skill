from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

try:
    from scripts.versioning import load_versions
except ImportError:  # executed as `python scripts/run_all_tests.py`
    from versioning import load_versions

SUMMARY_RE = re.compile(
    r"^(?:=+\s*)?(?:(?P<failed>\d+) failed,?\s*)?(?P<passed>\d+) passed"
    r"(?:,\s*(?P<skipped>\d+) skipped)?",
    re.MULTILINE,
)


def discover_tests() -> list[str]:
    """Return every pytest module under ``tests/``.

    The previous implementation globbed only ``tests/test_v6_*.py``, which
    silently skipped the contract suites in ``tests/capability``,
    ``tests/contract``, ``tests/contracts``, ``tests/fail_closed`` and
    ``tests/package_boundary``. A runner named "run all tests" must not
    quietly cover a subset.
    """
    return sorted(
        str(path.relative_to(ROOT)) for path in (ROOT / "tests").rglob("test_*.py")
    )


def parse_summary(output: str) -> dict[str, int]:
    """Extract pass/fail/skip counts from pytest's terse summary line."""
    counts = {"passed": 0, "failed": 0, "skipped": 0}
    for match in SUMMARY_RE.finditer(output):
        for key in counts:
            value = match.group(key)
            if value is not None:
                counts[key] = int(value)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run every OriginPlot test module and report a machine-readable result."
    )
    parser.add_argument(
        "--expected-min-tests",
        type=int,
        default=0,
        help="fail when fewer than this many tests run",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="write an originplot.run_all_tests.v1 record here",
    )
    args = parser.parse_args()

    tests = discover_tests()
    if not tests:
        print("no tests found", file=sys.stderr)
        return 2
    versions = load_versions(ROOT)
    print(
        f"OriginPlot {versions.release_version} test runner "
        f"(contract {versions.contract_version}): {len(tests)} modules"
    )

    completed = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", *tests],
        cwd=str(ROOT),
        text=True,
        capture_output=True,
        check=False,
    )
    output = completed.stdout + completed.stderr
    print(output, end="")

    counts = parse_summary(output)
    tests_run = counts["passed"] + counts["failed"]
    test_errors: list[str] = []
    if completed.returncode != 0:
        test_errors.append(f"pytest exited {completed.returncode}")
    if counts["failed"]:
        test_errors.append(f"{counts['failed']} failed")
    if tests_run < args.expected_min_tests:
        test_errors.append(
            f"{tests_run} tests ran, expected at least {args.expected_min_tests}"
        )

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps(
                {
                    "schema": "originplot.run_all_tests.v1",
                    "status": "ok" if not test_errors else "failed",
                    "release_version": versions.release_version,
                    "contract_version": versions.contract_version,
                    "modules": tests,
                    "tests_run": tests_run,
                    "passed": counts["passed"],
                    "failed": counts["failed"],
                    "skipped": counts["skipped"],
                    "expected_min_tests": args.expected_min_tests,
                    "test_errors": test_errors,
                    "compile_failures": [],
                    "returncode": completed.returncode,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return 0 if not test_errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
