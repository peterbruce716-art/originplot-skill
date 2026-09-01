from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from originplot.spec.io import file_sha256, read_table

COLUMN_ROLES = (
    "x",
    "y",
    "x_error",
    "y_error",
    "z",
    "group",
    "category",
    "label",
    "support",
    "retain",
    "uncertain",
)

_ERROR_RE = re.compile(r"(^|[^a-z])(sd|std|stderr|se|sigma|err|error|uncertainty)([^a-z]|$)", re.I)
_X_RE = re.compile(r"(^|[^a-z])(x|time|strain|temperature|temp|wavelength|wavenumber|2theta|theta|binding energy|potential|voltage|frequency|distance|displacement)([^a-z]|$)", re.I)
_Y_RE = re.compile(r"(^|[^a-z])(y|stress|intensity|current|absorbance|transmittance|heat flow|signal|response|counts|amplitude|fraction)([^a-z]|$)", re.I)
_Z_RE = re.compile(r"(^|[^a-z])(z|height|density|matrix value)([^a-z]|$)", re.I)
_GROUP_RE = re.compile(r"(^|[^a-z])(group|sample|condition|batch|series|treatment)([^a-z]|$)", re.I)
_CATEGORY_RE = re.compile(r"(^|[^a-z])(category|class|type|state)([^a-z]|$)", re.I)
_LABEL_RE = re.compile(r"(^|[^a-z])(label|phase|annotation|name|id)([^a-z]|$)", re.I)
_SUPPORT_RE = re.compile(r"(^|[^a-z])(weight|used|mask|quality|chi|residual|control|flag)([^a-z]|$)", re.I)
_UNIT_RE = re.compile(r"(?:\(([^()]+)\)|\[([^\[\]]+)\])\s*$")


def _numeric_ratio(values: list[Any]) -> float:
    present = [value for value in values if value not in (None, "")]
    if not present:
        return 0.0
    numeric = 0
    for value in present:
        try:
            float(value)
            numeric += 1
        except (TypeError, ValueError):
            pass
    return numeric / len(present)


def _unit(name: str) -> str | None:
    match = _UNIT_RE.search(name)
    if not match:
        return None
    return (match.group(1) or match.group(2) or "").strip() or None


def _classify(name: str, values: list[Any], *, x_already: bool) -> tuple[str, float, str]:
    normalized = re.sub(r"[_\-]+", " ", name).strip()
    numeric = _numeric_ratio(values)
    lower = normalized.lower()

    if _ERROR_RE.search(normalized):
        role = "x_error" if " x" in f" {lower}" or lower.startswith("x") else "y_error"
        return role, 0.95, "column name indicates an uncertainty/error quantity"
    if _GROUP_RE.search(normalized):
        return "group", 0.9, "column name indicates grouping/experimental condition"
    if _CATEGORY_RE.search(normalized):
        return "category", 0.9, "column name indicates a categorical variable"
    if _SUPPORT_RE.search(normalized):
        return "support", 0.9, "column name indicates control/diagnostic data"
    if _LABEL_RE.search(normalized) and numeric < 0.8:
        return "label", 0.85, "column name and values indicate labels/annotations"
    if _Z_RE.search(normalized) and numeric >= 0.8:
        return "z", 0.85, "column name indicates a numeric Z/matrix quantity"
    if _X_RE.search(normalized) and numeric >= 0.8:
        return "x", 0.9, "column name indicates an independent-axis quantity"
    if _Y_RE.search(normalized) and numeric >= 0.8:
        return "y", 0.9, "column name indicates a measured/dependent quantity"
    if lower in {"x", "x1"} and numeric >= 0.8:
        return "x", 0.95, "explicit X column"
    if lower in {"y", "y1"} and numeric >= 0.8:
        return "y", 0.95, "explicit Y column"
    if numeric < 0.2:
        return "retain", 0.7, "non-numeric metadata without a verified visible role"
    return "uncertain", 0.0, "numeric column has no sufficiently reliable semantic role"


def inspect_table(path: Path, sheet: str | None = None) -> dict[str, Any]:
    path = path.resolve()
    rows = read_table(path, sheet)
    headers = list(rows[0]) if rows else []
    columns: list[dict[str, Any]] = []
    x_already = False
    for name in headers:
        values = [row.get(name) for row in rows[:200]]
        role, confidence, reason = _classify(name, values, x_already=x_already)
        if role == "x":
            x_already = True
        columns.append(
            {
                "name": name,
                "role": role,
                "confidence": round(confidence, 3),
                "unit": _unit(name),
                "numeric_ratio": round(_numeric_ratio(values), 3),
                "reason": reason,
            }
        )
    result: dict[str, Any] = {
        "schema": "originplot.data_understanding.v1",
        "source": {
            "path": str(path),
            "sheet": sheet,
            "format": path.suffix.lower().lstrip("."),
            "hash": file_sha256(path),
            "rows": len(rows),
        },
        "columns": columns,
        "uncertain": [item["name"] for item in columns if item["role"] == "uncertain"],
    }
    from .recommend import recommend_plots

    result["recommended_plots"] = recommend_plots(result)
    return result
