#!/usr/bin/env python3
"""Fail before OriginPlot live artifacts are created unless Python is elevated."""

from __future__ import annotations

import argparse
import ctypes
import getpass
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path


def is_admin() -> bool:
    if sys.platform != "win32":
        return False
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def demo_restart_directive(error_code: str, *, python_is_admin: bool) -> dict[str, object] | None:
    if error_code != "E122_ORIGIN_DEMO_EXPORT_BLOCKED":
        return None
    return {
        "schema": "originplot.admin_restart_directive.v1",
        "current_run_invalidated": True,
        "restart_required": True,
        "restart_from": "administrator_preflight",
        "required_privilege": "administrator",
        "new_run_id_required": True,
        "clean_output_root_required": True,
        "reuse_current_run_artifacts": False,
        "max_full_elevated_restarts": 1,
        "python_was_admin": bool(python_is_admin),
        "repeated_watermark_action": "stop_and_resolve_origin_license_or_environment",
    }


def build_record(admin_override: bool | None = None) -> dict[str, object]:
    elevated = is_admin() if admin_override is None else bool(admin_override)
    return {
        "schema": "originplot.admin_preflight.v1",
        "status": "ok" if elevated else "failed",
        "error_code": None if elevated else "E120_ENVIRONMENT_MISMATCH",
        "is_admin": elevated,
        "required_privilege": "administrator",
        "user": getpass.getuser(),
        "process_id": os.getpid(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "workflow_scope": "template_retrieval_to_final_cleanup",
        "action": "continue" if elevated else "restart_entire_workflow_in_elevated_powershell",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, required=True)
    args = parser.parse_args()
    record = build_record()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(
        json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(record, ensure_ascii=False))
    return 0 if record["is_admin"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
