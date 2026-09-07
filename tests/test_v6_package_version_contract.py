from __future__ import annotations

import json
import shutil
import zipfile
from pathlib import Path

from scripts.build_shareable_package_v6 import build
from scripts.validate_shareable_package_v6 import validate

SKILL_ROOT = Path(__file__).resolve().parents[1]


def _rewrite_entry(source: Path, target: Path, name: str, payload: bytes) -> None:
    with (
        zipfile.ZipFile(source) as src,
        zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as dst,
    ):
        for item in src.infolist():
            data = payload if item.filename == name else src.read(item.filename)
            dst.writestr(item, data)


def test_default_package_validates(tmp_path: Path) -> None:
    zip_path = tmp_path / "originplot-v6.zip"
    build(SKILL_ROOT, zip_path)
    assert validate(zip_path) == []


def test_version_json_must_match_pyproject(tmp_path: Path) -> None:
    # This validator used to pin the literal "6.0.0". That hardcode kept passing
    # while pyproject.toml declared 6.1.2, so it certified a package whose own
    # metadata disagreed with itself.
    zip_path = tmp_path / "originplot-v6.zip"
    build(SKILL_ROOT, zip_path)

    with zipfile.ZipFile(zip_path) as archive:
        version = json.loads(archive.read("version.json").decode("utf-8"))
    version["version"] = "9.9.9"

    drifted = tmp_path / "drifted.zip"
    _rewrite_entry(
        zip_path, drifted, "version.json", json.dumps(version).encode("utf-8")
    )

    errors = validate(drifted)
    assert any("must match" in error for error in errors), errors


def test_aa2195_evidence_identity_is_still_pinned(tmp_path: Path) -> None:
    zip_path = tmp_path / "originplot-v6.zip"
    build(SKILL_ROOT, zip_path)

    with zipfile.ZipFile(zip_path) as archive:
        version = json.loads(archive.read("version.json").decode("utf-8"))
    version["benchmark_evidence"] = {"aa2195": "6.1.2"}

    drifted = tmp_path / "relabelled.zip"
    _rewrite_entry(
        zip_path, drifted, "version.json", json.dumps(version).encode("utf-8")
    )

    errors = validate(drifted)
    assert any("AA2195" in error for error in errors), errors


def test_empty_version_is_rejected(tmp_path: Path) -> None:
    zip_path = tmp_path / "originplot-v6.zip"
    build(SKILL_ROOT, zip_path)

    with zipfile.ZipFile(zip_path) as archive:
        version = json.loads(archive.read("version.json").decode("utf-8"))
    version["version"] = "   "

    drifted = tmp_path / "empty.zip"
    _rewrite_entry(
        zip_path, drifted, "version.json", json.dumps(version).encode("utf-8")
    )

    errors = validate(drifted)
    assert any("nonempty" in error for error in errors), errors


def test_build_is_reproducible_for_identical_input(tmp_path: Path) -> None:
    first = tmp_path / "a.zip"
    second = tmp_path / "b.zip"
    build(SKILL_ROOT, first)
    shutil.copyfile(first, tmp_path / "a-copy.zip")
    build(SKILL_ROOT, second)
    with zipfile.ZipFile(first) as a, zipfile.ZipFile(second) as b:
        assert sorted(a.namelist()) == sorted(b.namelist())
