from __future__ import annotations

from pathlib import Path

from packaging.requirements import Requirement
from packaging.version import Version


ROOT = Path(__file__).resolve().parents[1]


def requirements(path: Path) -> dict[str, Requirement]:
    return {
        item.name.lower(): item
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith(("#", "-r "))
        for item in [Requirement(line)]
    }


def test_origin_requirement_accepts_the_verified_published_release() -> None:
    dependency = requirements(ROOT / "requirements-origin.txt")["originpro"]
    assert Version("1.1.15") in dependency.specifier
    assert Version("3.0") not in dependency.specifier
    assert dependency.marker.evaluate({"platform_system": "Windows"})
    assert not dependency.marker.evaluate({"platform_system": "Linux"})


def test_benchmark_declares_extraction_and_visual_dependencies_separately() -> None:
    benchmark = requirements(ROOT / "requirements-benchmark.txt")
    assert {"pymupdf", "opencv-python", "numpy", "scikit-image"} <= benchmark.keys()
    core = requirements(ROOT / "requirements-core.txt")
    assert not {"pymupdf", "opencv-python", "originpro"} & core.keys()
