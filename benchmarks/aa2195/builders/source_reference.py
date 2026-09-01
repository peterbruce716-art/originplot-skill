from __future__ import annotations

from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


FIG12_CANVAS = (805, 590)
FIG12_PAPER_TEXT_BAND = (0, 0, 805, 40)


def canonicalize_fig12_source_crop(source: str | Path, output: str | Path) -> dict[str, Any]:
    """Remove known out-of-figure paper text without changing figure coordinates."""
    source_path = Path(source)
    output_path = Path(output)
    image = Image.open(source_path).convert("RGB")
    if image.size != FIG12_CANVAS:
        raise ValueError(
            f"Fig12 source crop must be {FIG12_CANVAS[0]}x{FIG12_CANVAS[1]}, "
            f"got {image.width}x{image.height}"
        )
    cleaned = image.copy()
    ImageDraw.Draw(cleaned).rectangle(FIG12_PAPER_TEXT_BAND, fill="white")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cleaned.save(output_path)
    return {
        "status": "canonical_source_crop",
        "canvas_size": list(FIG12_CANVAS),
        "excluded_paper_text_band": list(FIG12_PAPER_TEXT_BAND),
        "output": output_path.name,
    }
