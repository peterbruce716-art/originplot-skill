from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run_runtime(command: list[str], timeout_seconds: int) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=max(1, int(timeout_seconds)),
        )
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        return subprocess.CompletedProcess(
            command,
            124,
            stdout,
            str(stderr) + f"\norigin_inspect_worker runtime timeout after {timeout_seconds} seconds.\n",
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run only OriginPlot v5 inspect-worker operations in a separate process.")
    parser.add_argument("--operation-plan", required=True, type=Path)
    parser.add_argument("--capabilities", required=True, type=Path)
    parser.add_argument("--manifest-out", required=True, type=Path)
    parser.add_argument("--adapter-modules", type=Path)
    parser.add_argument("--adapter-configs", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--artifact-manifest", type=Path)
    parser.add_argument("--workspace", type=Path)
    parser.add_argument("--run-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--runtime-timeout-seconds", type=int, default=150)
    args = parser.parse_args()
    command = [
        sys.executable,
        str(Path(__file__).resolve().parent / "originplot_runtime_v5.py"),
        "run",
        "--operation-plan",
        str(args.operation_plan),
        "--capabilities",
        str(args.capabilities),
        "--manifest-out",
        str(args.manifest_out),
        "--workers",
        "inspect",
    ]
    if args.adapter_modules:
        command.extend(["--adapter-modules", str(args.adapter_modules)])
    if args.adapter_configs:
        command.extend(["--adapter-configs", str(args.adapter_configs)])
    if args.run_dir:
        command.extend(["--run-dir", str(args.run_dir)])
    if args.artifact_manifest:
        command.extend(["--artifact-manifest", str(args.artifact_manifest)])
    if args.workspace:
        command.extend(["--workspace", str(args.workspace)])
    if args.run_id:
        command.extend(["--run-id", str(args.run_id)])
    if args.dry_run:
        command.append("--dry-run")
    result = run_runtime(command, args.runtime_timeout_seconds)
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
