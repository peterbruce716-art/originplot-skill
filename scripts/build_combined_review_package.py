from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any


def add_file(archive: zipfile.ZipFile, path: Path, arcname: str) -> None:
    archive.write(path, arcname=Path(arcname).as_posix())


def _path_key(value: str | Path) -> str:
    return str(Path(value).resolve()).replace("/", "\\").casefold()


def _sanitize_json_value(
    value: Any,
    path_targets: dict[str, str],
    basename_targets: dict[str, list[str]],
) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize_json_value(item, path_targets, basename_targets) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_json_value(item, path_targets, basename_targets) for item in value]
    if not isinstance(value, str):
        return value
    try:
        direct = path_targets.get(_path_key(value))
    except (OSError, ValueError):
        direct = None
    if direct:
        return direct
    if Path(value).is_absolute() or re.match(r"^[A-Za-z]:[\\/]", value):
        matches = basename_targets.get(Path(value).name.casefold(), [])
        if len(matches) == 1:
            return matches[0]
    return value


def _json_bytes_for_package(
    source: Path,
    path_targets: dict[str, str],
    basename_targets: dict[str, list[str]],
) -> bytes:
    payload = json.loads(source.read_text(encoding="utf-8-sig"))
    sanitized = _sanitize_json_value(payload, path_targets, basename_targets)
    return (json.dumps(sanitized, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def build(zip_out: Path, files: list[tuple[Path, str]]) -> dict[str, object]:
    zip_out.parent.mkdir(parents=True, exist_ok=True)
    normalized_files = [(Path(src), Path(arcname).as_posix()) for src, arcname in files]
    path_targets = {_path_key(src): arcname for src, arcname in normalized_files}
    basename_targets: dict[str, list[str]] = {}
    for src, arcname in normalized_files:
        basename_targets.setdefault(src.name.casefold(), []).append(arcname)
    entries = []
    with zipfile.ZipFile(zip_out, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for src, normalized in normalized_files:
            if src.exists() and src.is_file():
                if src.suffix.lower() == ".json":
                    archive.writestr(normalized, _json_bytes_for_package(src, path_targets, basename_targets))
                else:
                    add_file(archive, src, normalized)
                entries.append(normalized)
    return {"schema": "originplot.combined_review_package.v1", "zip": str(zip_out), "entry_count": len(entries), "entries": entries}


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a POSIX-path OriginPlot combined review package.")
    parser.add_argument("--zip-out", required=True, type=Path)
    parser.add_argument("--file", action="append", nargs=2, metavar=("SRC", "ARCNAME"), default=[])
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = build(args.zip_out, [(Path(src), arc) for src, arc in args.file])
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
