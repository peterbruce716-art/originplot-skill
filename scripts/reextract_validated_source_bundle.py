from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.extract_aa2195_fresh_source_bundle import FIGURES, SCHEMA, _extract_fig14_data
except ImportError:
    from extract_aa2195_fresh_source_bundle import FIGURES, SCHEMA, _extract_fig14_data


POLICY = "validated_crop_reextract"
REEXTRACTED_FIGURES = ("fig14",)


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _stable_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def reextract_bundle(reuse_record_path: Path, output_dir: Path) -> dict[str, Any]:
    reuse_record_path = reuse_record_path.resolve()
    output_dir = output_dir.resolve()
    reuse = _load(reuse_record_path)
    if reuse.get("schema") != "originplot.aa2195_validated_data_reuse.v1" or reuse.get("status") != "ok":
        raise ValueError("validated source reuse record is invalid")

    parent_manifest = Path(str(reuse.get("source_bundle_manifest", "")))
    if not parent_manifest.is_absolute():
        parent_manifest = (reuse_record_path.parent / parent_manifest).resolve()
    if not parent_manifest.is_file():
        raise ValueError("validated parent source manifest is missing")
    parent_manifest_sha256 = _sha256_file(parent_manifest)
    if parent_manifest_sha256 != str(reuse.get("source_bundle_manifest_sha256", "")).lower():
        raise ValueError("validated parent source manifest hash mismatch")

    parent = _load(parent_manifest)
    if parent.get("schema") != SCHEMA:
        raise ValueError("validated parent source bundle schema is invalid")
    expected_parent_digest = _stable_digest({
        figure: {
            "source_crop_sha256": parent.get("figures", {}).get(figure, {}).get("source_crop_sha256"),
            "data_sha256": parent.get("figures", {}).get(figure, {}).get("data_sha256"),
        }
        for figure in FIGURES
    })
    if expected_parent_digest != str(parent.get("bundle_data_sha256", "")).lower():
        raise ValueError("validated parent source bundle digest is invalid")
    if expected_parent_digest != str(reuse.get("source_bundle_data_sha256", "")).lower():
        raise ValueError("reuse record parent bundle digest mismatch")

    if output_dir.exists() and any(output_dir.iterdir()):
        raise RuntimeError("E126_STALE_OUTPUT_ROOT: re-extracted source bundle directory must be empty")
    output_dir.mkdir(parents=True, exist_ok=True)

    figures: dict[str, Any] = {}
    for figure in FIGURES:
        source_record = parent.get("figures", {}).get(figure)
        reuse_figure = reuse.get("figures", {}).get(figure)
        if not isinstance(source_record, dict) or not isinstance(reuse_figure, dict):
            raise ValueError(f"validated source lineage is missing for {figure}")
        quality_pass = (
            reuse_figure.get("structure_pass") is True
            and reuse_figure.get("visual_pass") is True
            and reuse_figure.get("live_origin_verified") is True
            and reuse_figure.get("overall_release_pass") is True
            and reuse_figure.get("provenance") == "live_same_run"
        )
        if not quality_pass:
            raise ValueError(f"validated source quality gates did not pass for {figure}")
        if str(source_record.get("data_sha256", "")).lower() != str(reuse_figure.get("data_sha256", "")).lower():
            raise ValueError(f"validated source data hash mismatch for {figure}")
        if str(source_record.get("source_crop_sha256", "")).lower() != str(reuse_figure.get("source_crop_sha256", "")).lower():
            raise ValueError(f"validated source crop record mismatch for {figure}")

        crop_raw = str(source_record.get("source_crop", ""))
        crop_name = Path(crop_raw).name
        source_crop = (parent_manifest.parent / crop_raw).resolve()
        if source_crop.parent != parent_manifest.parent.resolve() or crop_name != crop_raw:
            raise ValueError(f"validated source crop path is not a local bundle filename for {figure}")
        if not source_crop.is_file() or _sha256_file(source_crop) != str(source_record.get("source_crop_sha256", "")).lower():
            raise ValueError(f"validated source crop hash mismatch for {figure}")
        target_crop = output_dir / crop_name
        shutil.copy2(source_crop, target_crop)

        data = source_record.get("data")
        if not isinstance(data, dict):
            raise ValueError(f"validated source data is missing for {figure}")
        data_policy = "validated_reuse"
        if figure == "fig14":
            data = _extract_fig14_data(target_crop)
            data_policy = POLICY
        record = dict(source_record)
        record.update({
            "source_crop": crop_name,
            "source_crop_sha256": _sha256_file(target_crop),
            "source_crop_size_bytes": target_crop.stat().st_size,
            "data": data,
            "data_sha256": _stable_digest(data),
            "data_policy": data_policy,
            "parent_data_sha256": str(source_record["data_sha256"]).lower(),
        })
        figures[figure] = record

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "fresh_extraction": False,
        "validated_crop_reextract": True,
        "source_data_policy": POLICY,
        "reextracted_figures": list(REEXTRACTED_FIGURES),
        "parent_source_bundle_manifest": str(parent_manifest),
        "parent_source_bundle_manifest_sha256": parent_manifest_sha256,
        "parent_source_bundle_data_sha256": expected_parent_digest,
        "source_reuse_record": str(reuse_record_path),
        "source_reuse_record_sha256": _sha256_file(reuse_record_path),
        "source_pdf": parent.get("source_pdf", {}),
        "figures": figures,
    }
    payload["bundle_data_sha256"] = _stable_digest({
        figure: {
            "source_crop_sha256": figures[figure]["source_crop_sha256"],
            "data_sha256": figures[figure]["data_sha256"],
        }
        for figure in FIGURES
    })
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Re-extract corrected Fig14 data from a quality-validated AA2195 source crop bundle."
    )
    parser.add_argument("--reuse-record", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    payload = reextract_bundle(args.reuse_record, args.output_dir)
    json_out = args.json_out.resolve() if args.json_out else args.output_dir.resolve() / "source_bundle.json"
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "ok", "json_out": str(json_out), "bundle_data_sha256": payload["bundle_data_sha256"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
