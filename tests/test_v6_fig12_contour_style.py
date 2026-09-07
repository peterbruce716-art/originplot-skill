from __future__ import annotations

import inspect
import re

from benchmarks.aa2195.builders import fig12_builder
from benchmarks.aa2195.builders.fig12_builder import (
    FIG12_CONTOUR_LINE_COLOR,
    FIG12_CONTOUR_LINE_SLOTS,
    FIG12_CONTOUR_LINE_WIDTH,
    _apply_contour_line_style,
)
from benchmarks.aa2195.builders.geometry import fig12_panels


class _RecordingLayer:
    """Captures LabTalk sent to a layer so the emitted script can be asserted."""

    def __init__(self) -> None:
        self.commands: list[str] = []

    def lt_exec(self, command: str) -> None:
        self.commands.append(command)


def _script(show_lines: bool) -> str:
    layer = _RecordingLayer()
    _apply_contour_line_style(layer, show_lines=show_lines)
    assert len(layer.commands) == 1, "styling must be one committed block"
    return layer.commands[0]


def test_every_declared_level_is_styled() -> None:
    # Each Fig12 panel declares four z-levels. Styling only three left the
    # fourth contour line at Origin's default black.
    script = _script(show_lines=True)
    red, green, blue = FIG12_CONTOUR_LINE_COLOR
    for index in range(1, FIG12_CONTOUR_LINE_SLOTS + 1):
        assert f"layer.cmap.lineColor{index}=color({red},{green},{blue})" in script
        assert f"layer.cmap.lineWidth{index}={FIG12_CONTOUR_LINE_WIDTH:g}" in script
    # and no slot beyond the declared count
    assert f"lineColor{FIG12_CONTOUR_LINE_SLOTS + 1}" not in script


def test_slot_count_matches_the_declared_panel_levels() -> None:
    # The styling loop must cover every level the panels declare, or the
    # unstyled ones fall back to Origin's default black.
    levels = {len(panel["levels"]) for panel in fig12_panels()}
    assert levels == {FIG12_CONTOUR_LINE_SLOTS}, (
        f"panels declare {levels} z-levels but "
        f"{FIG12_CONTOUR_LINE_SLOTS} line slots are styled"
    )


def test_hidden_request_never_enables_the_lines() -> None:
    # The regression: enabling then disabling left the export dependent on
    # whether the trailing command committed.
    script = _script(show_lines=False)
    assert "layer.cmap.showLines(0)" in script
    assert "showLines(1)" not in script


def test_visible_request_enables_the_lines() -> None:
    script = _script(show_lines=True)
    assert "layer.cmap.showLines(1)" in script
    assert "showLines(0)" not in script


def test_visibility_is_committed_in_the_same_block() -> None:
    for show in (True, False):
        script = _script(show_lines=show)
        show_at = script.index("showLines(")
        commit_at = script.index("updateScale()")
        assert show_at < commit_at, "visibility must be set before the commit"


def test_overlay_route_requests_hidden_lines() -> None:
    # Pin the call site: the path-overlay route must ask for lines-off, since
    # it draws its own type-34 boundary and must not double it.
    source = inspect.getsource(fig12_builder)
    calls = re.findall(r"_apply_contour_line_style\((.*?)\)\n", source, re.S)
    call_sites = [c for c in calls if "def " not in c]
    assert call_sites, "no call site found"
    assert any(
        "show_lines=not path_overlays_enabled" in c.replace("\n", " ")
        for c in call_sites
    ), call_sites
