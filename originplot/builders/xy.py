from __future__ import annotations

from typing import Any

from originplot.core.errors import OriginPlotError
from originplot.operation_plan import OperationPlan
from originplot.spec.models import FigureSpec

from .base import FigureBuilder


class XYBuilder(FigureBuilder):
    plot_types = ("line", "scatter", "line_scatter", "errorbar")

    def validate(self, spec: FigureSpec) -> None:
        series = spec.data.get("series")
        if not isinstance(series, list) or not series:
            raise OriginPlotError("E320_SERIES_MAPPING_REQUIRED", f"{spec.plot_type} requires data.series")
        for index, item in enumerate(series):
            if not isinstance(item, dict) or not item.get("x") or not item.get("y"):
                raise OriginPlotError("E320_SERIES_MAPPING_REQUIRED", f"series {index} requires x and y columns")
            if item.get("label"):
                raise OriginPlotError(
                    "E324_MAPPING_NOT_EXECUTABLE",
                    f"series {index} label mapping is not executable in the v6 Origin adapter; remove it until native label rendering is implemented",
                )
            if spec.plot_type == "errorbar" and not (item.get("x_error") or item.get("y_error")):
                raise OriginPlotError("E321_ERROR_MAPPING_REQUIRED", f"errorbar series {index} requires x_error or y_error")

    def compile(self, spec: FigureSpec, *, layer: int = 0) -> OperationPlan:
        self.validate(spec)
        axes = {
            "x": dict(spec.figure.get("x_axis") or {}),
            "y": dict(spec.figure.get("y_axis") or {}),
        }
        operations: list[dict[str, Any]] = [
            {"op": "create_workbook", "name": f"{spec.figure_id}_Data"},
            {"op": "create_graph", "name": spec.figure_id, "layers": 1},
        ]
        for index, mapping in enumerate(spec.data["series"]):
            operations.append(
                {
                    "op": "add_xy_plot",
                    "layer": layer,
                    "series_id": str(mapping.get("id") or f"series_{index + 1}"),
                    "kind": spec.plot_type,
                    "mapping": {key: mapping.get(key) for key in ("x", "y", "x_error", "y_error") if mapping.get(key)},
                    "style": dict((spec.style.get("series") or {}).get(str(mapping.get("id") or f"series_{index + 1}"), {})),
                }
            )
        operations.extend(
            [
                {"op": "set_axes", "layer": layer, "axes": axes},
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
