from __future__ import annotations

import posixpath
import re
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from scripts.build_shareable_package_v6 import build
from scripts.validate_shareable_package_v6 import validate

ROOT = Path(__file__).resolve().parents[1]
GUIDES = (
    "docs/AGENT_QUICKSTART.md",
    "docs/CAPABILITY_MATRIX.md",
    "docs/DEVELOPMENT_GUIDE_v6.1.md",
)


def _assert_bundled_links(documents: dict[str, str]) -> None:
    pending, seen = ["SKILL.md"], set()
    while pending:
        name = pending.pop()
        if name in seen:
            continue
        seen.add(name)
        assert not re.search(r"(?m)^[ \t]{0,3}\[[^\]\n]+\]:", documents[name]), (
            f"workflow guides must use inline links for package checks: {name}"
        )
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", documents[name]):
            url = urlsplit(target)
            if url.scheme or url.netloc:
                continue
            path = (
                posixpath.normpath(
                    posixpath.join(posixpath.dirname(name), unquote(url.path))
                )
                if url.path
                else name
            )
            assert path in documents, f"missing linked document: {name} -> {target}"
            if url.fragment:
                headings = re.findall(r"^#+ (.+)$", documents[path], re.MULTILINE)
                anchors = {
                    re.sub(r"[^\w\- ]", "", heading.lower()).replace(" ", "-")
                    for heading in headings
                }
                assert unquote(url.fragment) in anchors, f"broken fragment: {target}"
            pending.append(path)


def test_built_compact_package_has_self_contained_workflow(tmp_path: Path) -> None:
    package = tmp_path / "runtime.zip"
    build(ROOT, package)
    with zipfile.ZipFile(package) as archive:
        documents = {
            name: archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.endswith(".md")
        }
    assert all(guide in documents for guide in GUIDES)
    assert all(f"]({guide})" in documents["SKILL.md"] for guide in GUIDES)
    _assert_bundled_links(documents)
    assert validate(package) == []


@pytest.mark.parametrize("missing", GUIDES)
def test_package_rejects_missing_operational_guide(
    tmp_path: Path, missing: str
) -> None:
    complete, broken = tmp_path / "complete.zip", tmp_path / "broken.zip"
    build(ROOT, complete)
    with zipfile.ZipFile(complete) as source, zipfile.ZipFile(broken, "w") as target:
        for item in source.infolist():
            if item.filename != missing:
                target.writestr(item, source.read(item.filename))
    assert any(missing in error for error in validate(broken))


@pytest.mark.parametrize("second_link", ["missing.md", "../SKILL.md#missing-heading"])
def test_document_check_rejects_broken_transitive_links(second_link: str) -> None:
    documents = {
        "SKILL.md": "# Skill\n[Guide](docs/guide.md)",
        "docs/guide.md": f"# Guide\n[Next]({second_link})",
    }
    with pytest.raises(AssertionError):
        _assert_bundled_links(documents)


def test_document_check_accepts_relative_heading_link() -> None:
    _assert_bundled_links(
        {
            "SKILL.md": "# Skill\n[Guide](docs/guide.md#live-session)",
            "docs/guide.md": "# Live Session\n[Back](../SKILL.md)",
        }
    )


@pytest.mark.parametrize("link", ["[Guide][route]", "[route][]", "[route]"])
def test_document_check_requires_inspectable_inline_links(link: str) -> None:
    with pytest.raises(AssertionError, match="must use inline links"):
        _assert_bundled_links({"SKILL.md": f"{link}\n\n[route]: missing.md#absent"})
