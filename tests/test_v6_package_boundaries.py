from __future__ import annotations

from pathlib import Path


def test_product_core_does_not_import_aa2195_benchmark() -> None:
    root = Path(__file__).resolve().parents[1] / "originplot"
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "benchmarks.aa2195" in text or "builders.aa2195" in text:
            offenders.append(str(path.relative_to(root.parent)))
    assert offenders == []


def test_aa2195_isolated_under_benchmarks() -> None:
    root = Path(__file__).resolve().parents[1]
    assert (root / "benchmarks" / "aa2195" / "builders" / "fig12_builder.py").is_file()
    assert not (root / "builders" / "aa2195").exists()


def test_aa2195_benchmark_does_not_import_root_legacy_runtime() -> None:
    root = Path(__file__).resolve().parents[1]
    benchmark = root / "benchmarks" / "aa2195"
    offenders = []
    for path in benchmark.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from runtime." in text or "import runtime." in text:
            offenders.append(str(path.relative_to(root)))
    assert offenders == []


def test_aa2195_duplicates_are_not_exposed_as_product_examples_or_references() -> None:
    root = Path(__file__).resolve().parents[1]
    forbidden = [
        root / "references" / "aa2195-benchmark.md",
        root / "references" / "aa2195-release-evidence.json",
        root / "examples" / "candidates",
        root / "examples" / "template_search" / "aa2195_official_template_search.json",
    ]
    assert [str(path.relative_to(root)) for path in forbidden if path.exists()] == []
