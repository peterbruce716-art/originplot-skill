from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_STATUS_DIR = Path("origin_approval_deferred_runs")
DEFAULT_RETRY_BOUNDARY = "same_narrow_runner_once_next_continuation"


def timestamp() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def parse_key_value(items: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in items:
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"expected key=value, got {item!r}")
        key, value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise argparse.ArgumentTypeError(f"empty key in {item!r}")
        parsed[key] = value
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Record an automatic Origin approval-service 503 deferral without "
            "launching Origin or asking for a manual handoff."
        )
    )
    parser.add_argument("--status-dir", default=str(DEFAULT_STATUS_DIR))
    parser.add_argument("--command", required=True, help="Intended narrow command or runner invocation.")
    parser.add_argument("--target-executable", default="", help="Authorized Origin executable, if known.")
    parser.add_argument("--wrapper", default="", help="Project-local automatic runner path, if known.")
    parser.add_argument("--latest-run", default="", help="Latest known output run directory, if any.")
    parser.add_argument("--latest-status", default="", help="Latest known runner status JSON, if any.")
    parser.add_argument("--authorization-scope", default="", help="Recorded user authorization scope.")
    parser.add_argument("--reason", default="approval_service_503")
    parser.add_argument("--retry-boundary", default=DEFAULT_RETRY_BOUNDARY)
    parser.add_argument("--extra", action="append", default=[], metavar="KEY=VALUE")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    extras = parse_key_value(args.extra)

    status_dir = Path(args.status_dir)
    status_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    status_path = status_dir / f"approval_service_503_auto_deferred_{stamp}.json"

    record = {
        "status": "approval_service_503_auto_deferred",
        "created_at": timestamp(),
        "reason": args.reason,
        "execution_happened": False,
        "manual_handoff_required": False,
        "command": args.command,
        "target_executable": args.target_executable,
        "wrapper": args.wrapper,
        "latest_run": args.latest_run,
        "latest_status": args.latest_status,
        "authorization_scope": args.authorization_scope,
        "retry_boundary": args.retry_boundary,
        "extra": extras,
    }

    status_path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(status_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
