from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_TASK_NAME = "OriginPlotAgent"
DEFAULT_ROOT = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "OriginPlotAgent"
JOB_ID_RE = re.compile(r"^[A-Za-z0-9._-]+$")
ADAPTER_MODULE_WHITELIST = {
    "originpro": "adapters/originpro/adapter.py",
    "inspection": "adapters/inspection/adapter.py",
    "evidence_qa": "adapters/evidence_qa/adapter.py",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def ensure_inside(path: Path, root: Path, label: str) -> Path:
    resolved = path.resolve()
    root_resolved = root.resolve()
    try:
        resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside workspace: {resolved}") from exc
    if resolved.is_symlink():
        raise ValueError(f"{label} must not be a symlink: {resolved}")
    return resolved


def ensure_workspace_or_skill_example(path: Path, workspace: Path, label: str) -> Path:
    """Allow job-local inputs plus read-only examples shipped with the skill."""
    resolved = path.resolve()
    try:
        return ensure_inside(resolved, workspace, label)
    except ValueError:
        skill_examples = Path(__file__).resolve().parents[1] / "examples"
        try:
            resolved.relative_to(skill_examples.resolve())
        except ValueError as exc:
            raise ValueError(f"{label} must stay inside workspace or skill examples: {resolved}") from exc
        if resolved.is_symlink():
            raise ValueError(f"{label} must not be a symlink: {resolved}")
        return resolved


def validate_adapter_modules(path: Path) -> None:
    payload = read_json(path)
    for route, module in payload.items():
        expected = ADAPTER_MODULE_WHITELIST.get(str(route))
        normalized = str(module).replace("\\", "/")
        if expected is None or normalized != expected:
            raise ValueError(f"adapter module route {route!r} must use the built-in whitelist")


def queue_paths(root: Path) -> dict[str, Path]:
    queue = root / "queue"
    return {
        "root": root,
        "queue": queue,
        "inbox": queue / "inbox",
        "running": queue / "running",
        "completed": queue / "completed",
        "failed": queue / "failed",
        "runtime": root / "runtime",
        "logs": root / "logs",
        "heartbeat": root / "runtime" / "heartbeat.json",
    }


def ensure_directories(root: Path) -> dict[str, Path]:
    paths = queue_paths(root)
    for name in ("inbox", "running", "completed", "failed", "runtime", "logs"):
        paths[name].mkdir(parents=True, exist_ok=True)
    return paths


def heartbeat_is_alive(root: Path, max_age_seconds: int) -> bool:
    heartbeat = queue_paths(root)["heartbeat"]
    if not heartbeat.exists():
        return False
    try:
        payload = read_json(heartbeat)
        updated = datetime.fromisoformat(str(payload["updated_at"]))
        if updated.tzinfo is None:
            updated = updated.replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - updated.astimezone(timezone.utc)
        return age.total_seconds() <= max_age_seconds
    except (OSError, KeyError, ValueError, json.JSONDecodeError):
        return False


def write_heartbeat(root: Path, state: str) -> None:
    atomic_write_json(
        queue_paths(root)["heartbeat"],
        {
            "schema": "originplot.local_agent.heartbeat.v1",
            "pid": os.getpid(),
            "state": state,
            "updated_at": utc_now(),
        },
    )


def run_schtasks(task_name: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["schtasks", "/run", "/tn", task_name],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def ensure_agent(root: Path, task_name: str, max_age_seconds: int, startup_timeout_seconds: int) -> dict[str, Any]:
    if heartbeat_is_alive(root, max_age_seconds):
        return {"agent_status": "ready", "start_attempted": False}

    result = run_schtasks(task_name)
    if result.returncode != 0:
        return {
            "agent_status": "start_failed",
            "start_attempted": True,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    deadline = time.monotonic() + startup_timeout_seconds
    while time.monotonic() < deadline:
        if heartbeat_is_alive(root, max_age_seconds):
            return {"agent_status": "ready", "start_attempted": True}
        time.sleep(1)

    return {"agent_status": "startup_timeout", "start_attempted": True}


def submit_job(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    paths = ensure_directories(root)
    workspace = args.workspace.resolve()
    if not JOB_ID_RE.match(args.job_id):
        raise ValueError("job_id may only contain letters, numbers, dot, underscore, and hyphen")
    figure_spec = ensure_workspace_or_skill_example(args.figure_spec, workspace, "figure_spec")
    compiled_ir = ensure_workspace_or_skill_example(args.compiled_ir, workspace, "compiled_ir")
    operation_plan = ensure_workspace_or_skill_example(args.operation_plan, workspace, "operation_plan")
    capabilities = ensure_workspace_or_skill_example(args.capabilities, workspace, "capabilities")
    manifest_out = ensure_inside(args.manifest_out, workspace, "manifest_out")
    run_dir = ensure_inside(args.run_dir, workspace, "run_dir") if args.run_dir else (workspace / "originplot_agent_runs" / args.job_id).resolve()
    artifact_manifest = ensure_inside(args.artifact_manifest, workspace, "artifact_manifest") if args.artifact_manifest else None
    adapter_modules = ensure_inside(args.adapter_modules, workspace, "adapter_modules") if args.adapter_modules else None
    adapter_configs = ensure_inside(args.adapter_configs, workspace, "adapter_configs") if args.adapter_configs else None
    if adapter_modules:
        validate_adapter_modules(adapter_modules)
    job = {
        "schema": "originplot.local_agent.job.v1",
        "job_id": args.job_id,
        "created_at": utc_now(),
        "execution_route": "local_agent",
        "fallback_reason": args.fallback_reason,
        "approval_status": "service_unavailable",
        "fallback_status": "activated",
        "origin_execution_status": "queued",
        "approval_attempts": args.approval_attempts,
        "workspace": str(workspace),
        "figure_spec": str(figure_spec),
        "compiled_ir": str(compiled_ir),
        "operation_plan": str(operation_plan),
        "capabilities": str(capabilities),
        "manifest_out": str(manifest_out),
        "adapter_modules": str(adapter_modules) if adapter_modules else "",
        "adapter_configs": str(adapter_configs) if adapter_configs else "",
        "run_dir": str(run_dir),
        "artifact_manifest": str(artifact_manifest) if artifact_manifest else "",
        "timeout_seconds": args.timeout_seconds,
        "dry_run": bool(args.dry_run),
    }

    agent_report = {"agent_status": "not_started", "start_attempted": False}
    if not args.no_start:
        agent_report = ensure_agent(root, args.task_name, args.heartbeat_max_age_seconds, args.startup_timeout_seconds)
    job["agent_status"] = agent_report["agent_status"]

    destination = paths["inbox"] / f"{args.job_id}.json"
    atomic_write_json(destination, job)

    status = {
        "schema": "originplot.local_agent.submit_status.v1",
        "job_id": args.job_id,
        "status": "queued",
        "execution_route": "local_agent",
        "fallback_reason": args.fallback_reason,
        "approval_status": "service_unavailable",
        "fallback_status": "activated",
        "agent_status": agent_report["agent_status"],
        "origin_execution_status": "queued",
        "approval_attempts": args.approval_attempts,
        "queued_job": str(destination),
        "created_at": utc_now(),
    }
    if args.status_out:
        atomic_write_json(args.status_out.resolve(), status)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


def claim_job(job_path: Path, running_dir: Path) -> Path | None:
    claimed = running_dir / job_path.name
    try:
        os.replace(job_path, claimed)
        return claimed
    except (FileNotFoundError, PermissionError):
        return None


def runtime_script() -> Path:
    return Path(__file__).resolve().parent / "originplot_orchestrator.py"


def run_runtime(job: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(runtime_script()),
        "--operation-plan",
        job["operation_plan"],
        "--capabilities",
        job["capabilities"],
        "--manifest-out",
        job["manifest_out"],
        "--run-dir",
        job["run_dir"],
        "--workspace",
        job["workspace"],
        "--run-id",
        job["job_id"],
    ]
    if job.get("artifact_manifest"):
        command.extend(["--artifact-manifest", str(job["artifact_manifest"])])
    if job.get("adapter_modules"):
        command.extend(["--adapter-modules", str(job["adapter_modules"])])
    if job.get("adapter_configs"):
        command.extend(["--adapter-configs", str(job["adapter_configs"])])
    if job.get("dry_run"):
        command.append("--dry-run")
    return subprocess.run(
        command,
        cwd=str(Path(job["workspace"])),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=int(job.get("timeout_seconds", 900)),
        check=False,
    )


def normalize_dry_run_manifest(job: dict[str, Any]) -> None:
    if not job.get("dry_run"):
        return
    manifest_path = Path(str(job.get("manifest_out", "")))
    if not manifest_path.exists():
        return
    try:
        payload = read_json(manifest_path)
    except Exception:
        return
    payload["overall_status"] = "ok_dry_run"
    payload["origin_execution_status"] = "dry_run_completed"
    payload["local_agent_dry_run_normalized"] = True
    atomic_write_json(manifest_path, payload)


def complete_job(paths: dict[str, Path], job_file: Path, job: dict[str, Any], result: subprocess.CompletedProcess[str]) -> None:
    job_id = str(job["job_id"])
    result_dir = paths["completed"] / job_id
    result_dir.mkdir(parents=True, exist_ok=True)
    (result_dir / "runtime.stdout.log").write_text(result.stdout, encoding="utf-8")
    (result_dir / "runtime.stderr.log").write_text(result.stderr, encoding="utf-8")
    normalize_dry_run_manifest(job)
    atomic_write_json(
        result_dir / "status.json",
        {
            "schema": "originplot.local_agent.result_status.v1",
            "job_id": job_id,
            "status": "completed",
            "execution_route": "local_agent",
            "fallback_reason": job.get("fallback_reason", "approval_service_503"),
            "approval_status": job.get("approval_status", "service_unavailable"),
            "fallback_status": "completed",
            "agent_status": "ready",
            "origin_execution_status": "completed" if not job.get("dry_run") else "dry_run_completed",
            "manifest_out": job.get("manifest_out", ""),
            "completed_at": utc_now(),
        },
    )
    job_file.unlink(missing_ok=True)


def fail_job(paths: dict[str, Path], job_file: Path, error: BaseException, stdout: str = "", stderr: str = "") -> None:
    job_id = job_file.stem
    result_dir = paths["failed"] / job_id
    result_dir.mkdir(parents=True, exist_ok=True)
    if job_file.exists():
        shutil.move(str(job_file), str(result_dir / job_file.name))
    (result_dir / "runtime.stdout.log").write_text(stdout, encoding="utf-8")
    (result_dir / "runtime.stderr.log").write_text(stderr, encoding="utf-8")
    atomic_write_json(
        result_dir / "status.json",
        {
            "schema": "originplot.local_agent.result_status.v1",
            "job_id": job_id,
            "status": "failed",
            "execution_route": "local_agent",
            "fallback_reason": "approval_service_503",
            "approval_status": "service_unavailable",
            "fallback_status": "failed",
            "agent_status": "ready",
            "origin_execution_status": "failed",
            "failed_at": utc_now(),
            "error": str(error),
            "traceback": traceback.format_exc(),
        },
    )


def process_one(root: Path) -> bool:
    paths = ensure_directories(root)
    for waiting in sorted(paths["inbox"].glob("*.json")):
        claimed = claim_job(waiting, paths["running"])
        if claimed is None:
            continue
        try:
            write_heartbeat(root, "running")
            job = read_json(claimed)
            result = run_runtime(job)
            if result.returncode != 0:
                raise RuntimeError(f"originplot_orchestrator failed with code {result.returncode}")
            complete_job(paths, claimed, job, result)
        except Exception as error:
            stdout = locals().get("result").stdout if "result" in locals() else ""
            stderr = locals().get("result").stderr if "result" in locals() else ""
            fail_job(paths, claimed, error, stdout=stdout, stderr=stderr)
        finally:
            write_heartbeat(root, "ready")
        return True
    return False


def run_agent(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    ensure_directories(root)
    write_heartbeat(root, "ready")
    if args.once:
        process_one(root)
        write_heartbeat(root, "ready")
        return 0

    last_heartbeat = 0.0
    while True:
        now = time.monotonic()
        if now - last_heartbeat >= args.heartbeat_seconds:
            write_heartbeat(root, "ready")
            last_heartbeat = now
        process_one(root)
        time.sleep(args.poll_seconds)


def install_task(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    script = Path(__file__).resolve()
    command = f'"{sys.executable}" "{script}" agent --root "{root}"'
    result = subprocess.run(
        ["schtasks", "/create", "/tn", args.task_name, "/sc", "ONLOGON", "/tr", command, "/it", "/rl", "LIMITED", "/f"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    print(result.stdout, end="")
    print(result.stderr, end="", file=sys.stderr)
    return result.returncode


def status(args: argparse.Namespace) -> int:
    root = args.root.resolve()
    paths = ensure_directories(root)
    payload: dict[str, Any] = {
        "schema": "originplot.local_agent.status.v1",
        "root": str(root),
        "heartbeat_alive": heartbeat_is_alive(root, args.heartbeat_max_age_seconds),
        "counts": {
            name: len(list(paths[name].glob("*.json"))) if name in {"inbox", "running"} else len([p for p in paths[name].iterdir() if p.is_dir()])
            for name in ("inbox", "running", "completed", "failed")
        },
    }
    if paths["heartbeat"].exists():
        payload["heartbeat"] = read_json(paths["heartbeat"])
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="File-queue Local Origin Agent fallback for approval-service 503 events."
    )
    sub = parser.add_subparsers(dest="command", required=True)

    submit = sub.add_parser("submit", help="Queue an OriginPlot job for the local agent.")
    submit.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    submit.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    submit.add_argument("--job-id", required=True)
    submit.add_argument("--workspace", type=Path, required=True)
    submit.add_argument("--figure-spec", type=Path, required=True)
    submit.add_argument("--compiled-ir", type=Path, required=True)
    submit.add_argument("--operation-plan", type=Path, required=True)
    submit.add_argument("--capabilities", type=Path, required=True)
    submit.add_argument("--manifest-out", type=Path, required=True)
    submit.add_argument("--adapter-modules", type=Path, help="JSON mapping route to adapter module, forwarded to runtime v5.")
    submit.add_argument("--adapter-configs", type=Path, help="JSON mapping route to adapter config, forwarded to runtime v5.")
    submit.add_argument("--run-dir", type=Path)
    submit.add_argument("--artifact-manifest", type=Path)
    submit.add_argument("--timeout-seconds", type=int, default=900)
    submit.add_argument("--heartbeat-max-age-seconds", type=int, default=30)
    submit.add_argument("--startup-timeout-seconds", type=int, default=30)
    submit.add_argument("--fallback-reason", default="approval_service_503")
    submit.add_argument("--approval-attempts", type=int, default=3)
    submit.add_argument("--dry-run", action="store_true")
    submit.add_argument("--no-start", action="store_true", help="Queue only; do not run schtasks.")
    submit.add_argument("--status-out", type=Path)
    submit.set_defaults(func=submit_job)

    agent = sub.add_parser("agent", help="Run the local queue worker.")
    agent.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    agent.add_argument("--once", action="store_true")
    agent.add_argument("--poll-seconds", type=float, default=2.0)
    agent.add_argument("--heartbeat-seconds", type=float, default=10.0)
    agent.set_defaults(func=run_agent)

    install = sub.add_parser("install-task", help="Install an ONLOGON scheduled task for the current user.")
    install.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    install.add_argument("--task-name", default=DEFAULT_TASK_NAME)
    install.set_defaults(func=install_task)

    stat = sub.add_parser("status", help="Report queue counts and heartbeat state.")
    stat.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    stat.add_argument("--heartbeat-max-age-seconds", type=int, default=30)
    stat.set_defaults(func=status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
