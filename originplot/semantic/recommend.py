from __future__ import annotations

from typing import Any


def recommend_plots(understanding: dict[str, Any]) -> list[str]:
    roles = [str(item.get("role")) for item in understanding.get("columns") or [] if isinstance(item, dict)]
    counts = {role: roles.count(role) for role in set(roles)}
    recommendations: list[str] = []

    if counts.get("x", 0) and counts.get("y", 0) and (counts.get("x_error", 0) or counts.get("y_error", 0)):
        recommendations.append("errorbar")
    if counts.get("x", 0) and counts.get("y", 0):
        recommendations.extend(["line_scatter", "scatter", "line"])
    if counts.get("category", 0) and counts.get("y", 0):
        recommendations.append("grouped_bar" if counts.get("y", 0) > 1 or counts.get("group", 0) else "bar")
    if counts.get("x", 0) and counts.get("y", 0) and counts.get("z", 0):
        recommendations.extend(["heatmap", "contour"])

    ordered: list[str] = []
    for item in recommendations:
        if item not in ordered:
            ordered.append(item)
    return ordered[:3]
