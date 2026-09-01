from __future__ import annotations

from abc import ABC, abstractmethod

from originplot.operation_plan import OperationPlan
from originplot.spec.models import FigureSpec


class FigureBuilder(ABC):
    plot_types: tuple[str, ...] = ()

    def supports(self, plot_type: str) -> bool:
        return plot_type in self.plot_types

    @abstractmethod
    def validate(self, spec: FigureSpec) -> None:
        raise NotImplementedError

    @abstractmethod
    def compile(self, spec: FigureSpec, *, layer: int = 0) -> OperationPlan:
        raise NotImplementedError

    def capabilities(self) -> dict[str, object]:
        return {"plot_types": list(self.plot_types), "origin_independent_compile": True}
