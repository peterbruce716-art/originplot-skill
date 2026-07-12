from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


RUN_MANIFEST_SCHEMA = "originplot.run_manifest.v5"
WORKER_TIMEOUT_ERROR_CODES = {
    "preflight": "E130_DOCTOR_FAILED",
    "build": "E300_ORIGIN_ATTACH_FAILED",
    "inspect": "E310_REOPEN_FAILED",
    "qa": "E420_VISUAL_MISMATCH",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def tail_lines(text: str, count: int = 20) -> str:
    return "\n".join(text.splitlines()[-count:])


def run_command(command: list[str], cwd: Path, *, log_dir: Path, worker: str, timeout_seconds: int) -> dict[str, Any]:
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=max(1, int(timeout_seconds)),
        )
        stdout = completed.stdout
        stderr = completed.stderr
        returncode = completed.returncode
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        stdout = exc.stdout or ""
        stderr = exc.stderr or ""
        returncode = 124
        if isinstance(stdout, bytes):
            stdout = stdout.decode("utf-8", errors="replace")
        if isinstance(stderr, bytes):
            stderr = stderr.decode("utf-8", errors="replace")
        stderr = (
            str(stderr)
            + f"\nWorker {worker!r} exceeded timeout_seconds={max(1, int(timeout_seconds))}; "
            "treating the run as fail-closed.\n"
        )
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_log = log_dir / f"{worker}.stdout.log"
    stderr_log = log_dir / f"{worker}.stderr.log"
    stdout_log.write_text(stdout, encoding="utf-8")
    stderr_log.write_text(stderr, encoding="utf-8")
    result = {
        "command": command,
        "returncode": returncode,
        "stdout_log": str(stdout_log),
        "stderr_log": str(stderr_log),
        "stdout_sha256": sha256_text(str(stdout)),
        "stderr_sha256": sha256_text(str(stderr)),
        "stderr_tail": tail_lines(str(stderr)),
    }
    if timed_out:
        result["timed_out"] = True
        result["timeout_seconds"] = max(1, int(timeout_seconds))
        result["error_code"] = WORKER_TIMEOUT_ERROR_CODES.get(worker, "E220_BUILD_FAILED")
    return result


def load_manifest(path: Path) -> dict[str, Any]:
    return read_json(path) if path.exists() else {"schema": RUN_MANIFEST_SCHEMA, "overall_status": "failed", "error": "missing manifest"}


def status_from_workers(preflight: dict[str, Any], build: dict[str, Any], inspect: dict[str, Any], qa: dict[str, Any], *, dry_run: bool) -> dict[str, str]:
    if dry_run:
        return {
            "preflight_status": preflight.get("preflight_status", "not_run"),
            "build_status": "not_run",
            "round_trip_status": "not_run",
            "structure_status": "not_run",
            "serialization_status": "not_run",
            "visual_status": "not_run",
            "overall_status": "incomplete",
        }
    statuses = {
        "preflight_status": preflight.get("preflight_status", "failed"),
        "build_status": build.get("build_status", "failed"),
        "round_trip_status": inspect.get("round_trip_status", "failed"),
        "structure_status": inspect.get("structure_status", "failed"),
        "serialization_status": qa.get("serialization_status", "failed"),
        "visual_status": qa.get("visual_status", "failed"),
    }
    statuses["overall_status"] = "pass" if all(value == "pass" for value in statuses.values()) else "failed"
    return statuses


def main() -> int:
    parser = argparse.ArgumentParser(description="OriginPlot v5.2 verified live runtime orchestrator.")
    parser.add_argument("--operation-plan", required=True, type=Path)
    parser.add_argument("--capabilities", required=True, type=Path)
    parser.add_argument("--adapter-modules", type=Path)
    parser.add_argument("--adapter-configs", type=Path)
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--artifact-manifest", type=Path)
    parser.add_argument("--manifest-out", required=True, type=Path)
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--run-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--worker-timeout-seconds", type=int, default=180)
    args = parser.parse_args()

    scripts = Path(__file__).resolve().parent
    run_dir = args.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    log_dir = run_dir / "logs"
    artifact_manifest = (args.artifact_manifest or run_dir / "run_artifacts.json").resolve()
    run_id = args.run_id or run_dir.name
    operation_plan = args.operation_plan.resolve()
    capabilities = args.capabilities.resolve()
    adapter_modules = args.adapter_modules.resolve() if args.adapter_modules else None
    adapter_configs = args.adapter_configs.resolve() if args.adapter_configs else None
    workspace = args.workspace.resolve()
    common = [
        "--operation-plan",
        str(operation_plan),
        "--capabilities",
        str(capabilities),
        "--run-dir",
        str(run_dir),
        "--artifact-manifest",
        str(artifact_manifest),
        "--workspace",
        str(workspace),
        "--run-id",
        run_id,
    ]
    if adapter_modules:
        common.extend(["--adapter-modules", str(adapter_modules)])
    if adapter_configs:
        common.extend(["--adapter-configs", str(adapter_configs)])
    if args.dry_run:
        common.append("--dry-run")
    runtime_timeout = str(max(5, int(args.worker_timeout_seconds) - 10))

    preflight_out = run_dir / "preflight_manifest.json"
    preflight_cmd = [
        sys.executable,
        str(scripts / "originplot_runtime_v5.py"),
        "preflight",
        "--operation-plan",
        str(operation_plan),
        "--capabilities",
        str(capabilities),
        "--manifest-out",
        str(preflight_out),
    ]
    build_out = run_dir / "build_manifest.json"
    inspect_out = run_dir / "inspect_manifest.json"
    qa_out = run_dir / "qa_manifest.json"
    commands = [
        ("preflight", preflight_cmd),
        (
            "build",
            [
                sys.executable,
                str(scripts / "origin_build_worker.py"),
                "--manifest-out",
                str(build_out),
                "--runtime-timeout-seconds",
                runtime_timeout,
                *common,
            ],
        ),
        (
            "inspect",
            [
                sys.executable,
                str(scripts / "origin_inspect_worker.py"),
                "--manifest-out",
                str(inspect_out),
                "--runtime-timeout-seconds",
                runtime_timeout,
                *common,
            ],
        ),
        (
            "qa",
            [
                sys.executable,
                str(scripts / "qa_controller.py"),
                "--manifest-out",
                str(qa_out),
                "--runtime-timeout-seconds",
                runtime_timeout,
                *common,
            ],
        ),
    ]

    command_results = []
    for name, command in commands:
        result = run_command(command, workspace, log_dir=log_dir, worker=name, timeout_seconds=args.worker_timeout_seconds)
        result["worker"] = name
        command_results.append(result)
        if result["returncode"] not in {0} and name in {"preflight", "build", "inspect"}:
            break

    preflight = load_manifest(preflight_out)
    build = load_manifest(build_out)
    inspect = load_manifest(inspect_out)
    qa = load_manifest(qa_out)
    statuses = status_from_workers(preflight, build, inspect, qa, dry_run=args.dry_run)
    manifest: dict[str, Any] = {
        "schema": RUN_MANIFEST_SCHEMA,
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "execution_mode": "dry_run" if args.dry_run else "live",
        "orchestrator": "originplot_orchestrator.v5.2",
        "run_dir": str(run_dir),
        "artifact_manifest": str(artifact_manifest),
        "worker_manifests": {
            "preflight": str(preflight_out),
            "build": str(build_out),
            "inspect": str(inspect_out),
            "qa": str(qa_out),
        },
        "command_results": command_results,
        **statuses,
    }
    if manifest["overall_status"] != "pass":
        manifest["error_code"] = next(
            (
                item.get("error_code")
                for item in command_results
                if item.get("error_code")
            ),
            next(
                (
                    item.get("error_code")
                    for item in [preflight, build, inspect, qa]
                    if item.get("error_code")
                ),
                "E420_VISUAL_MISMATCH" if not args.dry_run else "EVIDENCE_INCOMPLETE",
            ),
        )
    write_json(args.manifest_out, manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["overall_status"] in {"pass", "incomplete"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
