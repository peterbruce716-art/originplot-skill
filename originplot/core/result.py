from __future__ import annotations

from typing import Any

from .profiles import ProfileConfig


GATE_NAMES = (
    "opju_saved",
    "opju_reopened",
    "editable_plot_present",
    "worksheet_binding",
    "origin_export_nonblank",
    "demo_watermark_absent",
    "visual_comparison",
    "provenance",
    "hash_chain",
    "release_evidence",
)


def gate_plan(profile: ProfileConfig) -> dict[str, str]:
    gates = {name: "required" for name in GATE_NAMES[:6]}
    gates["visual_comparison"] = (
        "not_required" if profile.visual_qa == "off" else "required"
    )
    for name in ("provenance", "hash_chain", "release_evidence"):
        gates[name] = "required" if profile.name == "release" else "not_required"
    return gates


def planned_result(profile: ProfileConfig, *, mode: str, warnings: list[str] | None = None) -> dict[str, Any]:
    return {
        "profile": profile.name,
        "mode": mode,
        "command_success": True,
        "structure_pass": False,
        "visual_pass": False,
        "live_origin_verified": False,
        "pass_eligible": False,
        "overall_status": "planned_not_executed",
        "gates": gate_plan(profile),
        "warnings": list(warnings or []),
    }


def normalize_live_result(profile: ProfileConfig, result: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(result)
    normalized["profile"] = profile.name
    normalized.setdefault("gates", gate_plan(profile))
    live = bool(normalized.get("live_origin_verified"))
    structure = bool(normalized.get("structure_pass"))
    visual = bool(normalized.get("visual_pass"))
    hard_gate_names = set(GATE_NAMES[:6]) | {"provenance", "hash_chain", "release_evidence"}
    required_gates = [name for name, status in normalized["gates"].items() if status == "required" and name in hard_gate_names]
    failed_gates = [name for name in required_gates if normalized.get("gate_results", {}).get(name) != "pass"]
    hard_pass = bool(normalized.get("command_success")) and live and structure and not failed_gates
    normalized["failed_gates"] = failed_gates
    if profile.name == "quick":
        normalized["pass_eligible"] = False
        normalized["overall_status"] = "completed" if hard_pass else "incomplete"
    elif profile.name == "standard":
        normalized["pass_eligible"] = False
        normalized["overall_status"] = (
            "live_visual_pass" if hard_pass and visual
            else "live_structure_pass" if hard_pass
            else "incomplete"
        )
    return normalized
