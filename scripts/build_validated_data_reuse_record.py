from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


FIGURES = ("fig3", "fig12", "fig14", "fig15", "fig16")
SCHEMA = "originplot.aa2195_validated_data_reuse.v1"


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
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_reuse_record(batch_root: Path) -> dict[str, Any]:
    batch_root = batch_root.resolve()
    audit = _load(batch_root / "five_figure_batch_audit.json")
    status = _load(batch_root / "live_validation_status.json")
    if audit.get("status") != "pass" or audit.get("findings") not in ([], None):
        raise ValueError("prior batch audit did not pass without findings")
    if status.get("status") != "completed":
        raise ValueError("prior batch did not complete")

    source_manifest_raw = str(status.get("source_bundle_manifest", "")).strip()
    if not source_manifest_raw:
        raise ValueError("prior batch does not identify a source bundle manifest")
    source_manifest = Path(source_manifest_raw)
    if not source_manifest.is_absolute():
        source_manifest = (batch_root / source_manifest).resolve()
    source_bundle = _load(source_manifest)
    if source_bundle.get("schema") != "originplot.aa2195_fresh_source_bundle.v1":
        raise ValueError("prior source bundle schema is invalid")

    expected_bundle_digest = _stable_digest(
        {
            figure: {
                "source_crop_sha256": source_bundle.get("figures", {}).get(figure, {}).get("source_crop_sha256"),
                "data_sha256": source_bundle.get("figures", {}).get(figure, {}).get("data_sha256"),
            }
            for figure in FIGURES
        }
    )
    if expected_bundle_digest != str(source_bundle.get("bundle_data_sha256", "")).lower():
        raise ValueError("prior source bundle digest is invalid")

    figures: dict[str, Any] = {}
    for figure in FIGURES:
        manifest = _load(batch_root / figure / "candidate_manifest.json")
        readback = _load(batch_root / figure / "candidate_readback.json")
        run_manifest = _load(batch_root / figure / "evidence" / "run_manifest.json")
        source_gate = readback.get("source_data_gate") or readback.get("fresh_source_gate")
        if not isinstance(source_gate, dict) or source_gate.get("status") != "pass":
            raise ValueError(f"prior source data gate did not pass for {figure}")
        source_record = source_bundle.get("figures", {}).get(figure)
        if not isinstance(source_record, dict):
            raise ValueError(f"prior source bundle is missing {figure}")
        required_truth = (
            manifest.get("structure_pass") is True
            and manifest.get("visual_pass") is True
            and manifest.get("live_origin_verified") is True
            and run_manifest.get("release_status", {}).get("overall_release_pass") is True
            and run_manifest.get("provenance") == "live_same_run"
        )
        if not required_truth:
            raise ValueError(f"prior quality gates did not pass for {figure}")
        if str(source_gate.get("data_sha256", "")).lower() != str(source_record.get("data_sha256", "")).lower():
            raise ValueError(f"prior data hash mismatch for {figure}")
        if str(source_gate.get("source_crop_sha256", "")).lower() != str(source_record.get("source_crop_sha256", "")).lower():
            raise ValueError(f"prior crop hash mismatch for {figure}")
        figures[figure] = {
            "run_id": str(run_manifest.get("run_id", "")),
            "provenance": "live_same_run",
            "structure_pass": True,
            "visual_pass": True,
            "live_origin_verified": True,
            "overall_release_pass": True,
            "data_sha256": str(source_record["data_sha256"]).lower(),
            "source_crop_sha256": str(source_record["source_crop_sha256"]).lower(),
        }

    return {
        "schema": SCHEMA,
        "status": "ok",
        "reuse_scope": "scientific_data_and_source_crops_only",
        "forbidden_reuse": ["opju", "origin_export", "readback", "visual_metrics"],
        "source_batch_root": str(batch_root),
        "source_bundle_manifest": str(source_manifest),
        "source_bundle_manifest_sha256": _sha256_file(source_manifest),
        "source_bundle_data_sha256": str(source_bundle["bundle_data_sha256"]).lower(),
        "source_pdf_sha256": str(source_bundle.get("source_pdf", {}).get("sha256", "")).lower(),
        "figures": figures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build a fail-closed record authorizing reuse of quality-validated AA2195 data."
    )
    parser.add_argument("--batch-root", required=True, type=Path)
    parser.add_argument("--json-out", required=True, type=Path)
    args = parser.parse_args()
    result = build_reuse_record(args.batch_root)
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"status": "ok", "json_out": str(args.json_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
