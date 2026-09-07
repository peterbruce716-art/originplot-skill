from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from adapters.inspection.adapter import origin_graph_pages


def origin_font_size(points: float) -> float:
    return max(5.0, min(float(points), 18.0))


MAX_EXPORT_SUPERSAMPLE = 4


def resolve_export_supersample(params: dict[str, Any] | None) -> int:
    """Return the validated ``export_supersample`` factor, defaulting to 1.

    1 means export straight at the benchmark canvas, which is the promoted
    behaviour and stays byte-identical.
    """
    requested = (params or {}).get("export_supersample", 1)
    if isinstance(requested, bool):
        raise ValueError(
            f"export_supersample requested={requested!r} is not an integer"
        )
    if isinstance(requested, int):
        factor = requested
    elif isinstance(requested, str) and re.fullmatch(r"[+-]?\d+", requested):
        factor = int(requested)
    else:
        raise ValueError(
            f"export_supersample requested={requested!r} is not an integer"
        )
    if factor < 1 or factor > MAX_EXPORT_SUPERSAMPLE:
        raise ValueError(
            f"export_supersample requested={factor} outside allowed range "
            f"[1, {MAX_EXPORT_SUPERSAMPLE}]"
        )
    return factor


def export_page_png(
    page: Any,
    path: str | Path,
    canvas_size: Any,
    supersample: int = 1,
) -> dict[str, Any]:
    """Export a graph page to PNG, optionally rendering above the canvas first.

    The benchmark compares an Origin export against a source crop that PyMuPDF
    rasterised at scale 3.0, so the source carries a soft anti-aliased edge that
    a 1:1 Origin export does not. Rendering at ``supersample`` times the canvas
    and resampling down reproduces that edge physics instead of comparing a
    crisp raster against a smooth one.

    ``supersample=1`` takes exactly the original code path.
    """
    width = int(canvas_size[0])
    height = int(canvas_size[1]) if len(canvas_size) > 1 else 0
    factor = resolve_export_supersample({"export_supersample": supersample})
    if factor == 1:
        page.save_fig(str(path), type="png", replace=True, width=width)
        return {"supersample": 1, "export_width": width, "resampled": False}

    from PIL import Image

    page.save_fig(str(path), type="png", replace=True, width=width * factor)
    with Image.open(path) as rendered:
        rendered.load()
        if height > 0:
            target = (width, height)
        else:
            target = (width, max(1, round(rendered.height * width / rendered.width)))
        resampled = rendered.resize(target, Image.LANCZOS)
    resampled.save(path)
    return {
        "supersample": factor,
        "export_width": width * factor,
        "resampled": True,
        "resampled_to": list(target),
    }


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
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


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


def create_visible_graph_page(op: Any, *, lname: str, template: str) -> Any:
    """Create a graph page in the visible Origin session."""
    page = op.new_graph(lname=lname, template=template, hidden=False)
    try:
        page.show = True
    except Exception:
        pass
    return page


def reveal_graph_page(page: Any) -> dict[str, bool | str]:
    """Keep a graph page visible after styling is complete."""
    evidence: dict[str, bool | str] = {
        "status": "applied",
        "graph_page_created_visible": True,
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
