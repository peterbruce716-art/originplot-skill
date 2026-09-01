from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adapters.inspection.adapter import origin_graph_pages


def origin_font_size(points: float) -> float:
    return max(5.0, min(float(points), 18.0))


def page_dot_command(
    width_inches: float,
    height_inches: float,
    resx_dpi: float,
    resy_dpi: float,
) -> str:
    width_inches_value = float(width_inches)
    height_inches_value = float(height_inches)
    resx_value = float(resx_dpi)
    resy_value = float(resy_dpi)
    if (
        width_inches_value <= 0.0
        or height_inches_value <= 0.0
        or resx_value <= 0.0
        or resy_value <= 0.0
    ):
        raise ValueError(
            "E540_PAGE_UNIT_SCALE_MISMATCH: page dots require positive physical inches and page resolution"
        )
    width_dots = round(width_inches_value * resx_value)
    height_dots = round(height_inches_value * resy_value)
    return (
        f"page.width={width_dots}; page.height={height_dots}; "
        "page.emo=0; page.autoSize=2;"
    )


def page_percent_layer_command(frame: tuple[float, float, float, float]) -> str:
    left, top, width, height = (float(value) for value in frame)
    if (
        left < 0.0
        or top < 0.0
        or width <= 0.0
        or height <= 0.0
        or left + width > 100.0
        or top + height > 100.0
    ):
        raise ValueError(
            "E541_LAYER_UNIT_SCALE_MISMATCH: layer.unit=1 page-percent frame must stay within 0..100"
        )
    return (
        "layer.unit=1; "
        f"layer.left={left:g}; layer.top={top:g}; "
        f"layer.width={width:g}; layer.height={height:g};"
    )


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def page_name(page: Any) -> str:
    return str(getattr(page, "lname", "") or getattr(page, "name", ""))


def find_graph(op: Any, name: str) -> Any | None:
    for page in origin_graph_pages(op):
        if page_name(page) == name or str(getattr(page, "name", "")) == name:
            return page
    return None


def remove_default_labels(layer: Any) -> None:
    for command in [
        "legend -r;",
        "label -r legend;",
        "label -r xb;",
        "label -r xt;",
        "label -r yl;",
        "label -r yr;",
    ]:
        try:
            layer.lt_exec(command)
        except Exception:
            pass


def disable_speed_mode(layer_or_page: Any) -> None:
    commands = [
        "page.speedMode=0;",
        "layer.speedMode=0;",
        "speedmode index:=page sm:=off;",
        "speedmode index:=layer sm:=off;",
        "layer.speed.matrix=0; layer.speed.wks=0; @LFM=0;",
        "doc -uw;",
    ]
    for command in commands:
        try:
            layer_or_page.lt_exec(command)
        except Exception:
            pass


def fit_page_to_window(page: Any) -> dict[str, str]:
    """Fit the graph page to its editable Origin window without changing page geometry."""
    command = "win -z0;"
    page.lt_exec(command)
    return {
        "status": "applied",
        "command": command,
        "scope": "origin_edit_view_only",
    }


def create_hidden_graph_page(op: Any, *, lname: str, template: str) -> Any:
    """Create a graph page hidden first so object-by-object styling does not flash."""
    page = op.new_graph(lname=lname, template=template, hidden=True)
    try:
        page.show = False
    except Exception:
        pass
    return page


def reveal_graph_page(page: Any) -> dict[str, bool | str]:
    """Reveal a graph page only after styling is complete."""
    evidence: dict[str, bool | str] = {
        "status": "applied",
        "graph_page_created_hidden": True,
        "revealed_after_styling": False,
    }
    try:
        page.show = True
        evidence["revealed_after_styling"] = True
    except Exception:
        try:
            page.activate()
            evidence["revealed_after_styling"] = True
        except Exception:
            pass
    return evidence


def axisless_layer_command() -> str:
    return (
        "layer.x.showAxes=0; layer.y.showAxes=0; "
        "layer.x.showLabels=0; layer.y.showLabels=0; "
        "layer.x.ticks=0; layer.y.ticks=0; "
        "layer.x.showGrids=0; layer.y.showGrids=0; "
        "layer.x.opposite=0; layer.y.opposite=0; "
        "layer.x.showopposite=0; layer.y.showopposite=0; "
        "layer.x.arrow.show=0; layer.y.arrow.show=0; "
        "legend -r; label -r legend; label -r xb; label -r xt; label -r yl; label -r yr;"
    )
