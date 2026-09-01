"""Compatibility checks for v6 execution contracts."""

from __future__ import annotations

from .capability import validate_capability_subset


class CapabilityMismatchError(RuntimeError):
    """Raised when a producer requires unsupported adapter operations."""



def ensure_supported(required, supported) -> None:
    """Ensure every required operation is executable."""

    missing = validate_capability_subset(required, supported)
    if missing:
        raise CapabilityMismatchError(
            "Unsupported operations: " + ", ".join(sorted(missing))
        )
