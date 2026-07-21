from __future__ import annotations

import ctypes
import json
import subprocess
import sys
from contextlib import contextmanager
from typing import Any, Iterator


def is_administrator() -> bool:
    try:
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def process_inventory() -> list[dict[str, Any]]:
    if sys.platform != "win32":
        return []
    script = ("$rows = Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'Origin*.exe' } | "
              "ForEach-Object { $p=Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue; "
              "[pscustomobject]@{pid=[int]$_.ProcessId;visible=[bool]($p -and $p.MainWindowHandle -ne 0);"
              "command_line=[string]$_.CommandLine} }; ConvertTo-Json -Compress -InputObject @($rows)")
    try:
        completed = subprocess.run([r"C:\Program Files\PowerShell\7\pwsh.exe", "-NoProfile", "-Command", script],
                                   text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8, check=False)
        payload = json.loads(completed.stdout or "[]")
    except Exception:
        return []
    return payload if isinstance(payload, list) else ([payload] if isinstance(payload, dict) else [])


@contextmanager
def attached_origin(op: Any) -> Iterator[dict[str, Any]]:
    if not is_administrator():
        raise RuntimeError("E120_ENVIRONMENT_MISMATCH: administrator Python is required for Origin live execution")
    before_records = process_inventory()
    before = [item for item in before_records if item.get("visible") and "-embedding" not in str(item.get("command_line", "")).lower()]
    if len(before) != 1:
        raise RuntimeError("E123_ORIGIN_SESSION_IDENTITY_DRIFT: exactly one visible non-Embedding Origin process is required")
    op.attach()
    try:
        after = process_inventory()
        match = next((item for item in after if int(item.get("pid", -1)) == int(before[0]["pid"])), None)
        prior_pids = {int(item["pid"]) for item in before_records if item.get("pid")}
        new_embedding = [int(item["pid"]) for item in after if item.get("pid") and int(item["pid"]) not in prior_pids and "-embedding" in str(item.get("command_line", "")).lower()]
        if not match or not match.get("visible") or new_embedding:
            raise RuntimeError("E123_ORIGIN_SESSION_IDENTITY_DRIFT: attached Origin identity changed")
        yield {"strategy": "administrator_attach_existing_authorized", "origin_pid": int(before[0]["pid"]), "admin_required": True, "new_embedding_pids": []}
    finally:
        op.detach()
