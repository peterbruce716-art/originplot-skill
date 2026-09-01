"""Canonical Operation registry for OriginPlot v6 execution contracts.

Builders and adapters should reference this registry instead of inventing
operation names. Unknown operations are intentionally rejected by validators.
"""

from enum import Enum


class OperationName(str, Enum):
    CREATE_WORKBOOK = "create_workbook"
    WRITE_COLUMNS = "write_columns"
    CREATE_GRAPH = "create_graph"
    ADD_PLOT = "add_plot"
    SET_AXIS_TITLE = "set_axis_title"
    SET_AXIS_UNIT = "set_axis_unit"
    SET_SERIES_STYLE = "set_series_style"
    SET_LEGEND = "set_legend"
    SAVE_PROJECT = "save_project"
    DETACH = "detach"
    REOPEN = "reopen"
    READBACK = "readback"
    EXPORT = "export"


SUPPORTED_OPERATIONS = frozenset(item.value for item in OperationName)


def is_supported_operation(name: str) -> bool:
    return name in SUPPORTED_OPERATIONS
