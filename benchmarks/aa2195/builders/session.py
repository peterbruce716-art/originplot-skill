from __future__ import annotations

import ctypes
import json
import subprocess
import sys
from contextlib import contextmanager
from pathlib import Path
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


def origin_process_inventory() -> list[dict[str, Any]]:
    if sys.platform != "win32":
        return []
    script = (
        "$rows = Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -like 'Origin*.exe' } | ForEach-Object { "
        "$p = Get-Process -Id $_.ProcessId -ErrorAction SilentlyContinue; "
        "[pscustomobject]@{ pid=[int]$_.ProcessId; visible=[bool]($p -and $p.MainWindowHandle -ne 0); "
        "command_line=[string]$_.CommandLine; executable_path=[string]$_.ExecutablePath } }; "
        "ConvertTo-Json -Compress -InputObject @($rows)"
    )
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=8,
        )
        payload = json.loads(completed.stdout or "[]")
    except Exception:
        return []
    records = payload if isinstance(payload, list) else [payload]
    return [record for record in records if isinstance(record, dict) and record.get("pid")]


def _is_embedding(record: dict[str, Any]) -> bool:
    return "-embedding" in str(record.get("command_line", "")).lower()


def _select_formal_origin_pid(
    records: list[dict[str, Any]], expected_origin_pid: int | None = None
) -> int:
    candidates = [
        record
        for record in records
        if bool(record.get("visible")) and not _is_embedding(record)
    ]
    if expected_origin_pid is not None:
        candidates = [record for record in candidates if int(record["pid"]) == int(expected_origin_pid)]
    if len(candidates) != 1:
        raise RuntimeError(
            "E123_ORIGIN_SESSION_IDENTITY_DRIFT: formal attach requires exactly one "
            "visible non-Embedding Origin process with stable identity"
        )
    return int(candidates[0]["pid"])


def validate_attached_origin_identity(
    before: list[dict[str, Any]],
    after: list[dict[str, Any]],
    *,
    expected_origin_pid: int | None = None,
) -> dict[str, Any]:
    origin_pid = _select_formal_origin_pid(before, expected_origin_pid)
    after_by_pid = {int(record["pid"]): record for record in after if record.get("pid")}
    attached = after_by_pid.get(origin_pid)
    new_embedding_pids = sorted(
        int(record["pid"])
        for record in after
        if record.get("pid")
        and int(record["pid"]) not in {int(item["pid"]) for item in before if item.get("pid")}
        and _is_embedding(record)
    )
    if attached is None or not bool(attached.get("visible")) or _is_embedding(attached) or new_embedding_pids:
        raise RuntimeError(
            "E123_ORIGIN_SESSION_IDENTITY_DRIFT: op.attach() did not preserve the "
            "administrator-started visible Origin process"
        )
    return {
        "origin_pid": origin_pid,
        "origin_window_visible": True,
        "origin_embedding": False,
        "new_embedding_pids": [],
    }


def assert_no_demo_watermark(path: str | Path, max_cyan_ratio: float = 0.0005) -> dict[str, Any]:
    import numpy as np
    from PIL import Image

    image = np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    cyan_mask = (
        (image[:, :, 0] < 100)
        & (image[:, :, 1] > 180)
        & (image[:, :, 2] > 200)
        & (np.abs(image[:, :, 1].astype(np.int16) - image[:, :, 2].astype(np.int16)) < 70)
    )
    ratio = float(np.mean(cyan_mask))
    if ratio > float(max_cyan_ratio):
        raise RuntimeError(
            f"E122_ORIGIN_DEMO_EXPORT_BLOCKED: pre-save export contains demo cyan markings "
            f"(ratio={ratio:.8f}, max={float(max_cyan_ratio):.8f})"
        )
    return {"status": "pass", "demo_cyan_ratio": ratio, "max_cyan_ratio": float(max_cyan_ratio)}


@contextmanager
def origin_session(
    op: Any,
    *,
    attach_existing_authorized: bool = True,
    require_administrator: bool = True,
    allow_diagnostic_hidden: bool = False,
    expected_origin_pid: int | None = None,
) -> Iterator[dict[str, Any]]:
    if require_administrator and not is_administrator_python():
        raise RuntimeError(
            "E120_ENVIRONMENT_MISMATCH: Administrator Python is required before attaching to administrator Origin."
        )

    if attach_existing_authorized:
        before = origin_process_inventory()
        _select_formal_origin_pid(before, expected_origin_pid)
        op.attach()
        try:
            identity = validate_attached_origin_identity(
                before,
                origin_process_inventory(),
                expected_origin_pid=expected_origin_pid,
            )
            yield {
                "strategy": "administrator_attach_existing_authorized",
                "admin_required": "true",
                "origin_process_policy": "attach_to_administrator_opened_visible_origin",
                "release": "op.detach()",
                **identity,
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
