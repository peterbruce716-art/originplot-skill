from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from .core.errors import OriginPlotError
from .core.figure_spec import load_figure_spec
from .core.profiles import ProfileConfig, resolve_profile
from .core.result import normalize_live_result, planned_result
from .runtime.protocol import build_worker_task
from .runtime.origin_session import is_administrator
from .template.policy import TemplateDecision, apply_template_policy


def _read_object(path: Path | None) -> dict[str, Any] | None:
    if path is None:
        return None
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise OriginPlotError("E100_SCHEMA_INVALID", f"JSON object required: {path}")
    return payload


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
            if path.is_file() and path.suffix.lower() in {".otpu", ".otp", ".opju"}:
                semantic_match = any(token in path.stem.lower() for token in tokens)
                if semantic_match:
                    candidates.append({"id": path.stem, "source": "local", "path": str(path), "reusable": True})
                if len(candidates) >= limit:
                    return candidates
    return candidates


def _gallery_candidates(limit: int, search_terms: str) -> list[dict[str, Any]]:
    from scripts.search_official_templates import build_gallery_url, discover

    result = discover(
        build_gallery_url(search_terms or "line", ""),
        max_items=max(1, limit),
        attempts=1,
        timeout=8.0,
        backoff=0.0,
    )
    candidates = []
    for item in result.get("candidates", []):
        if isinstance(item, dict) and item.get("status") == "discovered":
            candidates.append({"id": item.get("gid"), "title": item.get("title"), "source": "originlab_gallery", "detail_url": item.get("detail_url"), "reusable": False})
    return candidates[:limit]


def choose_templates(
    profile: ProfileConfig,
    *,
    strict_record: dict[str, Any] | None = None,
    search_terms: str = "",
    allow_network: bool = False,
) -> TemplateDecision:
    return apply_template_policy(
        profile.template_policy,
        max_candidates=profile.max_template_candidates,
        local_search=lambda limit: _local_candidates(limit, search_terms),
        gallery_search=(lambda limit: _gallery_candidates(limit, search_terms)) if allow_network else None,
        strict_record=strict_record,
    )


def _legacy_worker(
    *,
    profile: ProfileConfig,
    figure: str | None,
    builder: str | None,
    figure_spec: Path | None,
    candidate: Path,
    output_dir: Path,
    live: bool,
    require_live_success: bool,
) -> dict[str, Any]:
    worker = Path(__file__).resolve().parents[1] / "scripts" / "origin_candidate_worker.py"
    command = [sys.executable, str(worker)]
    if figure:
        command += ["--figure", figure]
    if builder:
        command += ["--builder", builder]
    if figure_spec:
        command += ["--figure-spec", str(figure_spec)]
    command += ["--candidate", str(candidate), "--output-dir", str(output_dir)]
    command.append("--live" if live else "--dry-run")
    if require_live_success:
        command.append("--require-live-success")
    completed = subprocess.run(
        command,
        cwd=str(worker.parents[1]),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    manifest_path = output_dir / "candidate_manifest.json"
    if manifest_path.is_file():
        result = _read_object(manifest_path) or {}
    else:
        result = {
            "status": "failed",
            "error_code": "E525_CANDIDATE_WORKER_FAILED",
            "message": completed.stderr.strip() or completed.stdout.strip(),
        }
    result.setdefault("controller_exit_code", completed.returncode)
    if completed.returncode and result.get("status") != "failed":
        result["status"] = "failed"
    return result


def execute(
    *,
    profile: ProfileConfig,
    figure: str | None,
    builder: str | None,
    figure_spec_path: Path | None,
    candidate_path: Path | None,
    output_dir: Path,
    live: bool,
    require_live_success: bool = False,
    source_policy: str | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_payload = _read_object(candidate_path) if candidate_path is not None else None
    if profile.name == "release":
        if live and profile.require_admin_controller and not is_administrator():
            raise OriginPlotError("E120_ENVIRONMENT_MISMATCH", "release controller must run as administrator")
        if candidate_path is None:
            raise OriginPlotError("E100_SCHEMA_INVALID", "release requires --candidate")
        candidate_payload = candidate_payload or {}
        candidate_policy = str(candidate_payload.get("source_data_policy") or candidate_payload.get("data_source_policy") or "supplied")
        if source_policy is not None and source_policy != candidate_policy:
            raise OriginPlotError(
                "E204_SOURCE_POLICY_CONFLICT",
                f"release source policy is fixed by candidate ({candidate_policy}); requested {source_policy}",
            )
        source_policy = candidate_policy
        record_path = candidate_payload.get("template_search_record")
        strict_record = None
        if record_path:
            resolved = Path(str(record_path))
            if not resolved.is_absolute():
                resolved = candidate_path.resolve().parent / resolved
            strict_record = _read_object(resolved) if resolved.is_file() else None
        templates = choose_templates(profile, strict_record=strict_record)
        result = _legacy_worker(
            profile=profile,
            figure=figure,
            builder=builder,
            figure_spec=figure_spec_path,
            candidate=candidate_path,
            output_dir=output_dir,
            live=live,
            require_live_success=require_live_success,
        )
        result["profile"] = "release"
        result["template_policy"] = "strict"
        result["template_decision"] = templates.to_dict()
        return result

    data_payload = None
    if builder == "generic_line":
        if figure_spec_path is None:
            if live:
                raise OriginPlotError("E300_FIGURE_SPEC_INVALID", "generic_line requires --figure-spec for live execution")
        else:
            data_payload = load_figure_spec(figure_spec_path)
    templates = choose_templates(profile, search_terms=figure or builder or "line", allow_network=live)

    if not live:
        result = planned_result(profile, mode="dry_run", warnings=list(templates.warnings))
        result.update(
            {
                "figure": figure,
                "builder": builder,
                "figure_spec": str(figure_spec_path) if figure_spec_path else None,
                "candidate": str(candidate_path) if candidate_path else None,
                "template_decision": templates.to_dict(),
                "data_validation": {"status": "pass", "rows": len(data_payload["x"])} if data_payload else {"status": "not_requested"},
                "source_policy": source_policy or "supplied",
                "message": "Controller planning completed; no Origin process was started.",
            }
        )
        (output_dir / "candidate_summary.json").write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        return result

    if candidate_path is None and builder != "generic_line":
        raise OriginPlotError("E100_SCHEMA_INVALID", "live execution requires --candidate unless builder is generic_line")
    task = build_worker_task(
        profile=profile.to_dict(),
        figure_spec=str(figure_spec_path) if figure_spec_path else None,
        candidate=str(candidate_path),
        builder=builder,
        figure=figure,
        output_dir=output_dir,
        template_decision=templates.to_dict(),
        data_payload=data_payload,
        source_policy=source_policy or "supplied",
    )
    task_path = output_dir / "origin_worker_task.json"
    task_path.write_text(json.dumps(task, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    worker = Path(__file__).resolve().parents[1] / "scripts" / "origin_profile_worker.py"
    completed = subprocess.run(
        [sys.executable, str(worker), "--task", str(task_path)],
        cwd=str(worker.parents[1]),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    result_path = output_dir / "candidate_summary.json"
    result = _read_object(result_path) if result_path.is_file() else None
    if result is None:
        result = {
            "profile": profile.name,
            "status": "failed",
            "overall_status": "failed",
            "error_code": "E525_ORIGIN_WORKER_FAILED",
            "message": completed.stderr.strip() or completed.stdout.strip(),
        }
    result["controller_exit_code"] = completed.returncode
    if profile.name == "standard":
        raw_reference = None
        for key in ("reference_image", "source_reference", "source_crop"):
            if candidate_payload and candidate_payload.get(key):
                raw_reference = str(candidate_payload[key])
                break
        if raw_reference:
            reference = Path(raw_reference)
            if not reference.is_absolute() and candidate_path is not None:
                reference = candidate_path.resolve().parent / reference
            export = output_dir / "candidate_export.png"
            if reference.is_file() and export.is_file():
                from scripts.visual_qa import score_visual

                metrics = score_visual(reference, export, comparison_dir=output_dir / "visual_comparison")
                (output_dir / "candidate_visual_metrics.json").write_text(
                    json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
                )
                result["visual_pass"] = bool(metrics.get("pass_eligible"))
                result.setdefault("gate_results", {})["visual_comparison"] = "pass" if result["visual_pass"] else "failed"
            else:
                result.setdefault("warnings", []).append("W311_REFERENCE_IMAGE_MISSING: basic visual QA was not run")
                (output_dir / "candidate_visual_metrics.json").write_text(
                    json.dumps({"status": "not_run", "reason": "reference_image_missing", "visual_pass": False}, indent=2) + "\n", encoding="utf-8"
                )
        else:
            result.setdefault("warnings", []).append("W310_REFERENCE_IMAGE_NOT_PROVIDED: Standard reports structure only")
            (output_dir / "candidate_visual_metrics.json").write_text(
                json.dumps({"status": "not_run", "reason": "reference_image_not_provided", "visual_pass": False}, indent=2) + "\n", encoding="utf-8"
            )
    normalized = normalize_live_result(profile, result)
    (output_dir / "candidate_summary.json").write_text(
        json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if profile.evidence_level == "visual":
        manifest = {
            "schema": "originplot.profile_manifest.v1",
            "profile": profile.name,
            "overall_status": normalized.get("overall_status"),
            "gates": normalized.get("gates"),
            "gate_results": normalized.get("gate_results"),
            "artifacts": [name for name in ("candidate.opju", "candidate_export.png", "candidate_readback.json", "candidate_visual_metrics.json", "candidate_summary.json") if (output_dir / name).is_file()],
        }
        (output_dir / "candidate_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    return normalized
