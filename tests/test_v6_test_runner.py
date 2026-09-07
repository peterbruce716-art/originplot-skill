from __future__ import annotations

from pathlib import Path

from scripts.run_all_tests import discover_tests, parse_summary

ROOT = Path(__file__).resolve().parents[1]


def test_discovery_covers_the_contract_suites() -> None:
    modules = discover_tests()
    # The old glob was tests/test_v6_*.py only, which missed every subdirectory.
    for subdir in (
        "capability",
        "contract",
        "contracts",
        "fail_closed",
        "package_boundary",
    ):
        assert any(f"{subdir}" in module for module in modules), subdir
    on_disk = sorted(
        str(p.relative_to(ROOT)) for p in (ROOT / "tests").rglob("test_*.py")
    )
    assert modules == on_disk


def test_parse_summary_reads_a_clean_run() -> None:
    assert parse_summary("103 passed in 2.48s") == {
        "passed": 103,
        "failed": 0,
        "skipped": 0,
    }


def test_parse_summary_reads_failures_and_skips() -> None:
    counts = parse_summary("2 failed, 100 passed, 3 skipped in 1.20s")
    assert counts == {"passed": 100, "failed": 2, "skipped": 3}


def test_parse_summary_is_empty_when_pytest_says_nothing() -> None:
    assert parse_summary("collected 0 items") == {
        "passed": 0,
        "failed": 0,
        "skipped": 0,
    }
