from __future__ import annotations

import importlib.util
import os
import platform
import sys
from typing import Any

from .capabilities import resolve_origin_capabilities
from .origin_session import is_administrator


def _origin_registration() -> dict[str, Any]:
    if sys.platform != "win32":
        return {"registered": False, "reason": "non_windows"}
    try:
        import winreg

        for progid in ("Origin.Application", "Origin.ApplicationSI"):
            try:
                with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, progid + r"\CLSID") as key:
                    clsid, _ = winreg.QueryValueEx(key, None)
                    return {"registered": True, "progid": progid, "clsid_present": bool(clsid)}
            except OSError:
                continue
    except Exception:
        pass
    return {"registered": False, "reason": "origin_com_class_not_found"}


def doctor(origin_version: str | None = None) -> dict[str, Any]:
    requested_version = origin_version or os.environ.get("ORIGINPLOT_ORIGIN_VERSION")
    capabilities = resolve_origin_capabilities(requested_version)
    python_ok = sys.version_info[:2] == (3, 10)
    registration = _origin_registration()
    originpro_available = importlib.util.find_spec("originpro") is not None
    originext_available = importlib.util.find_spec("OriginExt") is not None
    windows = sys.platform == "win32"
    return {
        "schema": "originplot.doctor.v3",
        "platform": {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "windows": windows,
        },
        "python": {
            "version": platform.python_version(),
            "validated_baseline": "3.10",
            "baseline_match": python_ok,
            "executable": sys.executable,
        },
        "administrator": {
            "current_process": is_administrator(),
            "origin_worker_required": True,
            "release_controller_required": True,
            "policy_changed_in_v6": False,
        },
        "origin": {
            **registration,
            "originpro_available": originpro_available,
            "originext_available": originext_available,
            "requested_version": requested_version,
            "capabilities": capabilities,
        },
        "ready_for_offline_planning": python_ok,
        "ready_for_live_worker": bool(windows and python_ok and originpro_available and registration.get("registered")),
        "note": "doctor is read-only and does not launch Origin; live success still requires the elevated same-run lifecycle",
    }
