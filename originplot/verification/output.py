from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from originplot.core.errors import OriginPlotError
from originplot.spec import FIGURE_SPEC_SCHEMA
from originplot.spec.io import (
    _normalize_figure,
    _normalize_layout,
    _normalize_style,
    _normalize_verification,
    file_sha256,
)

from .artifacts import no_demo_watermark, required_artifacts

LIVE_GATES = (
    "opju_saved",
    "opju_reopened",
    "editable_plot_present",
    "worksheet_binding",
    "origin_export_nonblank",
    "origin_exports_complete",
    "demo_watermark_absent",
)


def artifact_hashes(output_dir: Path) -> dict[str, str]:
    """Bind worker evidence to final files; this is integrity, not a signature."""
    return {
        name: file_sha256(path)
        for name, path in required_artifacts(output_dir).items()
        if name != "verification.json"
    }


def _object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return value


def _export_valid(path: Path) -> bool:
    if path.suffix == ".pdf":
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError

        try:
            with path.open("rb") as handle:
                reader = PdfReader(handle, strict=True)
                if reader.is_encrypted or not reader.pages:
                    return False
                for page in reader.pages:
                    if page.mediabox.width <= 0 or page.mediabox.height <= 0:
                        return False
                    contents = page.get_contents()
                    if contents is None or not contents.get_data().strip():
                        return False
                return True
        except (PdfReadError, TypeError, IndexError):
            return False
    from PIL import Image, ImageStat

    with Image.open(path) as original:
        if original.format != {".png": "PNG", ".tif": "TIFF"}[path.suffix]:
            return False
        with original.convert("RGB") as image:
            return min(image.size) > 10 and max(ImageStat.Stat(image).var) > 0


def _archived_spec_valid(payload: dict[str, Any]) -> bool:
    if payload.get("schema") != FIGURE_SPEC_SCHEMA:
        return False
    source = payload.get("source")
    if (
        not isinstance(source, dict)
        or not isinstance(source.get("file"), str)
        or not source["file"].strip()
    ):
        return False
    if not isinstance(source.get("hash"), str) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", source["hash"]
    ):
        return False
    figure = _normalize_figure(payload.get("figure"))
    kind = figure["type"]
    _normalize_layout(payload.get("layout"), kind)
    _normalize_style(payload.get("style"))
    _normalize_verification(payload.get("verification"))
    data = payload.get("data")
    if not isinstance(data, dict):
        return False
    if kind == "contour":
        mappings, required = [data.get("matrix")], ("x", "y", "z")
    elif kind in {
        "line",
        "scatter",
        "line_scatter",
        "errorbar",
        "bar",
        "grouped_bar",
        "stacked_bar",
    }:
        mappings = data.get("series")
        required = (
            ("category", "y") if "bar" in kind and kind != "errorbar" else ("x", "y")
        )
    else:
        return False  # compile-only primitives cannot carry live evidence
    if not isinstance(mappings, list) or not mappings:
        return False
    for mapping in mappings:
        if not isinstance(mapping, dict) or any(
            not isinstance(mapping.get(key), str) or not mapping[key].strip()
            for key in required
        ):
            return False
        if kind == "errorbar" and not (
            mapping.get("x_error") or mapping.get("y_error")
        ):
            return False
    return True


def verify_output(output_dir: Path) -> dict[str, Any]:
    """Recheck files and recorded lifecycle evidence without launching Origin."""
    output_dir = output_dir.resolve()
    paths = required_artifacts(output_dir)
    states: dict[str, bool] = {}
    failures: list[str] = []
    for name, path in paths.items():
        try:
            states[name] = path.is_file() and path.stat().st_size > 0
        except OSError:
            states[name] = False
        if not states[name]:
            failures.append(f"missing_or_empty:{name}")
    record: dict[str, Any] = {}
    try:
        record = _object(paths["verification.json"])
    except (OSError, ValueError):
        failures.append("invalid_verification_record")
    if (
        record.get("schema") != "originplot.origin_worker_result.v2"
        or record.get("mode") != "live"
    ):
        failures.append("live_worker_record_required")
    if (
        record.get("command_success") is not True
        or record.get("live_origin_verified") is not True
    ):
        failures.append("live_success_required")
    gates = record.get("gate_results")
    if not isinstance(gates, dict) or any(
        gates.get(key) != "pass" for key in LIVE_GATES
    ):
        failures.append("live_gates_incomplete")
    expected = record.get("artifact_sha256")
    for name, path in paths.items():
        if name == "verification.json":
            continue
        try:
            if not isinstance(expected, dict) or expected.get(name) != file_sha256(
                path
            ):
                failures.append(f"artifact_hash_mismatch:{name}")
        except OSError:
            failures.append(f"artifact_unreadable:{name}")
    for name in ("figure.png", "figure.pdf", "figure.tif"):
        try:
            if not _export_valid(paths[name]):
                failures.append(f"invalid_export:{name}")
        except (OSError, ValueError, KeyError):
            failures.append(f"invalid_export:{name}")
    if not no_demo_watermark(paths["figure.png"]):
        failures.append("demo_watermark_check_failed")
    try:
        if not _archived_spec_valid(_object(paths["figure_spec.json"])):
            failures.append("invalid_figure_spec")
    except (OSError, ValueError, OriginPlotError):
        failures.append("invalid_figure_spec")
    success = not failures
    return {
        "output_dir": str(output_dir),
        "artifacts": states,
        "all_required_present": all(states.values()),
        "command_success": success,
        "live_origin_verified": success,
        "verification_scope": "offline_artifact_integrity_and_recorded_live_evidence",
        "origin_reopened_now": False,
        "failures": failures,
    }
