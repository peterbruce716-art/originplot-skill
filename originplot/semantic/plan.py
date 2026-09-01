from __future__ import annotations

from pathlib import Path
from typing import Any

from originplot.core.errors import OriginPlotError
from originplot.spec import FIGURE_SPEC_SCHEMA, resolve_style

from .inspect import inspect_table


def _first(columns: list[dict[str, Any]], role: str) -> str | None:
    return next((str(item["name"]) for item in columns if item.get("role") == role), None)


def _all(columns: list[dict[str, Any]], role: str) -> list[str]:
    return [str(item["name"]) for item in columns if item.get("role") == role]


def build_figurespec(
    path: Path,
    *,
    plot_type: str | None = None,
    sheet: str | None = None,
    mapping: dict[str, str] | None = None,
    profile: str = "standard",
    reference_style: dict[str, Any] | None = None,
    user_style: dict[str, Any] | None = None,
    preset_style: dict[str, Any] | None = None,
) -> dict[str, Any]:
    understanding = inspect_table(path, sheet)
    columns = [dict(item) for item in understanding["columns"]]
    mapping = {key: value for key, value in (mapping or {}).items() if value}
    explicit = bool(mapping)
    selected = str(plot_type or (understanding.get("recommended_plots") or [""])[0]).strip().lower()
    if not selected:
        raise OriginPlotError("E330_SEMANTIC_CONFIRMATION_REQUIRED", "no plot can be recommended safely; provide --plot-type and explicit column mapping")

    if understanding["uncertain"] and not explicit:
        raise OriginPlotError(
            "E330_SEMANTIC_CONFIRMATION_REQUIRED",
            "unresolved numeric columns require explicit mapping: " + ", ".join(understanding["uncertain"]),
        )

    for item in columns:
        if item["name"] in understanding["uncertain"] and explicit:
            item["role"] = "retain"
            item["reason"] = "retained after explicit user mapping"
            item["confidence"] = 1.0

    x = mapping.get("x") or _first(columns, "x")
    y = mapping.get("y") or _first(columns, "y")
    y_columns = [mapping["y"]] if mapping.get("y") else _all(columns, "y")
    y_error = mapping.get("y_error") or _first(columns, "y_error")
    x_error = mapping.get("x_error") or _first(columns, "x_error")
    category = mapping.get("category") or _first(columns, "category")
    group = mapping.get("group") or _first(columns, "group")
    z = mapping.get("z") or _first(columns, "z")

    if selected in {"line", "scatter", "line_scatter", "errorbar"}:
        if not x or not y:
            raise OriginPlotError("E305_DATA_ROLES_MISSING", f"{selected} requires confirmed x and y columns")
        series: dict[str, Any] = {"id": "series_1", "x": x, "y": y}
        if x_error:
            series["x_error"] = x_error
        if y_error:
            series["y_error"] = y_error
        if selected == "errorbar" and not (x_error or y_error):
            raise OriginPlotError("E321_ERROR_MAPPING_REQUIRED", "errorbar requires confirmed x_error or y_error")
        data = {"series": [series]}
    elif selected in {"bar", "grouped_bar", "stacked_bar"}:
        if group:
            raise OriginPlotError(
                "E324_LONG_FORM_BAR_CONFIRMATION_REQUIRED",
                "long-form grouped/stacked bar data requires an explicit FigureSpec with manually confirmed series mapping; automatic planning will not pivot or split group values",
            )
        if not category or not y_columns:
            raise OriginPlotError("E322_CATEGORY_MAPPING_REQUIRED", f"{selected} requires confirmed category and y columns")
        if selected in {"grouped_bar", "stacked_bar"}:
            bar_series = [
                {"id": f"series_{index + 1}", "category": category, "y": y_name}
                for index, y_name in enumerate(y_columns)
            ]
            if y_error and len(bar_series) == 1:
                bar_series[0]["y_error"] = y_error
            data = {"series": bar_series}
        else:
            series = {"id": "series_1", "category": category, "y": y_columns[0]}
            if y_error:
                series["y_error"] = y_error
            data = {"series": [series]}
    elif selected in {"heatmap", "contour"}:
        if not x or not y or not z:
            raise OriginPlotError("E323_MATRIX_MAPPING_REQUIRED", f"{selected} requires confirmed x, y and z columns")
        data = {"matrix": {"x": x, "y": y, "z": z}}
    else:
        raise OriginPlotError("E440_PLOT_FAMILY_NOT_IMPLEMENTED", f"automatic planning is not available for {selected}")

    role_by_name = {item["name"]: item["role"] for item in columns}
    if explicit:
        for role, column in mapping.items():
            if column in role_by_name and role in {"x", "y", "x_error", "y_error", "z", "category", "group", "label"}:
                role_by_name[column] = role
        for item in columns:
            item["role"] = role_by_name[item["name"]]

    style_result = resolve_style(
        defaults={"legend": {"visible": True, "frame": False}},
        preset=preset_style,
        reference=reference_style,
        user=user_style,
    )

    return {
        "schema": FIGURE_SPEC_SCHEMA,
        "source": {
            "file": str(path.resolve()),
            "sheet": sheet,
            "hash": understanding["source"]["hash"],
        },
        "data": data,
        "figure": {
            "id": path.stem,
            "type": selected,
            "x_axis": {"title": x or category or "X"},
            "y_axis": {"title": y or "Y"},
        },
        "style": style_result["style"],
        "style_audit": {
            "precedence": "user > confirmed_reference > preset > default",
            "sources": style_result["sources"],
            "rejected": style_result["rejected"],
        },
        "layout": {"page": {"width_cm": 18.0, "height_cm": 12.0}},
        "verification": {"profile": profile, "require_reopen": True, "require_binding_readback": True, "require_origin_export": True},
        "semantic_confirmation": {
            "mode": "explicit_mapping" if explicit else "high_confidence_auto",
            "columns": columns,
            "matched_presets": understanding.get("matched_presets") or [],
        },
    }
