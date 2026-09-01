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

    # Bar auto-planning is deliberately limited to wide-form tables.  A group
    # column plus a single Y is long-form data and would require a pivot/split,
    # which is a scientific data transformation that OriginPlot must not invent.
    if counts.get("category", 0) and counts.get("y", 0) and not counts.get("group", 0):
        recommendations.append("grouped_bar" if counts.get("y", 0) > 1 else "bar")

    if counts.get("x", 0) and counts.get("y", 0) and counts.get("z", 0):
        recommendations.extend(["heatmap", "contour"])

    ordered: list[str] = []
    for item in recommendations:
        if item not in ordered:
            ordered.append(item)
    return ordered[:3]
