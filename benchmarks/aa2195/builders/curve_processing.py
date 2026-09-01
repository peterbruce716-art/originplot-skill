from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import numpy as np


def curve_roughness(values: Sequence[float]) -> float:
    """Return the absolute second-difference sum for a one-dimensional curve."""
    array = np.asarray(values, dtype=float)
    if array.ndim != 1:
        raise ValueError("Curve values must be one-dimensional")
    if not np.isfinite(array).all():
        raise ValueError("Curve values must be finite")
    if array.size < 3:
        return 0.0
    return float(np.abs(np.diff(array, n=2)).sum())


def smooth_digitized_curve(
    x: Sequence[float],
    y: Sequence[float],
    *,
    window: int,
    max_deviation: float,
) -> tuple[list[float], list[float], dict[str, Any]]:
    """Suppress raster stair-steps without moving endpoints or exceeding a data-space bound."""
    x_values = np.asarray(x, dtype=float)
    y_values = np.asarray(y, dtype=float)
    if x_values.ndim != 1 or y_values.ndim != 1:
        raise ValueError("Curve x and y values must be one-dimensional")
    if x_values.size != y_values.size:
        raise ValueError("Curve x and y must contain the same number of points")
    if not np.isfinite(x_values).all() or not np.isfinite(y_values).all():
        raise ValueError("Curve x and y values must be finite")
    if x_values.size > 1 and not np.all(np.diff(x_values) > 0.0):
        raise ValueError("Curve x values must be strictly increasing")
    if isinstance(window, bool) or int(window) != window or int(window) < 3 or int(window) % 2 == 0:
        raise ValueError("Smoothing window must be an odd integer of at least 3")
    if not np.isfinite(max_deviation) or float(max_deviation) < 0.0:
        raise ValueError("Smoothing max_deviation must be finite and non-negative")

    window = int(window)
    max_deviation = float(max_deviation)
    smoothed = y_values.copy()
    radius = window // 2
    applied = bool(y_values.size >= window and max_deviation > 0.0)
    if applied:
        ascending = np.arange(1, radius + 2, dtype=float)
        weights = np.concatenate((ascending, ascending[-2::-1]))
        weights /= weights.sum()
        for index in range(radius, y_values.size - radius):
            candidate = float(np.dot(y_values[index - radius:index + radius + 1], weights))
            delta = float(np.clip(candidate - y_values[index], -max_deviation, max_deviation))
            smoothed[index] = y_values[index] + delta

    if y_values.size:
        smoothed[0] = y_values[0]
        smoothed[-1] = y_values[-1]
    delta = np.abs(smoothed - y_values)
    roughness_before = curve_roughness(y_values)
    roughness_after = curve_roughness(smoothed)
    evidence = {
        "method": "bounded_triangular_raster_stair_step_suppression",
        "point_count": int(y_values.size),
        "window": window,
        "max_deviation": max_deviation,
        "applied": applied,
        "max_abs_delta": float(delta.max()) if delta.size else 0.0,
        "endpoint_preserved": bool(
            y_values.size == 0
            or (smoothed[0] == y_values[0] and smoothed[-1] == y_values[-1])
        ),
        "roughness_before": roughness_before,
        "roughness_after": roughness_after,
        "roughness_ratio": (
            roughness_after / roughness_before if roughness_before > 0.0 else 1.0
        ),
    }
    return x_values.tolist(), smoothed.tolist(), evidence
