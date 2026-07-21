from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from originplot.core.errors import OriginPlotError


ROOT = Path(__file__).resolve().parent
FIGURES = ("fig3", "fig12", "fig14", "fig15", "fig16")


def _object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OriginPlotError(
            "E210_AA2195_CONFIG_INVALID", f"cannot load {path.name}: {exc}"
        ) from exc
    if not isinstance(payload, dict):
        raise OriginPlotError("E210_AA2195_CONFIG_INVALID", f"{path.name} must contain an object")
    return payload


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    config = {
        "thresholds": _object(ROOT / "thresholds.json"),
        "templates": _object(ROOT / "templates.json"),
        "routes": _object(ROOT / "routes.json"),
        "source_identities": _object(ROOT / "source_identities.json"),
    }
    for key in ("thresholds", "templates"):
        missing = [figure for figure in FIGURES if figure not in config[key]]
        if missing:
            raise OriginPlotError(
                "E210_AA2195_CONFIG_INVALID", f"{key} missing: {', '.join(missing)}"
            )
    routes = config["routes"]
    required_routes = {"geometry_table_versions", "fig15_frozen_effective_route", "fig16_frozen_effective_route", "fig14_marker_shapes", "fig16_segment_count"}
    missing_routes = sorted(required_routes - set(routes))
    if missing_routes:
        raise OriginPlotError("E210_AA2195_CONFIG_INVALID", f"routes missing: {', '.join(missing_routes)}")
    if sorted(routes["geometry_table_versions"]) != sorted(FIGURES):
        raise OriginPlotError("E210_AA2195_CONFIG_INVALID", "geometry_table_versions must cover all AA2195 figures")
    for key, digest in config["source_identities"].items():
        if not re.fullmatch(r"[0-9a-f]{64}", str(digest)):
            raise OriginPlotError("E210_AA2195_CONFIG_INVALID", f"invalid SHA256 in source_identities: {key}")
    return config
