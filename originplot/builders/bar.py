from __future__ import annotations

from typing import Any

from originplot.core.errors import OriginPlotError
from originplot.operation_plan import OperationPlan
from originplot.spec.models import FigureSpec

from .base import FigureBuilder


class BarBuilder(FigureBuilder):
    plot_types = ("bar", "grouped_bar", "stacked_bar")

    def validate(self, spec: FigureSpec) -> None:
        series = spec.data.get("series")
        if not isinstance(series, list) or not series:
            raise OriginPlotError("E320_SERIES_MAPPING_REQUIRED", f"{spec.plot_type} requires data.series")
        for index, item in enumerate(series):
            if not isinstance(item, dict) or not item.get("category") or not item.get("y"):
                raise OriginPlotError("E322_CATEGORY_MAPPING_REQUIRED", f"bar series {index} requires category and y columns")
            if item.get("group") or item.get("label"):
                raise OriginPlotError(
                    "E324_MAPPING_NOT_EXECUTABLE",
                    f"bar series {index} group/label mapping is not executable in the v6 Origin adapter; use explicit wide-form series instead",
                )

    def compile(self, spec: FigureSpec, *, layer: int = 0) -> OperationPlan:
        self.validate(spec)
        operations: list[dict[str, Any]] = [
            {"op": "create_workbook", "name": f"{spec.figure_id}_Data"},
            {"op": "create_graph", "name": spec.figure_id, "layers": 1},
        ]
        for index, mapping in enumerate(spec.data["series"]):
            series_id = str(mapping.get("id") or f"series_{index + 1}")
            operations.append(
                {
                    "op": "add_bar_plot",
                    "layer": layer,
                    "series_id": series_id,
                    "kind": spec.plot_type,
                    "mapping": {key: mapping.get(key) for key in ("category", "y", "y_error") if mapping.get(key)},
                    "style": dict((spec.style.get("series") or {}).get(series_id, {})),
                }
            )
        operations.extend(
            [
                {"op": "set_axes", "layer": layer, "axes": {"x": dict(spec.figure.get("x_axis") or {}), "y": dict(spec.figure.get("y_axis") or {})}},
                {"op": "set_legend", "layer": layer, "legend": dict(spec.style.get("legend") or {})},
                {"op": "set_page", "page": dict(spec.layout.get("page") or {})},
                {"op": "export", "formats": ["png", "pdf", "tif"]},
            ]
        )
        return OperationPlan(
            figure_id=spec.figure_id,
            plot_type=spec.plot_type,
            source={"path": str(spec.source_path), "sheet": spec.sheet, "hash": spec.source_hash},
            profile=spec.profile,
            operations=tuple(operations),
            metadata={"style": spec.style, "layout": spec.layout},
        )
