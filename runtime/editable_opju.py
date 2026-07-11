from __future__ import annotations

import stat
from pathlib import Path
from typing import Any


def ensure_opju_file_editable(path: Path) -> dict[str, Any]:
    evidence: dict[str, Any] = {
        "schema": "originplot.editable_open_evidence.v1",
        "path": str(path),
        "exists": path.exists(),
        "readonly_attribute_cleared": False,
    }
    if not path.exists():
        evidence["writable_after"] = False
        return evidence

    mode_before = path.stat().st_mode
    readonly_before = not bool(mode_before & stat.S_IWRITE)
    evidence["readonly_before"] = readonly_before
    if readonly_before:
        path.chmod(mode_before | stat.S_IWRITE)
        evidence["readonly_attribute_cleared"] = True

    mode_after = path.stat().st_mode
    evidence["readonly_after"] = not bool(mode_after & stat.S_IWRITE)
    evidence["writable_after"] = bool(mode_after & stat.S_IWRITE)
    return evidence


def open_opju_editable(
    op: Any,
    path: Path,
    *,
    save_after_open: bool = True,
    raise_on_failure: bool = True,
) -> dict[str, Any]:
    evidence = ensure_opju_file_editable(path)
    evidence.update(
        {
            "origin_open_readonly_requested": False,
            "origin_open_asksave": False,
            "same_path_save_verified_after_reopen": False,
        }
    )

    try:
        opened = bool(op.open(str(path), readonly=False, asksave=False))
    except Exception as exc:
        evidence["origin_open_result"] = False
        evidence["origin_open_error"] = str(exc)
        if raise_on_failure:
            raise
        return evidence

    evidence["origin_open_result"] = opened
    if not opened:
        if raise_on_failure:
            raise RuntimeError(f"Origin could not open OPJU in editable mode: {path}")
        return evidence

    if save_after_open:
        try:
            op.save(str(path))
            evidence["same_path_save_verified_after_reopen"] = True
        except Exception as exc:
            evidence["same_path_save_error"] = str(exc)
            if raise_on_failure:
                raise

    return evidence
