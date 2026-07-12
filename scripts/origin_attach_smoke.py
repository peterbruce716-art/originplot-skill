from __future__ import annotations

import argparse
import importlib.metadata as metadata
import json
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from scripts.origin_com_health import classify_origin_com_failure
except ImportError:
    from origin_com_health import classify_origin_com_failure


def package_version(name: str) -> str:
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not_installed"


def write_status(path: Path | None, result: dict[str, Any]) -> None:
    if path is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_status(path: Path | None) -> dict[str, Any]:
    if path is None or not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        return payload if isinstance(payload, dict) else {}
    except Exception:
        return {}


def collect_recent_origin_events(since: datetime) -> list[dict[str, Any]]:
    """Collect only recent WER/DCOM records needed to explain a native timeout."""
    script = (
        "$since = [datetime]::Parse('%s'); "
        "$rows = @(); "
        "Get-WinEvent -FilterHashtable @{LogName='Application'; Id=1000,1001; StartTime=$since} -ErrorAction SilentlyContinue | "
        "ForEach-Object { if ($_.Message -match 'Origin64\\.exe|ONAG\\.dll') { $rows += [pscustomobject]@{log='Application'; id=$_.Id; message=$_.Message} } }; "
        "Get-WinEvent -FilterHashtable @{LogName='System'; Id=10010; StartTime=$since} -ErrorAction SilentlyContinue | "
        "ForEach-Object { $rows += [pscustomobject]@{log='System'; id=$_.Id; message=$_.Message} }; "
        "$rows | ConvertTo-Json -Compress"
    ) % since.strftime("%Y-%m-%dT%H:%M:%S")
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=15,
        )
        payload = json.loads(completed.stdout) if completed.stdout.strip() else []
        return payload if isinstance(payload, list) else [payload]
    except Exception:
        return []


def cleanup_embedding_processes(*, attempts: int = 15, delay_seconds: float = 1.0) -> dict[str, Any]:
    script = (
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
    stopped: list[int] = []
    failures: list[str] = []
    last_returncode = 0
    for attempt in range(max(1, attempts)):
        if attempt:
            time.sleep(max(0.0, delay_seconds))
        try:
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-Command", script],
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=10,
            )
            last_returncode = completed.returncode
            stopped.extend(int(item) for item in completed.stdout.strip().split(",") if item.strip().isdigit())
        except Exception as exc:
            failures.append(f"{exc.__class__.__name__}: {exc}")
    unique = sorted(set(stopped))
    result: dict[str, Any] = {"stopped_embedding_pids": unique, "returncode": last_returncode, "attempts": max(1, attempts)}
    if failures:
        result["cleanup_errors"] = failures
    return result


def launch_delayed_embedding_cleanup(status_json: Path | None) -> dict[str, Any]:
    helper = Path(__file__).resolve().parent / "origin_cleanup_embedding.py"
    if status_json is not None:
        json_out = status_json.resolve().with_name(status_json.stem + "_delayed_embedding_cleanup.json")
    else:
        json_out = Path("outputs/origin_attach_smoke/delayed_embedding_cleanup.json").resolve()
    stdout_log = json_out.with_suffix(".stdout.log")
    stderr_log = json_out.with_suffix(".stderr.log")
    command = [
        sys.executable,
        str(helper),
        "--duration-seconds",
        "45",
        "--interval-seconds",
        "2",
        "--json-out",
        str(json_out),
    ]
    stdout_log.parent.mkdir(parents=True, exist_ok=True)
    stdout_handle = stdout_log.open("w", encoding="utf-8")
    stderr_handle = stderr_log.open("w", encoding="utf-8")
    kwargs: dict[str, Any] = {
        "stdout": stdout_handle,
        "stderr": stderr_handle,
        "close_fds": True,
        "cwd": str(Path.cwd()),
    }
    if sys.platform.startswith("win"):
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        process = subprocess.Popen(command, **kwargs)
        return {
            "status": "started",
            "pid": process.pid,
            "json_out": str(json_out),
            "stdout_log": str(stdout_log),
            "stderr_log": str(stderr_log),
            "command": command,
        }
    except Exception as exc:
        return {"status": "failed", "error": f"{exc.__class__.__name__}: {exc}", "command": command}


def run_parent(args: argparse.Namespace) -> int:
    timeout = max(1, int(args.phase_timeout_seconds))
    pre_cleanup = cleanup_embedding_processes(attempts=1, delay_seconds=0.0)
    command = [
        sys.executable,
        str(Path(__file__).resolve()),
        "--child-process",
        "--output-dir",
        str(args.output_dir),
        "--originext-mode",
        str(args.originext_mode),
        "--export-width",
        str(args.export_width),
    ]
    if args.status_json:
        command.extend(["--status-json", str(args.status_json)])
    if args.new_hidden:
        command.append("--new-hidden")
    try:
        completed = subprocess.run(
            command,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
            timeout=timeout,
        )
        if completed.stdout:
            print(completed.stdout, end="")
        if completed.stderr:
            print(completed.stderr, end="", file=sys.stderr)
        return completed.returncode
    except subprocess.TimeoutExpired as exc:
        status = read_status(args.status_json)
        if not status:
            status = {
                "output_dir": str(args.output_dir.resolve()),
                "steps": [],
                "errors": [],
                "mode": args.originext_mode if args.originext_mode != "originpro" else ("new_hidden" if args.new_hidden else "attach_existing"),
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "python_executable": sys.executable,
                "python_version": sys.version,
                "originpro_version": package_version("originpro"),
                "OriginExt_version": package_version("OriginExt"),
                "pywin32_version": package_version("pywin32"),
            }
        status["status"] = "failed"
        status["error_code"] = "origin_attach_smoke_timeout"
        status["timeout_seconds"] = timeout
        status.setdefault("errors", []).append(
            {
                "error_class": "TimeoutExpired",
                "message": "Child process did not return from Origin attach or OriginExt constructor before timeout.",
                "last_step": status.get("steps", [None])[-1] if status.get("steps") else None,
            }
        )
        status["timeout_stdout_tail"] = str(exc.stdout or "")[-1000:]
        status["timeout_stderr_tail"] = str(exc.stderr or "")[-1000:]
        status["pre_spawn_embedding_cleanup"] = pre_cleanup
        status["embedding_cleanup"] = cleanup_embedding_processes()
        status["delayed_embedding_cleanup"] = launch_delayed_embedding_cleanup(args.status_json)
        health = classify_origin_com_failure(collect_recent_origin_events(datetime.now()))
        status["origin_com_health"] = health
        if health["blocking"]:
            status["error_code"] = health["error_code"]
            status["message"] = health["message"]
        write_status(args.status_json, status)
        print(json.dumps(status, ensure_ascii=False, indent=2), flush=True)
        return 124


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a generic OriginPro/OriginExt smoke test.")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/origin_attach_smoke"))
    parser.add_argument("--status-json", type=Path)
    parser.add_argument("--new-hidden", action="store_true", help="Use originpro new-hidden mode instead of attach-existing.")
    parser.add_argument(
        "--phase-timeout-seconds",
        type=int,
        default=45,
        help="Parent-process hard timeout for COM attach/constructor phases; exits 124 if a native call blocks.",
    )
    parser.add_argument("--child-process", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument(
        "--originext-mode",
        choices=["originpro", "originext_application", "originext_si", "originext_comsi"],
        default="originpro",
        help="Use an OriginExt constructor smoke instead of originpro when not set to originpro.",
    )
    parser.add_argument("--export-width", type=int, default=600)
    args = parser.parse_args()

    if not args.child_process:
        return run_parent(args)

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, Any] = {
        "output_dir": str(out_dir),
        "steps": [],
        "errors": [],
        "mode": args.originext_mode if args.originext_mode != "originpro" else ("new_hidden" if args.new_hidden else "attach_existing"),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "python_executable": sys.executable,
        "python_version": sys.version,
        "originpro_version": package_version("originpro"),
        "OriginExt_version": package_version("OriginExt"),
        "pywin32_version": package_version("pywin32"),
    }
    op = None
    originext_app = None
    try:
        if args.originext_mode != "originpro":
            result["steps"].append("before_import_originext")
            write_status(args.status_json, result)
            import OriginExt  # type: ignore

            result["steps"].append("after_import_originext")
            class_by_mode = {
                "originext_application": OriginExt.Application,
                "originext_si": OriginExt.ApplicationSI,
                "originext_comsi": OriginExt.ApplicationCOMSI,
            }
            result["steps"].append(f"create_{args.originext_mode}")
            write_status(args.status_json, result)
            originext_app = class_by_mode[args.originext_mode]()
            for command, step in [("sec -poc", "lt_sec_poc"), ("doc -s", "lt_doc_s"), ("doc -nt", "lt_doc_nt")]:
                result["steps"].append(step)
                write_status(args.status_json, result)
                originext_app.LT_execute(command)
            result["status"] = "ok"
        else:
            result["steps"].append("before_import_originpro")
            write_status(args.status_json, result)
            import originpro as op  # type: ignore

            result["steps"].append("after_import_originpro")
            if args.new_hidden:
                result["steps"].append("new_hidden")
            else:
                result["steps"].append("attach")
                write_status(args.status_json, result)
                op.attach()
            result["steps"].append("new")
            write_status(args.status_json, result)
            op.new(asksave=False)
            result["steps"].append("new_graph")
            write_status(args.status_json, result)
            gp = op.new_graph(lname="OriginSmokeGraph", template="LINE")
            png = out_dir / "origin_smoke.png"
            result["steps"].append("save_fig")
            write_status(args.status_json, result)
            gp.save_fig(str(png), type="png", replace=True, width=args.export_width)
            result["png_exists"] = png.exists()
            result["png_size"] = png.stat().st_size if png.exists() else 0
            opju = out_dir / "origin_smoke.opju"
            result["steps"].append("save_opju")
            write_status(args.status_json, result)
            op.save(str(opju))
            result["opju_exists"] = opju.exists()
            result["opju_size"] = opju.stat().st_size if opju.exists() else 0
            result["status"] = "ok"
    except Exception as exc:
        result["status"] = "failed"
        result["errors"].append({"error_class": exc.__class__.__name__, "message": str(exc)})
    finally:
        if originext_app is not None:
            for release_name in ["Detach", "Exit"]:
                release = getattr(originext_app, release_name, None)
                if release is None:
                    continue
                try:
                    release()
                    result["release"] = f"OriginExt.{release_name}()"
                    break
                except Exception as exc:
                    result["release"] = f"OriginExt.{release_name}() failed: {exc.__class__.__name__}: {exc}"
        elif op is not None:
            try:
                if args.new_hidden:
                    op.exit()
                    result["release"] = "op.exit()"
                else:
                    op.detach()
                    result["release"] = "op.detach()"
            except Exception as exc:
                release_call = "op.exit()" if args.new_hidden else "op.detach()"
                result["release"] = f"{release_call} failed: {exc.__class__.__name__}: {exc}"
        else:
            result["release"] = "not_imported"

    write_status(args.status_json, result)
    print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
    return 0 if result.get("status") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
