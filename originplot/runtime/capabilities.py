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

_COMPILE_PRIMITIVES = (
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
)

_LIVE_BLOCKED = {
    "heatmap": "regular_grid_adapter_not_live_verified",
}


def normalize_origin_version(version: str | None) -> str | None:
    if not version:
        return None
    match = re.search(r"20\d{2}", str(version))
    return match.group(0) if match else None


def _profile_path(version: str) -> Path | None:
    preferred = [
        CAPABILITY_DIR / f"origin-{version}-v6.json",
        CAPABILITY_DIR / f"origin-{version}-v5.json",
        CAPABILITY_DIR / f"origin-{version}.json",
    ]
    return next((path for path in preferred if path.is_file()), None)


def _primitive_maturity(compatibility: str) -> dict[str, dict[str, str]]:
    maturity: dict[str, dict[str, str]] = {}
    for primitive in _COMPILE_PRIMITIVES:
        if compatibility == "blocked_unverified":
            live_status = "blocked"
            reason = "origin_version_not_supported"
        elif primitive in _LIVE_BLOCKED:
            live_status = "blocked"
            reason = _LIVE_BLOCKED[primitive]
        else:
            live_status = "requires_same_run_verification"
            reason = "v6_adapter_has_no_promoted_live_evidence"
        maturity[primitive] = {
            "compile_status": "supported",
            "live_status": live_status,
            "reason": reason,
        }
    return maturity


def resolve_origin_capabilities(version: str | None) -> dict[str, Any]:
    normalized = normalize_origin_version(version)
    compatibility = _VERSION_STATUS.get(normalized, "blocked_unverified") if normalized else "unknown"
    path = _profile_path(normalized) if normalized else None
    profile: dict[str, Any] = {}
    if path:
        try:
            profile = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            profile = {}

    maturity = _primitive_maturity(compatibility)
    live_candidates = [
        primitive
        for primitive, state in maturity.items()
        if state["live_status"] == "requires_same_run_verification"
    ]
    # v6 live evidence is deliberately empty until the new adapter is exercised in a
    # licensed Origin run and the same-run reopen/readback/export gates are recorded.
    live_evidence_primitives: list[str] = []

    return {
        "origin_version": normalized,
        "compatibility": compatibility,
        "profile_found": bool(path),
        "profile_path": str(path) if path else None,
        "profile_schema": profile.get("schema") if isinstance(profile, dict) else None,
        "compile_primitives": list(_COMPILE_PRIMITIVES),
        "live_candidate_primitives": live_candidates,
        "live_evidence_primitives": live_evidence_primitives,
        "primitive_maturity": maturity,
        # Backward-compatible field: this now means version-gated live candidates,
        # not blanket proof that a primitive has live evidence.
        "plot_primitives": live_candidates if compatibility != "blocked_unverified" else [],
        "live_authorization": "administrator_required",
        "note": "offline compile support is separate from live Origin evidence; every live run remains fail-closed behind same-run verification",
    }
