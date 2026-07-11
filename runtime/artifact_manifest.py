from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


SCHEMA = "originplot.artifacts.v1"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(
    path: str | Path,
    *,
    run_id: str | None = None,
    producer_worker: str | None = None,
    origin_pid: int | None = None,
    python_pid: int | None = None,
    inherited_from_run: str | None = None,
    inheritance_reason: str | None = None,
    eligible_for_pass: bool | None = None,
) -> dict[str, Any]:
    item = Path(path)
    exists = item.exists()
    record: dict[str, Any] = {
        "path": str(item),
        "exists": exists,
        "size_bytes": item.stat().st_size if exists else 0,
        "sha256": sha256_file(item) if exists and item.is_file() else "",
        "created_at": utc_now(),
        "python_pid": python_pid if python_pid is not None else os.getpid(),
    }
    if run_id:
        record["run_id"] = run_id
    if producer_worker:
        record["producer_worker"] = producer_worker
    if origin_pid is not None:
        record["origin_pid"] = origin_pid
    if inherited_from_run:
        record["inherited_from_run"] = inherited_from_run
        record["inheritance_reason"] = inheritance_reason or "unspecified"
        record["eligible_for_pass"] = False if eligible_for_pass is None else bool(eligible_for_pass)
    elif eligible_for_pass is not None:
        record["eligible_for_pass"] = bool(eligible_for_pass)
    return record


def empty_manifest(run_id: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "run_id": run_id,
        "project": {},
        "pre_save_export": {},
        "inspection": {},
        "post_reopen_export": {},
        "benchmark_actual": {},
        "semantic_benchmark": {},
        "deviation_ledger": {},
        "worker_pids": {},
        "operations": [],
        "warnings": [],
        "errors": [],
    }


def read_artifacts(path: str | Path, run_id: str = "originplot-run") -> dict[str, Any]:
    manifest_path = Path(path)
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if payload.get("schema") != SCHEMA:
            raise ValueError(f"artifact manifest schema must be {SCHEMA}")
        if payload.get("run_id") not in {None, run_id}:
            raise ValueError(f"artifact manifest run_id mismatch: {payload.get('run_id')} != {run_id}")
        return payload
    return empty_manifest(run_id)


def write_artifacts(path: str | Path, payload: dict[str, Any]) -> None:
    manifest_path = Path(path)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"artifact manifest schema must be {SCHEMA}")
    data = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    fd, temp_name = tempfile.mkstemp(prefix=manifest_path.name + ".", suffix=".tmp", dir=str(manifest_path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, manifest_path)
    finally:
        temp_path = Path(temp_name)
        if temp_path.exists():
            temp_path.unlink()


def update_artifacts(path: str | Path, run_id: str, updates: dict[str, Any]) -> dict[str, Any]:
    payload = read_artifacts(path, run_id=run_id)
    payload.setdefault("schema", SCHEMA)
    payload.setdefault("run_id", run_id)
    if payload["run_id"] != run_id:
        raise ValueError(f"artifact manifest run_id mismatch: {payload['run_id']} != {run_id}")
    for key, value in updates.items():
        if key == "operations":
            payload.setdefault("operations", [])
            payload["operations"].extend(value)
        elif key == "worker_pids":
            payload.setdefault("worker_pids", {})
            payload["worker_pids"].update(value)
        elif key in {"warnings", "errors"}:
            payload.setdefault(key, [])
            payload[key].extend(value)
        else:
            payload[key] = value
    write_artifacts(path, payload)
    return payload


def context_paths(context: dict[str, Any]) -> tuple[Path, Path, str]:
    run_dir = Path(context.get("run_dir") or ".").resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    artifacts_path = Path(context.get("artifact_manifest") or run_dir / "run_artifacts.json").resolve()
    run_id = str(context.get("run_id") or run_dir.name or "originplot-run")
    return run_dir, artifacts_path, run_id


def note_operation(context: dict[str, Any], operation: dict[str, Any], status: str, extra: dict[str, Any] | None = None) -> None:
    _, artifacts_path, run_id = context_paths(context)
    record = {
        "seq": operation.get("seq"),
        "worker": operation.get("worker"),
        "operation_id": operation.get("operation_id"),
        "adapter_route": operation.get("adapter_route"),
        "status": status,
    }
    if extra:
        record.update(extra)
    update_artifacts(
        artifacts_path,
        run_id,
        {
            "worker_pids": {str(operation.get("worker") or "unknown"): os.getpid()},
            "operations": [record],
        },
    )


def walk_artifact_records(value: Any) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if {"path", "sha256", "exists"}.issubset(value.keys()):
            records.append(value)
        for item in value.values():
            records.extend(walk_artifact_records(item))
    elif isinstance(value, list):
        for item in value:
            records.extend(walk_artifact_records(item))
    return records


def same_run_failures(payload: dict[str, Any]) -> list[dict[str, Any]]:
    run_id = str(payload.get("run_id") or "")
    failures: list[dict[str, Any]] = []
    for record in walk_artifact_records(payload):
        record_run = record.get("run_id")
        if record.get("inherited_from_run"):
            if record.get("eligible_for_pass") is not False:
                failures.append({"code": "INHERITED_ARTIFACT_ELIGIBLE_FOR_PASS", "path": record.get("path")})
            continue
        if record_run and run_id and record_run != run_id:
            failures.append({"code": "ARTIFACT_RUN_ID_MISMATCH", "expected": run_id, "actual": record_run, "path": record.get("path")})
    return failures


def has_seed_fallback(payload: dict[str, Any]) -> bool:
    text = json.dumps(payload, ensure_ascii=False).lower()
    return "verified_seed_opju_copy" in text or "seed fallback" in text or "seed_opju" in text
