"""Classify native Origin COM startup failures without invoking COM."""

from __future__ import annotations

from typing import Any, Iterable


def classify_origin_com_failure(events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    rows = list(events)
    text = "\n".join(str(row.get("message", "")) for row in rows).lower()
    onag = "origin64.exe" in text and "onag.dll" in text and (
        "faulting module" in text or "错误模块" in text or "appcrash" in text
    )
    dcom = any(int(row.get("id", 0)) == 10010 for row in rows)
    blocking = onag and dcom
    return {
        "error_code": "E301_ORIGIN_COM_SERVER_INITIALIZATION_BLOCKED" if blocking else "E300_ORIGIN_ATTACH_FAILED",
        "blocking": blocking,
        "onag_crash_detected": onag,
        "dcom_timeout_detected": dcom,
        "event_count": len(rows),
        "message": (
            "Origin COM server initialization is blocked by an Origin64.exe ONAG.dll crash; repair/restart Origin before retrying."
            if blocking
            else "Origin COM attach failed without a confirmed ONAG.dll/DCOM initialization signature."
        ),
    }
