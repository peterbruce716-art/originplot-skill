from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any


_SUPPORTED_ORIGIN_EXECUTABLE = re.compile(r"Origin(?:64|_64|_32)?\.exe", re.IGNORECASE)


def parse_wmic_embedding_pids(output: str) -> list[int]:
    pids: list[int] = []
    for line in output.splitlines():
        if not _SUPPORTED_ORIGIN_EXECUTABLE.search(line):
            continue
        if not re.search(r"-Embedding\b", line, re.IGNORECASE):
            continue
        parts = line.rstrip().rsplit(maxsplit=1)
        if parts and parts[-1].isdigit():
            pids.append(int(parts[-1]))
    return sorted(set(pids))


def _powershell_executable() -> str:
    standard = Path(r"C:\Program Files\PowerShell\7\pwsh.exe")
    if standard.is_file():
        return str(standard)
    return shutil.which("pwsh") or shutil.which("powershell") or "powershell"


def write_json(path: Path | None, payload: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def stop_embedding_once() -> dict[str, Any]:
    ps_script = (
        "$ids = @(); "
        "try { "
        "$targets = Get-CimInstance Win32_Process | "
        "Where-Object { $_.Name -like 'Origin*.exe' -and $_.CommandLine -like '*-Embedding*' }; "
        "$ids += @($targets | Select-Object -ExpandProperty ProcessId); "
        "} catch {} "
        "$ids = @($ids | Sort-Object -Unique); "
        "foreach ($id in $ids) { try { Stop-Process -Id $id -Force -ErrorAction Stop } catch {} }; "
        "$ids -join ','"
    )
    ps = subprocess.run(
        [_powershell_executable(), "-NoProfile", "-Command", ps_script],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10,
    )
    ids = [int(item) for item in ps.stdout.strip().split(",") if item.strip().isdigit()]
    method = "powershell_cim_commandline"
    wmic_stderr = ""
    if not ids:
        wmic_exe = Path(r"C:\Windows\System32\wbem\WMIC.exe")
        wmic_command = str(wmic_exe) if wmic_exe.exists() else "wmic"
        wmic = subprocess.run(
            [wmic_command, "process", "get", "ProcessId,CommandLine"],
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=10,
        )
        wmic_stderr = wmic.stderr
        ids.extend(parse_wmic_embedding_pids(wmic.stdout))
        if ids:
            for pid in sorted(set(ids)):
                subprocess.run(
                    ["taskkill", "/PID", str(pid), "/F"],
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    check=False,
                    timeout=10,
                )
            method = "wmic_commandline"
    return {
        "stopped_embedding_pids": sorted(set(ids)),
        "returncode": ps.returncode,
        "method": method,
        "stderr_tail": (ps.stderr + wmic_stderr)[-1000:],
    }


def cleanup_loop(
    duration_seconds: float, interval_seconds: float, json_out: Path | None
) -> dict[str, Any]:
    deadline = time.monotonic() + max(0.0, duration_seconds)
    attempts: list[dict[str, Any]] = []
    while True:
        try:
            attempts.append(
                {
                    "at": datetime.now().isoformat(timespec="seconds"),
                    **stop_embedding_once(),
                }
            )
        except Exception as exc:
            attempts.append(
                {
                    "at": datetime.now().isoformat(timespec="seconds"),
                    "error": f"{exc.__class__.__name__}: {exc}",
                }
            )
        payload = {
            "schema": "originplot.embedding_cleanup.v1",
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "duration_seconds": duration_seconds,
            "interval_seconds": interval_seconds,
            "attempts": attempts,
            "stopped_embedding_pids": sorted(
                {
                    pid
                    for attempt in attempts
                    for pid in attempt.get("stopped_embedding_pids", [])
                }
            ),
        }
        write_json(json_out, payload)
        if time.monotonic() >= deadline:
            return payload
        time.sleep(max(0.1, interval_seconds))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Stop delayed Origin64.exe -Embedding processes after attach timeouts."
    )
    parser.add_argument("--duration-seconds", type=float, default=45.0)
    parser.add_argument("--interval-seconds", type=float, default=2.0)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    result = cleanup_loop(args.duration_seconds, args.interval_seconds, args.json_out)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
