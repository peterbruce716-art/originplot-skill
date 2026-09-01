from __future__ import annotations

from typing import Any


def _binding(plot: Any) -> str:
    value = getattr(plot, "lt_range", "")
    if callable(value):
        value = value()
    return str(value or "").strip()


def inspect_reopened_project(op: Any, *, expected_figure_id: str, expected_workbook: str) -> dict[str, Any]:
    pages = list(op.pages("g"))
    page = next(
        (
            item
            for item in pages
            if str(getattr(item, "lname", "")) == expected_figure_id
            or str(getattr(item, "name", "")) == expected_figure_id
        ),
        None,
    )
    if page is None:
        raise RuntimeError("E503_GRAPH_PAGE_MISSING: reopened graph page is absent")
    layers: list[dict[str, Any]] = []
    all_bindings: list[str] = []
    plot_count = 0
    for layer_index in range(len(page)):
        layer = page[layer_index]
        plots = list(layer.plot_list())
        details = []
        for index, plot in enumerate(plots):
            binding = _binding(plot)
            all_bindings.append(binding)
            details.append({"plot_index": index, "binding": binding, "plot_type_code": getattr(plot, "type", None)})
        plot_count += len(plots)
        layers.append({"layer_index": layer_index, "plot_count": len(plots), "plots": details})
    if plot_count == 0:
        raise RuntimeError("E504_PLOT_MISSING: reopened graph has no editable plot")
    binding_ok = all(binding and f"[{expected_workbook}]" in binding and "!" in binding for binding in all_bindings)
    if not binding_ok:
        raise RuntimeError("E505_WORKSHEET_BINDING_MISSING: one or more plots lost direct worksheet binding")
    return {
        "graph_pages": len(pages),
        "layers": layers,
        "plot_count": plot_count,
        "bindings": all_bindings,
        "worksheet_binding_ok": True,
    }
