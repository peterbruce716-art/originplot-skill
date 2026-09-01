from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

from originplot.builders import compile_figure
from originplot.core.errors import OriginPlotError
from originplot.core.profiles import ProfileConfig
from originplot.operation_plan import OperationPlan
from originplot.runtime.capabilities import live_execution_block
from originplot.runtime.origin_session import is_administrator
from originplot.runtime.protocol import build_worker_task
from originplot.spec import load_figure_spec
from originplot.template.policy import TemplateDecision, apply_template_policy


def _local_candidates(limit: int, search_terms: str) -> list[dict[str, Any]]:
    root = Path(__file__).resolve().parents[1]
    candidates: list[dict[str, Any]] = []
    tokens = [token for token in re.split(r"[^a-z0-9]+", search_terms.lower()) if len(token) > 2]
    folders = [root / "assets" / "templates", root / "templates", Path.home() / "Documents" / "OriginLab" / "User Files"]
    for variable in ("APPDATA", "PROGRAMDATA"):
        if os.environ.get(variable):
            folders.append(Path(os.environ[variable]) / "OriginLab")
    for folder in folders:
        if not folder.is_dir():
            continue
        for path in sorted(folder.rglob("*")):
            if path.is_file() and path.suffix.lower() in {".otpu", ".otp", ".opju"} and any(token in path.stem.lower() for token in tokens):
                candidates.append({"id": path.stem, "source": "local", "path": str(path), "reusable": True})
                if len(candidates) >= limit:
                    return candidates
    return candidates


def _gallery_candidates(limit: int, search_terms: str) -> list[dict[str, Any]]:
    from scripts.search_official_templates import build_gallery_url, discover

    result = discover(build_gallery_url(search_terms or "line", ""), max_items=max(1, limit), attempts=3, timeout=8.0, backoff=0.5)
    return [
        {"id": item.get("gid"), "title": item.get("title"), "source": "originlab_gallery", "detail_url": item.get("detail_url"), "reusable": False}
        for item in result.get("candidates", [])
        if isinstance(item, dict) and item.get("status") == "discovered"
    ][:limit]


def choose_templates(profile: ProfileConfig, *, search_terms: str, allow_network: bool = False) -> TemplateDecision:
    return apply_template_policy(
        profile.template_policy,
        max_candidates=profile.max_template_candidates,
        local_search=lambda limit: _local_candidates(limit, search_terms),
        gallery_search=(lambda limit: _gallery_candidates(limit, search_terms)) if allow_network else None,
        strict_record=None,
    )


def _public_template_decision(decision: TemplateDecision) -> dict[str, Any]:
    payload = decision.to_dict()

    def sanitize(value: Any) -> Any:
        if isinstance(value, dict):
            return {key: sanitize(item) for key, item in value.items() if key != "path"}
        if isinstance(value, list):
            return [sanitize(item) for item in value]
        return value

    return sanitize(payload)


def _resolve_powershell_executable() -> Path:
    for executable in ("pwsh", "powershell"):
        resolved = shutil.which(executable)
        if resolved:
            return Path(resolved)
    fallback = Path(r"C:\Program Files\PowerShell\7\pwsh.exe")
    if fallback.is_file():
        return fallback
    raise OriginPlotError("E120_ENVIRONMENT_MISMATCH", "PowerShell is required for elevated Origin execution")


def _run_profile_worker(worker: Path, task_path: Path) -> subprocess.CompletedProcess[str]:
    cwd = worker.parents[1]
    if sys.platform != "win32" or is_administrator():
        command = [sys.executable, str(worker), "--task", str(task_path)]
    else:
        launcher = worker.parent / "run_origin_profile_worker_elevated.ps1"
        pwsh = _resolve_powershell_executable()
        command = [
            str(pwsh), "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(launcher),
            "-PythonExe", sys.executable,
            "-WorkerScript", str(worker),
            "-TaskPath", str(task_path),
            "-WorkingDirectory", str(cwd),
        ]
    return subprocess.run(command, cwd=str(cwd), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _blocked_live_result(
    *,
    profile: ProfileConfig,
    plot_type: str,
    source_hash: str,
    templates: TemplateDecision,
    block: dict[str, str],
) -> dict[str, Any]:
    return {
        "schema": "originplot.verification.v1",
        "profile": profile.name,
        "status": "failed",
        "overall_status": "failed",
        "command_success": False,
        "live_origin_verified": False,
        "pass_eligible": False,
        "plot_type": plot_type,
        "builder": plot_type,
        "source_hash": source_hash,
        "error_code": block["error_code"],
        "live_block_reason": block["reason"],
        "message": block["message"],
        "template_decision": _public_template_decision(templates),
    }


def execute(
    *,
    profile: ProfileConfig,
    figure_spec_path: Path,
    output_dir: Path,
    live: bool,
    require_live_success: bool = False,
    source_policy: str = "supplied",
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    spec = load_figure_spec(figure_spec_path)
    plan = compile_figure(spec)
    templates = choose_templates(profile, search_terms=spec.plot_type, allow_network=live)
    plan = replace(
        plan,
        profile=profile.name,
        metadata={**plan.metadata, "template_decision": templates.to_dict()},
    )

    normalized_spec = spec.to_dict()
    _write_json(output_dir / "figure_spec.json", normalized_spec)
    _write_json(output_dir / "operation_plan.json", plan.to_dict())

    if profile.name == "release":
        if live and profile.require_admin_controller and not is_administrator():
            raise OriginPlotError("E120_ENVIRONMENT_MISMATCH", "release controller must run as administrator")
        result = {
            "profile": "release",
            "status": "failed" if live else "planned_not_executed",
            "overall_status": "failed" if live else "planned_not_executed",
            "command_success": False,
            "pass_eligible": False,
            "error_code": "E440_GENERAL_RELEASE_NOT_PROMOTED" if live else None,
            "message": "v6 general Release remains fail-closed; AA2195 strict Release is retained under benchmarks/aa2195",
            "template_decision": _public_template_decision(templates),
        }
        _write_json(output_dir / "verification.json", result)
        return result

    if not live:
        result = {
            "schema": "originplot.verification.v1",
            "profile": profile.name,
            "status": "planned_not_executed",
            "overall_status": "planned_not_executed",
            "command_success": True,
            "live_origin_verified": False,
            "pass_eligible": False,
            "plot_type": spec.plot_type,
            "builder": spec.plot_type,
            "source_hash": spec.source_hash,
            "template_decision": _public_template_decision(templates),
            "message": "FigureSpec and OperationPlan compiled successfully; no Origin process was started.",
        }
        _write_json(output_dir / "verification.json", result)
        return result

    block = live_execution_block(spec.plot_type)
    if block is not None:
        result = _blocked_live_result(
            profile=profile,
            plot_type=spec.plot_type,
            source_hash=spec.source_hash,
            templates=templates,
            block=block,
        )
        _write_json(output_dir / "verification.json", result)
        return result

    task = build_worker_task(
        profile=profile.to_dict(),
        figure_spec=str((output_dir / "figure_spec.json").resolve()),
        output_dir=output_dir,
        operation_plan=plan.to_dict(),
        template_decision=templates.to_dict(),
        source_policy=source_policy,
    )
    task_path = output_dir / ".origin_worker_task.json"
    _write_json(task_path, task)
    worker = Path(__file__).resolve().parents[1] / "scripts" / "origin_profile_worker.py"
    try:
        completed = _run_profile_worker(worker, task_path)
    finally:
        task_path.unlink(missing_ok=True)
    verification_path = output_dir / "verification.json"
    if verification_path.is_file():
        result = json.loads(verification_path.read_text(encoding="utf-8-sig"))
    else:
        result = {
            "profile": profile.name,
            "command_success": False,
            "overall_status": "failed",
            "error_code": "E525_ORIGIN_WORKER_FAILED",
            "message": completed.stderr.strip() or completed.stdout.strip(),
        }
        _write_json(verification_path, result)
    result["controller_exit_code"] = completed.returncode
    result["template_decision"] = _public_template_decision(templates)
    _write_json(verification_path, result)
    if require_live_success and not result.get("command_success"):
        result.setdefault("error_code", "E526_LIVE_SUCCESS_REQUIRED")
    return result
