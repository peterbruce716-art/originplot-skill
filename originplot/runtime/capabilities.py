from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CAPABILITY_DIR = ROOT / "capabilities"

_VERSION_STATUS = {
    "2022": "verified_baseline",
    "2024": "compatible_unverified",
    "2026": "experimental",
}


def normalize_origin_version(version: str | None) -> str | None:
    if not version:
        return None
    match = re.search(r"20\d{2}", str(version))
    return match.group(0) if match else None


def _profile_path(version: str) -> Path | None:
    preferred = [
        CAPABILITY_DIR / f"origin-{version}-v5.json",
        CAPABILITY_DIR / f"origin-{version}.json",
    ]
    return next((path for path in preferred if path.is_file()), None)


def resolve_origin_capabilities(version: str | None) -> dict[str, Any]:
    normalized = normalize_origin_version(version)
    if not normalized:
        return {
            "origin_version": None,
            "compatibility": "unknown",
            "profile_found": False,
            "plot_primitives": [],
            "live_authorization": "administrator_required",
        }
    path = _profile_path(normalized)
    profile: dict[str, Any] = {}
    if path:
        try:
            profile = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            profile = {}
    compatibility = _VERSION_STATUS.get(normalized, "blocked_unverified")
    # Capability files describe evidence, not blanket permission. The adapter still
    # fails closed at live execution time if a concrete Origin operation is unavailable.
    primitives = [
        "line",
        "scatter",
        "line_scatter",
        "errorbar",
        "bar",
        "grouped_bar",
        "stacked_bar",
        "heatmap",
        "contour",
        "multi_panel",
    ] if compatibility != "blocked_unverified" else []
    return {
        "origin_version": normalized,
        "compatibility": compatibility,
        "profile_found": bool(path),
        "profile_path": str(path) if path else None,
        "profile_schema": profile.get("schema") if isinstance(profile, dict) else None,
        "plot_primitives": primitives,
        "live_authorization": "administrator_required",
        "note": "capability profile does not waive same-run Origin smoke/readback verification",
    }
