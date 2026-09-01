from __future__ import annotations

from copy import deepcopy
from typing import Any

_TOP_LEVEL = {"theme", "legend", "series", "matrix"}
_LEGEND_FIELDS = {"visible", "frame", "position"}
_SERIES_FIELDS = {"color", "line_color", "line_width_pt", "symbol", "symbol_size_pt", "fill_transparency_percent"}
_MATRIX_FIELDS = {"colormap", "levels", "show_colorbar"}


def _filter_style(payload: dict[str, Any] | None) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    payload = payload or {}
    accepted: dict[str, Any] = {}
    rejected: list[dict[str, Any]] = []
    for key, value in payload.items():
        if key not in _TOP_LEVEL:
            rejected.append({"path": key, "reason": "not an allow-listed visual style field"})
            continue
        if key == "theme":
            if isinstance(value, str):
                accepted[key] = value
            else:
                rejected.append({"path": key, "reason": "theme must be a string"})
        elif key == "legend":
            if not isinstance(value, dict):
                rejected.append({"path": key, "reason": "legend must be an object"})
                continue
            clean: dict[str, Any] = {}
            for field, item in value.items():
                if field in _LEGEND_FIELDS:
                    clean[field] = item
                else:
                    rejected.append({"path": f"legend.{field}", "reason": "not an allow-listed legend style field"})
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
                    if field in _SERIES_FIELDS:
                        clean[field] = item
                    else:
                        rejected.append({"path": f"series.{series_id}.{field}", "reason": "not an allow-listed series style field"})
                if clean:
                    clean_series[str(series_id)] = clean
            if clean_series:
                accepted[key] = clean_series
        elif key == "matrix":
            if not isinstance(value, dict):
                rejected.append({"path": key, "reason": "matrix must be an object"})
                continue
            clean = {}
            for field, item in value.items():
                if field in _MATRIX_FIELDS:
                    clean[field] = item
                else:
                    rejected.append({"path": f"matrix.{field}", "reason": "not an allow-listed matrix style field"})
            if clean:
                accepted[key] = clean
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
    sources are filtered through the same narrow visual allow-list; rejected fields are
    returned for audit rather than silently becoming executable instructions.
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
