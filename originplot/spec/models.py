from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

FIGURE_SPEC_SCHEMA = "originplot.figurespec.v6"


@dataclass(frozen=True)
class FigureSpec:
    """Validated v6 figure description.

    Builders consume this object but never mutate or reinterpret source-column roles.
    """

    source_path: Path
    source_hash: str
    sheet: str | None
    data: dict[str, Any]
    figure: dict[str, Any]
    style: dict[str, Any]
    layout: dict[str, Any]
    verification: dict[str, Any]
    raw: dict[str, Any]

    @property
    def plot_type(self) -> str:
        return str(self.figure.get("type") or "").strip().lower()

    @property
    def figure_id(self) -> str:
        return str(self.figure.get("id") or self.source_path.stem or "figure")

    @property
    def profile(self) -> str:
        return str(self.verification.get("profile") or "standard")

    def to_dict(self) -> dict[str, Any]:
        payload = dict(self.raw)
        payload["schema"] = FIGURE_SPEC_SCHEMA
        source = dict(payload.get("source") or {})
        source["file"] = str(self.source_path)
        source["hash"] = self.source_hash
        if self.sheet:
            source["sheet"] = self.sheet
        payload["source"] = source
        return payload
