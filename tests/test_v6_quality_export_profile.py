from __future__ import annotations

import json
from pathlib import Path


def test_origin2022_quality_export_profile_keeps_per_figure_choices() -> None:
    root = Path(__file__).resolve().parents[1]
    profile = json.loads(
        (root / "benchmarks/aa2195/examples/origin2022_quality_export.json").read_text(
            encoding="utf-8"
        )
    )
    assert profile == {"fig3": 3, "fig12": 1, "fig14": 1, "fig15": 3, "fig16": 3}
    assert all(type(value) is int and 1 <= value <= 4 for value in profile.values())
