from __future__ import annotations

import importlib
from pathlib import Path

from scripts.build_shareable_package_v6 import should_include


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


def test_template_search_module_imports_from_product_context() -> None:
    module = importlib.import_module("scripts.search_official_templates")
    assert callable(module.discover)
    assert callable(module.build_gallery_url)


def test_installable_product_core_does_not_depend_on_root_scripts_package() -> None:
    root = Path(__file__).resolve().parents[1] / "originplot"
    offenders = []
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if "from scripts." in text or "import scripts." in text:
            offenders.append(str(path.relative_to(root.parent)))
    assert offenders == []


def test_installable_runtime_assets_live_inside_originplot_package() -> None:
    root = Path(__file__).resolve().parents[1]
    required = [
        root / "originplot" / "runtime" / "worker.py",
        root / "originplot" / "runtime" / "run_origin_worker_elevated.ps1",
        root / "originplot" / "runtime" / "profiles" / "origin-2022-v6.json",
        root / "originplot" / "runtime" / "profiles" / "origin-2024-v6.json",
        root / "originplot" / "runtime" / "profiles" / "origin-2026-v6.json",
        root / "originplot" / "template" / "gallery.py",
        root / "originplot" / "template" / "retrieve.py",
    ]
    assert [
        str(path.relative_to(root)) for path in required if not path.is_file()
    ] == []


def test_v6_has_single_ordinary_origin_worker_implementation() -> None:
    root = Path(__file__).resolve().parents[1]
    assert not (root / "scripts" / "origin_profile_worker.py").exists()
    assert (root / "originplot" / "runtime" / "worker.py").is_file()


def test_v6_capability_profiles_have_one_canonical_location() -> None:
    root = Path(__file__).resolve().parents[1]
    duplicates = [
        root / "capabilities" / f"origin-{version}-v6.json"
        for version in ("2022", "2024", "2026")
    ]
    assert [str(path.relative_to(root)) for path in duplicates if path.exists()] == []


def test_wheel_configuration_includes_runtime_package_data() -> None:
    root = Path(__file__).resolve().parents[1]
    pyproject = (root / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.setuptools.package-data]" in pyproject
    assert '"originplot.runtime" = ["*.ps1", "profiles/*.json"]' in pyproject


def test_v6_shareable_builder_excludes_cache_artifacts(tmp_path: Path) -> None:
    cache_file = tmp_path / "originplot" / "__pycache__" / "module.pyc"
    source_file = tmp_path / "originplot" / "runtime" / "worker.py"
    cache_file.parent.mkdir(parents=True)
    source_file.parent.mkdir(parents=True)
    cache_file.write_bytes(b"cache")
    source_file.write_text("# source", encoding="utf-8")

    assert not should_include(cache_file, tmp_path)
    assert should_include(source_file, tmp_path)
