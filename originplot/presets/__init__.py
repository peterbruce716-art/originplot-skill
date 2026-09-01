from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CATALOG_PATH = Path(__file__).with_name("catalog.json")


def load_presets() -> dict[str, Any]:
    return json.loads(_CATALOG_PATH.read_text(encoding="utf-8"))


def match_presets(column_names: list[str]) -> list[str]:
    lowered = " ".join(column_names).lower()
    matches: list[str] = []
    for preset_id, preset in load_presets().items():
        groups = preset.get("match_all") or []
        if groups and all(any(token.lower() in lowered for token in group) for group in groups):
            matches.append(preset_id)
    return matches


__all__ = ["load_presets", "match_presets"]
