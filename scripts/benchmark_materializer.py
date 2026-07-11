from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "originplot.benchmark_actual.v1"


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def source_record(path: Path) -> dict[str, Any]:
    return {"path": path.name, "sha256": sha256_file(path), "size_bytes": path.stat().st_size}


def source_field(file_name: str, pointer: str, value: Any) -> dict[str, Any]:
    return {"source_file": file_name, "json_pointer": pointer, "value": value}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def materialize(
    *,
    recipe: dict[str, Any],
    inspection: dict[str, Any],
    qa_report: dict[str, Any],
    run_artifacts: dict[str, Any],
    figurespec: dict[str, Any],
    source_files: dict[str, Path],
) -> dict[str, Any]:
    graph_pages = _list(inspection.get("graph_pages"))
    workbooks = _list(inspection.get("workbooks"))
    matrices = _list(inspection.get("matrices"))
    layer_details = []
    for page in graph_pages:
        layer_details.extend(_list(page.get("layer_details")))

    structure = {
        "graph_pages": len(graph_pages),
        "layers": sum(int(page.get("layers") or 0) for page in graph_pages),
        "plots": sum(int(layer.get("plots") or 0) for layer in layer_details),
        "workbooks": len(workbooks),
        "matrices": len(matrices),
    }
    data = dict(inspection.get("data") or {})
    data.setdefault("workbooks", len(workbooks))
    data.setdefault("matrices", len(matrices))
    geometry = dict(inspection.get("geometry") or {})
    geometry.setdefault("panel_count", structure["layers"])
    style = dict(inspection.get("style") or {})

    object_rows = inspection.get("objects") or inspection.get("semantic_objects") or []
    object_counts: dict[str, int] = {}
    if isinstance(object_rows, list):
        for item in object_rows:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or item.get("type") or "")
            if role:
                object_counts[role] = object_counts.get(role, 0) + int(item.get("count") or 1)
    objects = [{"role": role, "count": count} for role, count in sorted(object_counts.items())]

    actual = {
        "schema": SCHEMA,
        "figure_id": recipe.get("figure_id") or figurespec.get("figure_id"),
        "recipe": recipe.get("recipe") or figurespec.get("recipe"),
        "run_id": run_artifacts.get("run_id"),
        "structure": structure,
        "data": data,
        "geometry": geometry,
        "style": style,
        "objects": objects,
        "actual_source": {
            "inspection": source_record(source_files["inspection"]),
            "qa_report": source_record(source_files["qa_report"]),
            "run_artifacts": source_record(source_files["run_artifacts"]),
            "figurespec": source_record(source_files["figurespec"]),
        },
        "field_sources": [
            source_field("inspection.json", "/graph_pages", structure["graph_pages"]),
            source_field("inspection.json", "/workbooks", structure["workbooks"]),
            source_field("inspection.json", "/matrices", structure["matrices"]),
            source_field("inspection.json", "/objects", objects),
            source_field("qa_report.json", "/", qa_report.get("status")),
            source_field("run_artifacts.json", "/run_id", run_artifacts.get("run_id")),
        ],
    }
    return actual


def main() -> int:
    parser = argparse.ArgumentParser(description="Materialize v5.4 benchmark actual from inspection/QA/run evidence.")
    parser.add_argument("--benchmark", required=True, type=Path)
    parser.add_argument("--inspection", required=True, type=Path)
    parser.add_argument("--qa-report", required=True, type=Path)
    parser.add_argument("--run-artifacts", required=True, type=Path)
    parser.add_argument("--figurespec", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()

    payload = materialize(
        recipe=read_json(args.benchmark),
        inspection=read_json(args.inspection),
        qa_report=read_json(args.qa_report),
        run_artifacts=read_json(args.run_artifacts),
        figurespec=read_json(args.figurespec),
        source_files={
            "inspection": args.inspection,
            "qa_report": args.qa_report,
            "run_artifacts": args.run_artifacts,
            "figurespec": args.figurespec,
        },
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "actual": str(args.out), "run_id": payload.get("run_id")}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
