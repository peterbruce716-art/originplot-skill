from __future__ import annotations

from originplot.core.errors import OriginPlotError
from originplot.operation_plan import OperationPlan
from originplot.spec.models import FigureSpec

from .base import FigureBuilder


class MatrixBuilder(FigureBuilder):
    plot_types = ("heatmap", "contour")

    def validate(self, spec: FigureSpec) -> None:
        matrix = spec.data.get("matrix")
        if not isinstance(matrix, dict) or not all(matrix.get(key) for key in ("x", "y", "z")):
            raise OriginPlotError("E323_MATRIX_MAPPING_REQUIRED", f"{spec.plot_type} requires data.matrix.x/y/z")

    def compile(self, spec: FigureSpec, *, layer: int = 0) -> OperationPlan:
        self.validate(spec)
        operations = (
            {"op": "create_workbook", "name": f"{spec.figure_id}_Data"},
            {"op": "create_graph", "name": spec.figure_id, "layers": 1},
            {"op": "add_matrix_plot", "layer": layer, "kind": spec.plot_type, "mapping": dict(spec.data["matrix"]), "style": dict(spec.style.get("matrix") or {})},
            {"op": "set_axes", "layer": layer, "axes": {"x": dict(spec.figure.get("x_axis") or {}), "y": dict(spec.figure.get("y_axis") or {})}},
            {"op": "set_legend", "layer": layer, "legend": dict(spec.style.get("legend") or {})},
            {"op": "set_page", "page": dict(spec.layout.get("page") or {})},
            {"op": "export", "formats": ["png", "pdf", "tif"]},
        )
        return OperationPlan(
            figure_id=spec.figure_id,
            plot_type=spec.plot_type,
            source={"path": str(spec.source_path), "sheet": spec.sheet, "hash": spec.source_hash},
            profile=spec.profile,
            operations=operations,
            metadata={"style": spec.style, "layout": spec.layout},
        )
