from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from originplot.controller import execute
from originplot.core.errors import OriginPlotError
from originplot.core.profiles import PROFILE_NAMES, resolve_profile
from originplot.runtime.doctor import doctor
from originplot.semantic import inspect_table
from originplot.semantic.plan import build_figurespec
from originplot.spec import load_figure_spec
from originplot.verification import required_artifacts


def _print(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _mapping(args: argparse.Namespace) -> dict[str, str]:
    return {
        key: value
        for key, value in {
            "x": getattr(args, "x", None),
            "y": getattr(args, "y", None),
            "x_error": getattr(args, "x_error", None),
            "y_error": getattr(args, "y_error", None),
            "category": getattr(args, "category", None),
            "z": getattr(args, "z", None),
        }.items()
        if value
    }


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json_object(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.resolve().read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise OriginPlotError("E340_STYLE_SPEC_INVALID", f"style JSON must contain an object: {path}")
    return payload


def _add_mapping_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--x")
    parser.add_argument("--y")
    parser.add_argument("--x-error")
    parser.add_argument("--y-error")
    parser.add_argument("--category")
    parser.add_argument("--z")


def _add_style_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--reference-style-json", type=Path, help="confirmed visual-only suggestions extracted from a reference figure")
    parser.add_argument("--style-json", type=Path, help="explicit user visual choices; highest precedence")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="originplot", description="OriginPlot v6 editable scientific plotting workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor_parser = sub.add_parser("doctor", help="read-only environment and Origin capability diagnostics")
    doctor_parser.add_argument("--origin-version")

    inspect_parser = sub.add_parser("inspect", help="inspect a scientific table without modifying it")
    inspect_parser.add_argument("data", type=Path)
    inspect_parser.add_argument("--sheet")

    plan_parser = sub.add_parser("plan", help="freeze semantic choices into FigureSpec v6")
    plan_parser.add_argument("data", type=Path)
    plan_parser.add_argument("--sheet")
    plan_parser.add_argument("--plot-type")
    plan_parser.add_argument("--profile", choices=PROFILE_NAMES, default="standard")
    plan_parser.add_argument("--output", type=Path)
    _add_mapping_flags(plan_parser)
    _add_style_flags(plan_parser)

    render_parser = sub.add_parser("render", help="compile and execute an existing FigureSpec")
    render_parser.add_argument("figure_spec", type=Path)
    render_parser.add_argument("--profile", choices=PROFILE_NAMES)
    render_parser.add_argument("--output-dir", type=Path)
    render_parser.add_argument("--dry-run", action="store_true")
    render_parser.add_argument("--require-live-success", action="store_true")

    draw_parser = sub.add_parser("draw", help="inspect, plan and render a table")
    draw_parser.add_argument("data", type=Path)
    draw_parser.add_argument("--sheet")
    draw_parser.add_argument("--plot-type")
    draw_parser.add_argument("--profile", choices=PROFILE_NAMES, default="standard")
    draw_parser.add_argument("--output-dir", type=Path)
    draw_parser.add_argument("--dry-run", action="store_true")
    _add_mapping_flags(draw_parser)
    _add_style_flags(draw_parser)

    verify_parser = sub.add_parser("verify", help="check canonical v6 artifacts")
    verify_parser.add_argument("output_dir", type=Path)
    return parser


def _default_output(data: Path) -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return data.resolve().parent / f"{data.stem}_OriginPlot_{stamp}"


def _verify_output(output_dir: Path) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    artifacts = required_artifacts(output_dir)
    states = {name: path.is_file() and path.stat().st_size > 0 for name, path in artifacts.items()}
    verification = {}
    if artifacts["verification.json"].is_file():
        try:
            verification = json.loads(artifacts["verification.json"].read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            verification = {}
    return {
        "output_dir": str(output_dir),
        "artifacts": states,
        "all_required_present": all(states.values()),
        "live_origin_verified": bool(verification.get("live_origin_verified")),
        "command_success": bool(verification.get("command_success")),
    }


def _planned_style_args(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "reference_style": _read_json_object(getattr(args, "reference_style_json", None)),
        "user_style": _read_json_object(getattr(args, "style_json", None)),
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "doctor":
            result = doctor(args.origin_version)
            _print(result)
            return 0
        if args.command == "inspect":
            result = inspect_table(args.data, args.sheet)
            _print(result)
            return 0
        if args.command == "plan":
            result = build_figurespec(
                args.data,
                plot_type=args.plot_type,
                sheet=args.sheet,
                mapping=_mapping(args),
                profile=args.profile,
                **_planned_style_args(args),
            )
            output = (args.output or args.data.with_suffix(".figure.json")).resolve()
            _write(output, result)
            _print({"status": "planned", "figure_spec": str(output), "plot_type": result["figure"]["type"]})
            return 0
        if args.command == "render":
            spec = load_figure_spec(args.figure_spec)
            profile = resolve_profile(args.profile or spec.profile)
            output = (args.output_dir or args.figure_spec.resolve().parent / f"{spec.figure_id}_OriginPlot").resolve()
            result = execute(
                profile=profile,
                figure_spec_path=args.figure_spec,
                output_dir=output,
                live=not args.dry_run,
                require_live_success=args.require_live_success,
            )
            _print(result)
            return 0 if result.get("command_success") or result.get("status") == "planned_not_executed" else 1
        if args.command == "draw":
            output = (args.output_dir or _default_output(args.data)).resolve()
            output.mkdir(parents=True, exist_ok=True)
            figure_spec = build_figurespec(
                args.data,
                plot_type=args.plot_type,
                sheet=args.sheet,
                mapping=_mapping(args),
                profile=args.profile,
                **_planned_style_args(args),
            )
            spec_path = output / "figure_spec.json"
            _write(spec_path, figure_spec)
            result = execute(
                profile=resolve_profile(args.profile),
                figure_spec_path=spec_path,
                output_dir=output,
                live=not args.dry_run,
                require_live_success=not args.dry_run,
            )
            _print(result)
            return 0 if result.get("command_success") or result.get("status") == "planned_not_executed" else 1
        if args.command == "verify":
            result = _verify_output(args.output_dir)
            _print(result)
            return 0 if result["all_required_present"] and result["command_success"] else 1
    except (OriginPlotError, OSError, ValueError, json.JSONDecodeError) as exc:
        _print({"status": "failed", "error_code": getattr(exc, "code", "E100_V6_COMMAND_FAILED"), "message": str(exc)})
        return 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
