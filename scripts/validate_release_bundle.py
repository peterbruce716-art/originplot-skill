from __future__ import annotations

import argparse
import json
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any


CACHE_NAMES = {"__pycache__", ".pytest_cache", "tmp_v5_validation"}
CACHE_SUFFIXES = {".pyc", ".pyo"}
ABSOLUTE_RE = re.compile(r"(?:^[A-Za-z]:[\\/]|[A-Za-z]:[\\/]Users[\\/]|/(?:home|Users)/[^/\s]+/)")


def _json_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _json_strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _json_strings(item)


def _artifact_paths(value: Any):
    if isinstance(value, dict):
        if "path" in value and value.get("exists") is True:
            yield str(value["path"])
        for item in value.values():
            yield from _artifact_paths(item)
    elif isinstance(value, list):
        for item in value:
            yield from _artifact_paths(item)


def _validate_directory(root: Path) -> dict[str, Any]:
    root = root.resolve()
    files = [path for path in root.rglob("*") if path.is_file()]
    cache_hits = [path.relative_to(root).as_posix() for path in files if set(path.relative_to(root).parts) & CACHE_NAMES or path.suffix.lower() in CACHE_SUFFIXES]
    absolute_hits: list[dict[str, str]] = []
    broken_hits: list[dict[str, str]] = []
    for path in files:
        if path.suffix.lower() not in {".json", ".md", ".txt", ".yaml", ".yml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            continue
        for line in text.splitlines():
            if ABSOLUTE_RE.search(line):
                absolute_hits.append({"file": path.relative_to(root).as_posix(), "value": line.strip()[:200]})
        if path.suffix.lower() == ".json":
            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                continue
            for value in _json_strings(payload):
                if ABSOLUTE_RE.search(value):
                    hit = {"file": path.relative_to(root).as_posix(), "value": value[:200]}
                    if hit not in absolute_hits:
                        absolute_hits.append(hit)
            for raw in _artifact_paths(payload):
                ref = Path(raw)
                local_ref = path.parent / ref
                root_ref = root / ref
                if ref.is_absolute() or ".." in ref.parts or not (local_ref.exists() or root_ref.exists()):
                    broken_hits.append({"file": path.relative_to(root).as_posix(), "reference": raw})
    clean = not cache_hits and not absolute_hits and not broken_hits
    return {
        "schema": "originplot.release_bundle_validation.v1",
        "bundle_validation": {
            "clean": clean,
            "portable": clean,
            "absolute_path_hits": len(absolute_hits),
            "cache_artifact_hits": len(cache_hits),
            "broken_reference_hits": len(broken_hits),
        },
        "findings": {"absolute_paths": absolute_hits, "cache_artifacts": cache_hits, "broken_references": broken_hits},
    }


def validate_release_bundle(path: Path) -> dict[str, Any]:
    path = Path(path)
    if path.is_dir():
        return _validate_directory(path)
    with tempfile.TemporaryDirectory(prefix="originplot_p18_bundle_") as tmp:
        with zipfile.ZipFile(path) as archive:
            unsafe = [name for name in archive.namelist() if Path(name).is_absolute() or ".." in Path(name).parts]
            if unsafe:
                return {"schema": "originplot.release_bundle_validation.v1", "bundle_validation": {"clean": False, "portable": False, "absolute_path_hits": len(unsafe), "cache_artifact_hits": 0, "broken_reference_hits": 0}, "findings": {"unsafe_entries": unsafe}}
            archive.extractall(tmp)
        return _validate_directory(Path(tmp))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = validate_release_bundle(args.path)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result["bundle_validation"]["clean"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
