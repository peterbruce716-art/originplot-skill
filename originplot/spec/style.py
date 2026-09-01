from __future__ import annotations

from copy import deepcopy
from typing import Any

# Keep the executable style surface deliberately smaller than the aspirational
# FigureSpec vocabulary. A field belongs here only when the Origin adapter has
# deterministic handling for it; everything else is surfaced in style_audit.
_TOP_LEVEL = {"theme", "legend", "series"}
_LEGEND_FIELDS = {"visible", "frame"}
_SERIES_FIELDS = {"color", "line_color", "line_width_pt", "symbol"}


def _filter_style(payload: dict[str, Any] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = payload or {}
    accepted: dict[str, Any] = {}
    rejected: list[dict[str, Any]] = []
    for key, value in payload.items():
        if key not in _TOP_LEVEL:
            rejected.append({"path": key, "reason": "not an executable allow-listed visual style field"})
            continue
        if key == "theme":
            if isinstance(value, str) and value.strip():
                accepted[key] = value.strip()
            else:
                rejected.append({"path": key, "reason": "theme must be a non-empty string"})
        elif key == "legend":
            if not isinstance(value, dict):
                rejected.append({"path": key, "reason": "legend must be an object"})
                continue
            clean: dict[str, Any] = {}
            for field, item in value.items():
                path = f"legend.{field}"
                if field not in _LEGEND_FIELDS:
                    rejected.append({"path": path, "reason": "legend field is not executed by the v6 Origin adapter"})
                elif not isinstance(item, bool):
                    rejected.append({"path": path, "reason": "legend visibility/frame values must be boolean"})
                else:
                    clean[field] = item
            if clean:
                accepted[key] = clean
        elif key == "series":
            if not isinstance(value, dict):
                rejected.append({"path": key, "reason": "series must be an object"})
                continue
            clean_series: dict[str, Any] = {}
            for series_id, series_style in value.items():
                if not isinstance(series_style, dict):
                    rejected.append({"path": f"series.{series_id}", "reason": "series style must be an object"})
                    continue
                clean: dict[str, Any] = {}
                for field, item in series_style.items():
                    path = f"series.{series_id}.{field}"
                    if field not in _SERIES_FIELDS:
                        rejected.append({"path": path, "reason": "series field is not executed by the v6 Origin adapter"})
                    elif field in {"color", "line_color"}:
                        if isinstance(item, (str, int)) and not isinstance(item, bool):
                            clean[field] = item
                        else:
                            rejected.append({"path": path, "reason": "color must be an Origin-compatible string or integer"})
                    elif field == "line_width_pt":
                        if isinstance(item, (int, float)) and not isinstance(item, bool) and float(item) >= 0:
                            clean[field] = item
                        else:
                            rejected.append({"path": path, "reason": "line_width_pt must be a non-negative number"})
                    elif field == "symbol":
                        if isinstance(item, int) and not isinstance(item, bool):
                            clean[field] = item
                        else:
                            rejected.append({"path": path, "reason": "symbol must be an integer Origin symbol id"})
                if clean:
                    clean_series[str(series_id)] = clean
            if clean_series:
                accepted[key] = clean_series
    return accepted, rejected


def _merge(target: dict[str, Any], incoming: dict[str, Any], source: str, sources: dict[str, str], prefix: str = "") -> None:
    for key, value in incoming.items():
        path = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            current = target.get(key)
            if not isinstance(current, dict):
                current = {}
                target[key] = current
            _merge(current, value, source, sources, path)
        else:
            target[key] = deepcopy(value)
            sources[path] = source


def resolve_style(
    *,
    defaults: dict[str, Any] | None = None,
    preset: dict[str, Any] | None = None,
    reference: dict[str, Any] | None = None,
    user: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve visual style without allowing reference material to alter scientific semantics.

    Precedence is explicit user > confirmed reference > preset > defaults. All four
    sources are filtered through the same executable visual allow-list; fields that the
    live adapter cannot honor are rejected into the audit instead of being silently
    accepted and ignored.
    """

    style: dict[str, Any] = {}
    sources: dict[str, str] = {}
    rejected: list[dict[str, Any]] = []
    for source, payload in (("default", defaults), ("preset", preset), ("reference", reference), ("user", user)):
        clean, denied = _filter_style(payload)
        for item in denied:
            rejected.append({**item, "source": source})
        _merge(style, clean, source, sources)
    return {"style": style, "sources": sources, "rejected": rejected}
