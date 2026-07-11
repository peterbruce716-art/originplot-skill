from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


STRICT_DATA_OK = {"raw_data_verified", "vector_extracted_verified", "digitized_with_error_bounds"}


def resolve(roots: list[Path], value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    if path.is_absolute():
        return path
    candidates = [root / path for root in roots]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0] if candidates else path


def validate_manifest(manifest_path: Path) -> dict[str, Any]:
    resolved_manifest = manifest_path.resolve()
    manifest = json.loads(resolved_manifest.read_text(encoding="utf-8"))
    explicit_root = manifest.get("package_root")
    roots = [resolved_manifest.parent]
    if explicit_root:
        roots.insert(0, Path(explicit_root).expanduser().resolve())
    roots.extend(list(resolved_manifest.parents[1:4]))
    roots.append(Path.cwd())
    origin = manifest.get("origin_result", {})
    per_figure = origin.get("per_figure", {})
    checks: list[dict[str, Any]] = []

    excel = resolve(roots, manifest.get("excel_package"))
    checks.append({"name": "excel_package_exists", "ok": bool(excel and excel.exists()), "path": str(excel) if excel else None})

    for fig_id, fig in per_figure.items():
        opju = resolve(roots, fig.get("opju_path"))
        data_status = fig.get("data_provenance_status")
        image_status = fig.get("image_consistency_status")
        strict_status = fig.get("strict_source_exact_status")
        strict_image_status = fig.get("strict_original_image_reproduction_status")
        open_status = (fig.get("opju_open_validation") or {}).get("status")
        structure_status = (fig.get("opju_structure_validation") or {}).get("status")
        qa_items = fig.get("origin_export_qa") or []
        qa_pass = bool(qa_items) and all((item.get("qa_status") or item.get("status")) in {"pass", "image_consistent"} for item in qa_items)
        checks.extend(
            [
                {"figure": fig_id, "name": "opju_exists", "ok": bool(opju and opju.exists()), "path": str(opju) if opju else None},
                {"figure": fig_id, "name": "has_origin_data_sheets", "ok": bool(fig.get("origin_data_sheets"))},
                {"figure": fig_id, "name": "opju_reopens_cleanly", "ok": open_status == "ok", "value": open_status},
                {"figure": fig_id, "name": "opju_structural_contract", "ok": structure_status == "pass", "value": structure_status},
                {"figure": fig_id, "name": "origin_export_qa_passes", "ok": qa_pass, "value": [item.get("qa_status") or item.get("status") for item in qa_items]},
                {"figure": fig_id, "name": "data_provenance_recorded", "ok": bool(data_status), "value": data_status},
                {"figure": fig_id, "name": "strict_source_exact_satisfied", "ok": strict_status == "strict_source_exact_satisfied", "value": strict_status},
                {"figure": fig_id, "name": "strict_data_provenance", "ok": data_status in STRICT_DATA_OK, "value": data_status},
                {"figure": fig_id, "name": "image_consistent", "ok": image_status == "image_consistent", "value": image_status},
                {"figure": fig_id, "name": "strict_original_image_complete", "ok": strict_image_status == "strict_reproduction_completed", "value": strict_image_status},
            ]
        )

    blocking = [check for check in checks if not check["ok"]]
    return {
        "manifest": str(manifest_path),
        "origin_status": origin.get("status"),
        "figure_count": len(per_figure),
        "status": "pass" if not blocking else "incomplete",
        "checks": checks,
        "blocking": blocking,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an Origin figure reproduction package manifest.")
    parser.add_argument("manifest", type=Path, help="Path to manifest.json.")
    parser.add_argument("--json-out", type=Path, help="Optional JSON output path.")
    parser.add_argument("--fail-on-incomplete", action="store_true", help="Return nonzero when strict checks are incomplete.")
    args = parser.parse_args()

    result = validate_manifest(args.manifest)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 2 if args.fail_on_incomplete and result["status"] != "pass" else 0


if __name__ == "__main__":
    raise SystemExit(main())
