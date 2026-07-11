from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def build_plan(structure: dict[str, Any], visual: dict[str, Any]) -> dict[str, Any]:
    actions: list[dict[str, Any]] = []
    if structure.get("status") != "pass":
        actions.append({"priority": 1, "stage": "structure", "action": "stop_visual_tuning", "reason": "OPJU structural contract failed"})
        for failure in structure.get("failures", []):
            actions.append({"priority": 1, "stage": "structure", "action": "repair_contract_failure", "detail": failure})
        return {"status": "blocked_by_structure", "actions": actions}

    bbox = visual.get("content_bbox_delta_normalized") or {}
    if bbox and max(bbox.values()) > (visual.get("thresholds") or {}).get("max_bbox_delta", 0.025):
        actions.append({"priority": 2, "stage": "geometry", "action": "correct_page_or_layer_frame", "evidence": bbox})
    registered = visual.get("registered") or {}
    if (registered.get("edge") or {}).get("f1", 1.0) < (visual.get("thresholds") or {}).get("min_edge_f1", 0.5):
        actions.append({"priority": 2, "stage": "geometry", "action": "correct_plot_and_annotation_coordinates", "evidence": registered.get("edge")})
    for roi, failures in (visual.get("roi_failures") or {}).items():
        actions.append({"priority": 2, "stage": "geometry" if "edge_f1" in failures else "typography_color", "action": "correct_panel", "panel": roi, "failures": failures})
    if registered.get("color_histogram_l1", 0.0) > (visual.get("thresholds") or {}).get("max_color_l1", 0.3):
        actions.append({"priority": 3, "stage": "typography_color", "action": "correct_palette_fills_and_transparency", "evidence": registered.get("color_histogram_l1")})
    if registered.get("ssim", 1.0) < (visual.get("thresholds") or {}).get("min_ssim", 0.55) and (registered.get("edge") or {}).get("f1", 0.0) >= (visual.get("thresholds") or {}).get("min_edge_f1", 0.5):
        actions.append({"priority": 3, "stage": "typography_color", "action": "correct_fonts_line_widths_and_anti_aliasing", "evidence": registered.get("ssim")})
    if not actions:
        actions.append({"priority": 4, "stage": "complete", "action": "accept_round_trip_export"})
    return {"status": "complete" if actions[0]["stage"] == "complete" else "corrections_required", "actions": actions}


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a bounded, stage-ordered correction plan from structure and visual QA.")
    parser.add_argument("--structure", required=True, type=Path)
    parser.add_argument("--visual", required=True, type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = build_plan(json.loads(args.structure.read_text(encoding="utf-8-sig")), json.loads(args.visual.read_text(encoding="utf-8-sig")))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
