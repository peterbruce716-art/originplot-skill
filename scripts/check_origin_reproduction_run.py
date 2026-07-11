from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_manifest(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def newest_run_dirs(output_root: Path, run_prefix: str) -> list[Path]:
    if not output_root.exists():
        return []
    return sorted(
        [p for p in output_root.glob(f"{run_prefix}*") if p.is_dir()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def summarize_manifest(run_dir: Path, manifest: dict[str, Any], require_origin_qa: bool) -> tuple[int, list[str]]:
    lines: list[str] = []
    origin = manifest.get("origin_result", {})
    preflight = origin.get("origin_com_preflight", {})
    per_figure = origin.get("per_figure", {})
    exit_code = 0
    lines.append(f"latest_complete_run={run_dir}")
    lines.append(f"created_at={manifest.get('created_at')}")
    lines.append(f"origin_status={origin.get('status')}")
    lines.append(f"adapter={origin.get('adapter')}")
    lines.append(f"preflight_mode={preflight.get('mode')}")
    lines.append(f"preflight_status={preflight.get('status')}")
    if not per_figure:
        lines.append("ERROR: manifest has no per_figure results")
        return 2, lines

    for fig_id, result in per_figure.items():
        open_status = (result.get("opju_open_validation") or {}).get("status")
        strategy = result.get("origin_session_strategy")
        attach_used = result.get("authorized_visible_origin_attach_used")
        loop_status = result.get("automatic_correction_loop_status")
        targets = result.get("origin_rendered_export_targets")
        structure_status = (result.get("opju_structure_validation") or {}).get("status")
        reconstruction_status = result.get("origin_object_reconstruction_status")
        qa_items = result.get("origin_export_qa") or []
        lines.append(
            f"{fig_id}: open={open_status} structure={structure_status} reconstruction={reconstruction_status} "
            f"strategy={strategy} attach={attach_used} loop={loop_status} targets={targets}"
        )
        if open_status != "ok":
            exit_code = max(exit_code, 3)
        if structure_status != "pass":
            lines.append(f"  ERROR: {fig_id} structural round-trip contract did not pass")
            exit_code = max(exit_code, 3)
        if reconstruction_status not in {"origin_export_matches_source_after_iteration", "strict_reproduction_completed"}:
            lines.append(f"  ERROR: {fig_id} editable reconstruction status is not complete")
            exit_code = max(exit_code, 3)
        if require_origin_qa and not qa_items:
            lines.append(f"  ERROR: {fig_id} has no origin_export_qa records")
            exit_code = max(exit_code, 3)
        for qa in qa_items:
            watermark = bool(qa.get("origin_export_watermark_detected"))
            registered = qa.get("registered") or {}
            pixel = registered.get("pixel") or {}
            edge = registered.get("edge") or {}
            mae = qa.get("resized_mae_0_1", pixel.get("mae_0_1", -1))
            rmse = qa.get("resized_rmse_0_1", pixel.get("rmse_0_1", -1))
            lines.append(
                "  "
                f"{qa.get('page')} "
                f"{qa.get('export_width')}x{qa.get('export_height')} vs "
                f"{qa.get('source_width')}x{qa.get('source_height')} "
                f"MAE={float(mae):.4f} "
                f"RMSE={float(rmse):.4f} "
                f"edge_f1={float(edge.get('f1', -1)):.4f} "
                f"ssim={float(registered.get('ssim', -1)):.4f} "
                f"watermark={watermark} status={qa.get('qa_status') or qa.get('status')}"
            )
            if watermark:
                exit_code = max(exit_code, 4)
            if (qa.get("qa_status") or qa.get("status")) not in {"pass", "image_consistent"}:
                lines.append(f"  ERROR: {fig_id} QA item for {qa.get('page')} did not pass")
                exit_code = max(exit_code, 3)
    return exit_code, lines


def main() -> int:
    parser = argparse.ArgumentParser(description="Check the latest or selected Origin reproduction run manifest.")
    parser.add_argument("--manifest", type=Path, help="Specific manifest.json to inspect.")
    parser.add_argument("--output-root", type=Path, default=Path("outputs"), help="Directory containing run folders.")
    parser.add_argument("--run-prefix", default="", help="Run directory prefix. Required when --manifest is omitted.")
    parser.add_argument("--require-origin-qa", action="store_true", help="Fail when a figure has no origin_export_qa records.")
    parser.add_argument("--json-out", type=Path, help="Optional JSON output path with status and printed lines.")
    args = parser.parse_args()

    if args.manifest:
        manifest_path = args.manifest.resolve()
        if not manifest_path.exists():
            print(f"ERROR: manifest not found: {manifest_path}")
            return 2
        run_dir = manifest_path.parent
        exit_code, lines = summarize_manifest(run_dir, load_manifest(manifest_path), args.require_origin_qa)
    else:
        if not args.run_prefix:
            print("ERROR: --run-prefix is required when --manifest is omitted")
            return 2
        runs = newest_run_dirs(args.output_root.resolve(), args.run_prefix)
        if not runs:
            print(f"ERROR: no output directories found for prefix {args.run_prefix!r} under {args.output_root.resolve()}")
            return 2
        latest = runs[0]
        manifest_path = latest / "manifest.json"
        if not manifest_path.exists():
            lines = [f"latest_run={latest}", "ERROR: latest run has no manifest.json"]
            for child in sorted(latest.iterdir()):
                size = child.stat().st_size if child.is_file() else 0
                lines.append(f"  {child.name}\t{size}")
            complete = [run for run in runs if (run / "manifest.json").exists()]
            if complete:
                lines.append(f"latest_complete_run={complete[0]}")
            exit_code = 2
        else:
            exit_code, lines = summarize_manifest(latest, load_manifest(manifest_path), args.require_origin_qa)

    for line in lines:
        print(line)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps({"exit_code": exit_code, "lines": lines}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())