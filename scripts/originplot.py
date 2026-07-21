from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from originplot.controller import execute
from originplot.core.errors import OriginPlotError
from originplot.core.profiles import (
    EVIDENCE_LEVELS,
    PROFILE_NAMES,
    REOPEN_CHECKS,
    TEMPLATE_POLICIES,
    VISUAL_QA_LEVELS,
    SOURCE_POLICIES,
    resolve_profile,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="OriginPlot profile-aware controller (quick, standard, release)."
    )
    parser.add_argument("--figure-spec", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--figure")
    parser.add_argument("--builder")
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--profile", choices=PROFILE_NAMES, default="standard")
    parser.add_argument("--template-policy", choices=TEMPLATE_POLICIES)
    parser.add_argument("--evidence-level", choices=EVIDENCE_LEVELS)
    parser.add_argument("--reopen-check", choices=REOPEN_CHECKS)
    parser.add_argument("--visual-qa", choices=VISUAL_QA_LEVELS)
    parser.add_argument("--source-policy", choices=SOURCE_POLICIES)
    parser.add_argument("--max-template-candidates", type=int)
    parser.add_argument("--max-rebuild-attempts", type=int)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--require-live-success", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        profile = resolve_profile(
            args.profile,
            template_policy=args.template_policy,
            evidence_level=args.evidence_level,
            reopen_check=args.reopen_check,
            visual_qa=args.visual_qa,
            max_template_candidates=args.max_template_candidates,
            max_rebuild_attempts=args.max_rebuild_attempts,
        )
        result = execute(
            profile=profile,
            figure=args.figure,
            builder=args.builder,
            figure_spec_path=args.figure_spec,
            candidate_path=args.candidate,
            output_dir=args.output_dir,
            live=args.live,
            require_live_success=args.require_live_success,
            source_policy=args.source_policy,
        )
    except (OriginPlotError, OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "profile": args.profile,
            "status": "failed",
            "overall_status": "failed",
            "error_code": getattr(exc, "code", "E100_SCHEMA_INVALID"),
            "message": str(exc),
        }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "candidate_summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.require_live_success or args.live:
        if result.get("profile") == "release":
            return 0 if result.get("pass_eligible") and result.get("live_origin_verified") else 1
        return 0 if result.get("command_success") and result.get("live_origin_verified") else 1
    return 0 if result.get("status") != "failed" and result.get("overall_status") != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
