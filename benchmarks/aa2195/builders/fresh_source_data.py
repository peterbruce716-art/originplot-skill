from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


SCHEMA = "originplot.aa2195_fresh_source_bundle.v1"
FIGURES = {"fig3", "fig12", "fig14", "fig15", "fig16"}
FRESH_FORBIDDEN_LINEAGE_KEYS = {
    "data_policy",
    "inherited_from_run",
    "reextracted_figures",
    "source_data_policy",
    "source_reuse_record",
    "source_reuse_record_sha256",
    "validated_crop_reextract",
    "validated_reuse_record",
    "validated_source_data_reuse_verified",
}


def fresh_lineage_fields(payload: Any, prefix: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            name = str(key)
            path = f"{prefix}.{name}" if prefix else name
            lower = name.lower()
            if (
                lower in FRESH_FORBIDDEN_LINEAGE_KEYS
                or lower.startswith("parent_")
                or "reuse" in lower
                or lower.startswith("validated_source")
            ):
                found.append(path)
            found.extend(fresh_lineage_fields(value, path))
    elif isinstance(payload, list):
        for index, value in enumerate(payload):
            found.extend(fresh_lineage_fields(value, f"{prefix}[{index}]"))
    return found


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_fresh_figure_data(
    candidate_params: dict[str, Any],
    figure: str,
) -> dict[str, Any]:
    if figure not in FIGURES:
        raise ValueError(f"Unsupported AA2195 figure: {figure}")
    manifest_raw = str(candidate_params.get("_runtime_data_manifest", "")).strip()
    crop_raw = str(candidate_params.get("_runtime_source_crop", "")).strip()
    source_data_policy = str(
        candidate_params.get("_runtime_source_data_policy", "fresh_extract")
    ).strip()
    if source_data_policy not in {
        "fresh_extract",
        "validated_reuse",
        "validated_crop_reextract",
    }:
        raise RuntimeError("E127_SOURCE_DATA_REQUIRED: invalid source data policy")
    if not manifest_raw or not crop_raw:
        raise RuntimeError(
            "E127_SOURCE_DATA_REQUIRED: runtime source manifest and crop are mandatory"
        )
    manifest_path = Path(manifest_raw).resolve()
    crop_path = Path(crop_raw).resolve()
    if not manifest_path.is_file() or not crop_path.is_file():
        raise RuntimeError("E127_SOURCE_DATA_REQUIRED: runtime source files are missing")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA:
        raise RuntimeError("E127_SOURCE_DATA_REQUIRED: invalid source data manifest")
    if source_data_policy in {"fresh_extract", "validated_reuse"}:
        if payload.get("fresh_extraction") is not True:
            raise RuntimeError("E127_SOURCE_DATA_REQUIRED: invalid source data manifest")
        if source_data_policy == "fresh_extract":
            lineage = fresh_lineage_fields(payload)
            if lineage:
                raise RuntimeError(
                    "E127_SOURCE_DATA_REQUIRED: fresh source manifest contains reuse lineage: "
                    + ", ".join(lineage)
                )
    elif (
        payload.get("fresh_extraction") is not False
        or payload.get("validated_crop_reextract") is not True
        or payload.get("source_data_policy") != "validated_crop_reextract"
        or payload.get("reextracted_figures") != ["fig14"]
    ):
        raise RuntimeError("E127_SOURCE_DATA_REQUIRED: invalid crop re-extraction manifest")
    record = payload.get("figures", {}).get(figure)
    if not isinstance(record, dict) or not isinstance(record.get("data"), dict):
        raise RuntimeError(f"E127_SOURCE_DATA_REQUIRED: {figure} data is missing")
    actual_crop_sha256 = _sha256_file(crop_path)
    expected_crop_sha256 = str(record.get("source_crop_sha256", "")).lower()
    if actual_crop_sha256 != expected_crop_sha256:
        raise RuntimeError(f"E127_SOURCE_DATA_REQUIRED: {figure} crop hash mismatch")
    return {
        "source_data_policy": source_data_policy,
        "manifest_path": str(manifest_path),
        "source_crop": str(crop_path),
        "source_crop_sha256": actual_crop_sha256,
        "source_pdf_sha256": str(payload.get("source_pdf", {}).get("sha256", "")),
        "bundle_data_sha256": str(payload.get("bundle_data_sha256", "")),
        "data_sha256": str(record.get("data_sha256", "")),
        "data": record["data"],
    }
