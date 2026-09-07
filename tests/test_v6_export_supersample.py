from __future__ import annotations

import pytest

from benchmarks.aa2195.builders.common_origin_utils import (
    MAX_EXPORT_SUPERSAMPLE,
    export_page_png,
    resolve_export_supersample,
)
from scripts.origin_candidate_worker import _effective_builder_route


def test_default_is_one_so_promoted_exports_are_unchanged() -> None:
    assert resolve_export_supersample(None) == 1
    assert resolve_export_supersample({}) == 1
    assert resolve_export_supersample({"export_supersample": 1}) == 1


def test_valid_factors_are_accepted() -> None:
    assert resolve_export_supersample({"export_supersample": 3}) == 3
    assert resolve_export_supersample({"export_supersample": "2"}) == 2


@pytest.mark.parametrize(
    "bad",
    [
        0,
        -1,
        MAX_EXPORT_SUPERSAMPLE + 1,
        "x",
        None,
        1.5j,
        1.0,
        1.5,
        True,
        False,
        "2.0",
    ],
)
def test_invalid_factors_fail_closed(bad: object) -> None:
    with pytest.raises(ValueError):
        resolve_export_supersample({"export_supersample": bad})


def test_supersample_reaches_the_render_identity_route() -> None:
    # _effective_builder_route is an allowlist. A route key missing from it is
    # dropped silently, which briefly let a supersampled export carry the same
    # fingerprint as a 1:1 export.
    route = {
        "route": "demo",
        "canvas_size": [1245, 900],
        "export_supersample": 3,
    }
    effective = _effective_builder_route({"builder_route": route})
    assert effective["export_supersample"] == 3


def test_default_route_carries_no_supersample_key() -> None:
    # Absent key must stay absent so the promoted fingerprint is unchanged.
    effective = _effective_builder_route(
        {"builder_route": {"route": "demo", "canvas_size": [1245, 900]}}
    )
    assert "export_supersample" not in effective


def test_export_helper_rejects_noninteger_factor_before_origin_call(tmp_path) -> None:
    class Page:
        def save_fig(self, *args, **kwargs) -> None:
            raise AssertionError("Origin export must not run for invalid input")

    with pytest.raises(ValueError):
        export_page_png(Page(), tmp_path / "invalid.png", [100, 80], supersample=1.5)
