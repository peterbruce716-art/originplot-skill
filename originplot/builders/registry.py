from __future__ import annotations

from originplot.core.errors import OriginPlotError
from originplot.operation_plan import OperationPlan
from originplot.spec.models import FigureSpec

from .bar import BarBuilder
from .base import FigureBuilder
from .composite import MultiPanelBuilder
from .matrix import MatrixBuilder
from .xy import XYBuilder

_BUILDERS: dict[str, FigureBuilder] = {}


def register_builder(builder: FigureBuilder) -> None:
    for plot_type in builder.plot_types:
        if not plot_type:
            raise ValueError("builder plot type must be nonempty")
        if plot_type in _BUILDERS:
            raise ValueError(f"builder already registered for plot type: {plot_type}")
        _BUILDERS[plot_type] = builder


def resolve_builder(plot_type: str) -> FigureBuilder:
    key = str(plot_type or "").strip().lower()
    try:
        return _BUILDERS[key]
    except KeyError as exc:
        raise OriginPlotError("E440_PLOT_FAMILY_NOT_IMPLEMENTED", f"unsupported plot type: {key or '<empty>'}") from exc


def list_builders() -> tuple[str, ...]:
    return tuple(sorted(_BUILDERS))


def compile_figure(spec: FigureSpec) -> OperationPlan:
    return resolve_builder(spec.plot_type).compile(spec)


for _builder in (XYBuilder(), BarBuilder(), MatrixBuilder(), MultiPanelBuilder()):
    register_builder(_builder)
