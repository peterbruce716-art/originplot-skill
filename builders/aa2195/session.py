from __future__ import annotations

import ctypes
import subprocess
import sys
from contextlib import contextmanager
from typing import Any, Iterator


def is_administrator_python() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def has_visible_origin_process() -> bool:
    if sys.platform != "win32":
        return False
    script = (
        "$p = Get-Process Origin* -ErrorAction SilentlyContinue | "
        "Where-Object { $_.MainWindowHandle -ne 0 }; "
        "if ($p) { 'true' } else { 'false' }"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=5,
        )
    except Exception:
        return False
    return completed.stdout.strip().lower() == "true"


@contextmanager
def origin_session(
    op: Any,
    *,
    attach_existing_authorized: bool = True,
    require_administrator: bool = True,
    allow_diagnostic_hidden: bool = False,
) -> Iterator[dict[str, str]]:
    if require_administrator and not is_administrator_python():
        raise RuntimeError(
            "E120_ENVIRONMENT_MISMATCH: Administrator Python is required before attaching to administrator Origin."
        )

    if attach_existing_authorized:
        op.attach()
        try:
            yield {
                "strategy": "administrator_attach_existing_authorized",
                "admin_required": "true",
                "origin_process_policy": "attach_to_administrator_opened_visible_origin",
                "release": "op.detach()",
            }
        finally:
            op.detach()
        return

    if not allow_diagnostic_hidden:
        raise RuntimeError(
            "E121_ATTACH_POLICY_VIOLATION: Formal OriginPlot runs must attach to an "
            "administrator-opened visible Origin process; hidden/new sessions are diagnostic-only."
        )

    op.set_show(False)
    try:
        op.new(asksave=False)
        yield {
            "strategy": "diagnostic_new_hidden_not_pass_eligible",
            "admin_required": "false",
            "origin_process_policy": "diagnostic_only_not_formal_reproduction",
            "release": "op.exit()",
        }
    finally:
        op.exit()
