from __future__ import annotations


class OriginPlotError(RuntimeError):
    """Error with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class ProfileConfigurationError(OriginPlotError):
    pass
