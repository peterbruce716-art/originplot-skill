from __future__ import annotations

from unittest.mock import patch

import pytest

from benchmarks.aa2195.builders import session


class AttachFailureOrigin:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def set_show(self, value: bool) -> None:
        self.calls.append(f"set_show:{value}")

    def attach(self) -> None:
        self.calls.append("attach")
        raise RuntimeError("attach failed")

    def detach(self) -> None:
        self.calls.append("detach")
        raise AssertionError("detach must not run after a failed attach")


def test_attach_failure_preserves_original_error_without_detach() -> None:
    process = {
        "pid": 16900,
        "visible": True,
        "command_line": "C:/program/origin2022/Origin64.exe",
    }
    origin = AttachFailureOrigin()

    with (
        patch.object(session, "is_administrator_python", return_value=True),
        patch.object(session, "origin_process_inventory", return_value=[process]),
    ):
        with pytest.raises(RuntimeError, match="attach failed"):
            with session.origin_session(origin, attach_existing_authorized=True):
                pass

    assert origin.calls == ["set_show:True", "attach"]
