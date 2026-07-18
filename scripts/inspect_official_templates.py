from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from builders.aa2195.session import has_visible_origin_process, is_administrator_python
from scripts.versioning import load_versions


VERSIONS = load_versions(ROOT)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def json_value(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return value


def resolve_project(manifest_path: Path, raw_path: str, project_root: Path | None) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    candidates = []
    if project_root is not None:
        candidates.append(project_root / path)
    candidates.extend([manifest_path.parent / path, Path.cwd() / path])
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve() if candidates else path.resolve()


def worksheet_record(sheet: Any) -> dict[str, Any]:
    try:
        rows, columns = sheet.shape
    except Exception:
        rows, columns = None, None
    return {
        "name": str(getattr(sheet, "name", "") or ""),
        "long_name": str(getattr(sheet, "lname", "") or ""),
        "rows": rows,
        "columns": columns,
    }


def inspect_templates(manifest_path: Path, output_path: Path, project_root: Path | None) -> dict[str, Any]:
    if not is_administrator_python():
        raise RuntimeError(
            "E120_ENVIRONMENT_MISMATCH: administrator Python is required before importing originpro"
        )
    if not has_visible_origin_process():
        raise RuntimeError(
            "E121_ATTACH_POLICY_VIOLATION: start a visible administrator Origin instance before inspection"
        )

    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    records = manifest.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("Official-template manifest has no records")

    projects = []
    for record in records:
        project = resolve_project(
            manifest_path,
            str(record.get("primary_project_file", "")),
            project_root,
        )
        if not project.is_file():
            raise FileNotFoundError(f"Official template project is missing: {project}")
        projects.append((record, project))

    import originpro as op  # type: ignore
    from builders.aa2195.readback import inspect_page

    report: dict[str, Any] = {
        "schema": "originplot.official_template_inspection.v1",
        "skill_version": VERSIONS.contract_version,
        **VERSIONS.as_dict(),
        "source_manifest": str(manifest_path.resolve()),
        "administrator_python": True,
        "visible_administrator_origin_required": True,
        "release": "op.detach()",
        "templates": {},
    }
    attached = False
    try:
        op.attach()
        attached = True
        for record, project in projects:
            gid = str(record.get("gid", project.stem))
            op.new(asksave=False)
            if not op.open(str(project), readonly=False, asksave=False):
                raise RuntimeError(f"Origin could not open official template {gid}: {project}")

            workbooks = []
            total_rows = 0
            for book in op.pages("w"):
                sheets = [worksheet_record(sheet) for sheet in book]
                total_rows += sum(int(item["rows"] or 0) for item in sheets)
                workbooks.append(
                    {
                        "name": str(getattr(book, "name", "") or ""),
                        "long_name": str(getattr(book, "lname", "") or ""),
                        "sheets": sheets,
                    }
                )
            graphs = []
            for page in op.pages("g"):
                page.activate()
                graphs.append(inspect_page(op, page))

            report["templates"][gid] = {
                "title": record.get("title"),
                "gallery_url": record.get("gallery_url"),
                "download_url": record.get("download_url"),
                "figure_roles": record.get("figure_roles", {}),
                "recommended_use": record.get("recommended_use"),
                "project_path": str(project),
                "project_sha256": sha256(project),
                "archive_sha256": record.get("zip_sha256"),
                "compatible_open": True,
                "opened_editable": True,
                "worksheet_rows_total": total_rows,
                "workbooks": workbooks,
                "graphs": graphs,
            }
        report["status"] = "ok"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(json_value(report), ensure_ascii=False, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        return report
    finally:
        if attached:
            try:
                op.new(asksave=False)
            finally:
                op.detach()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect downloaded OriginLab Graph Gallery projects in administrator Origin."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--project-root", type=Path)
    args = parser.parse_args()
    report = inspect_templates(args.manifest, args.output, args.project_root)
    summary = {
        "status": report["status"],
        "output": str(args.output.resolve()),
        "template_count": len(report["templates"]),
        "gids": sorted(report["templates"]),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
