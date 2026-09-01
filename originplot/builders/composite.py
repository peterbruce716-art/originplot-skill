from __future__ import annotations

from originplot.core.errors import OriginPlotError
from originplot.operation_plan import OperationPlan
from originplot.spec.models import FigureSpec

from .base import FigureBuilder


class MultiPanelBuilder(FigureBuilder):
    plot_types = ("multi_panel",)

    def validate(self, spec: FigureSpec) -> None:
        panels = spec.figure.get("panels")
        if not isinstance(panels, list) or len(panels) < 2:
            raise OriginPlotError("E324_PANEL_MAPPING_REQUIRED", "multi_panel requires at least two figure.panels")
        for index, panel in enumerate(panels):
            if not isinstance(panel, dict) or not isinstance(panel.get("figure"), dict) or not panel["figure"].get("type"):
                raise OriginPlotError("E324_PANEL_MAPPING_REQUIRED", f"panel {index} requires figure.type")
            if str(panel["figure"].get("type")).lower() == "multi_panel":
                raise OriginPlotError("E325_NESTED_MULTIPANEL_UNSUPPORTED", "nested multi_panel is not supported in v6.0")

    def compile(self, spec: FigureSpec, *, layer: int = 0) -> OperationPlan:
        self.validate(spec)
        from .registry import resolve_builder

        panels = spec.figure["panels"]
        operations: list[dict[str, object]] = [
            {"op": "create_workbook", "name": f"{spec.figure_id}_Data"},
            {"op": "create_graph", "name": spec.figure_id, "layers": len(panels)},
        ]
        panel_meta: list[dict[str, object]] = []
        for index, panel in enumerate(panels):
            child_figure = dict(panel["figure"])
            child_figure.setdefault("id", f"{spec.figure_id}_{index + 1}")
            child = FigureSpec(
                source_path=spec.source_path,
                source_hash=spec.source_hash,
                sheet=spec.sheet,
                data=dict(panel.get("data") or {}),
                figure=child_figure,
                style=dict(panel.get("style") or spec.style),
                layout=dict(panel.get("layout") or {}),
                verification=spec.verification,
                raw=spec.raw,
            )
            builder = resolve_builder(child.plot_type)
            child_plan = builder.compile(child, layer=index)
            for operation in child_plan.operations:
                if operation.get("op") not in {"create_workbook", "create_graph", "set_page", "export"}:
                    operations.append(dict(operation))
            panel_meta.append({"id": str(panel.get("id") or index + 1), "type": child.plot_type, "layer": index})
        operations.extend(
            [
                {"op": "arrange_panels", "layout": dict(spec.layout.get("panels") or {})},
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
            metadata={"panels": panel_meta, "style": spec.style, "layout": spec.layout},
        )
