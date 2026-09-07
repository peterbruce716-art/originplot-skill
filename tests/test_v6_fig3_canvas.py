from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from benchmarks.aa2195.builders.fig3_builder import _canvas_layout
from scripts import extract_aa2195_fresh_source_bundle as extractor
from scripts.origin_candidate_worker import (
    _render_identity_payload,
    render_parameter_fingerprint,
)


def _panels() -> list[dict]:
    return [
        {
            "name": name,
            "frame_percent": list(config["frame_percent"]),
            "series": {"test": {"x": [0.0, 1.0], "y": [0.0, 100.0]}},
        }
        for name, config in extractor.FIG3_PANELS.items()
    ]


def _extraction(mode: str = "full") -> dict:
    if mode == "legacy":
        return {"canvas_size": [1245, 900]}
    return {
        "fig3_canvas_mode": "full",
        "canvas_size": [1245, 950],
        "pdf_clip_points": [95.0, 48.3333333333, 510.0, 365.0],
    }


def _render(monkeypatch, figure: str, mode: str | None = None) -> tuple[dict, Mock]:
    width, height = extractor.PDF_CLIPS[figure]["size"]
    if figure == "fig3" and mode == "full":
        height = 950
    pixmap = SimpleNamespace(width=width, height=height, save=Mock())
    page = SimpleNamespace(get_pixmap=Mock(return_value=pixmap))
    document = [page] * 12
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: None)
    kwargs = {} if mode is None else {"fig3_canvas_mode": mode}
    record = extractor._render_crop(document, figure, Path("unused.png"), **kwargs)
    return record, page.get_pixmap


def test_legacy_crop_and_metadata_are_unchanged(monkeypatch) -> None:
    original = deepcopy(extractor.PDF_CLIPS)
    implicit, _ = _render(monkeypatch, "fig3")
    explicit, _ = _render(monkeypatch, "fig3", "legacy")
    assert (
        implicit
        == explicit
        == {
            "page_one_based": 5,
            "pdf_clip_points": [95.0, 48.3333333333, 510.0, 348.3333333333],
            "render_scale": 3.0,
            "canvas_size": [1245, 900],
            "canonicalization": "none",
        }
    )
    assert extractor.PDF_CLIPS == original


def test_full_crop_contains_bottom_titles_but_excludes_caption(monkeypatch) -> None:
    original = deepcopy(extractor.PDF_CLIPS)
    record, render = _render(monkeypatch, "fig3", "full")
    clip = render.call_args.kwargs["clip"]
    assert record["canvas_size"] == [1245, 950]
    assert record["fig3_canvas_mode"] == "full"
    assert clip.y1 > 360.6241760253906
    assert clip.y1 < 366.584
    assert tuple(clip) == (95.0, 48.3333333333, 510.0, 365.0)
    assert extractor.PDF_CLIPS == original


@pytest.mark.parametrize("figure", ["fig14", "fig15", "fig16"])
def test_full_option_does_not_change_other_crops(monkeypatch, figure: str) -> None:
    legacy, _ = _render(monkeypatch, figure)
    full, _ = _render(monkeypatch, figure, "full")
    assert legacy == full


def test_legacy_layout_and_route_are_unchanged() -> None:
    panels = _panels()
    canvas, inches, rendered, route = _canvas_layout(panels, _extraction("legacy"))
    assert canvas == (1245, 900)
    assert inches == (12.45, 9.0)
    assert rendered is panels
    assert route == "worksheet_backed_source_calibrated_four_layer_line"


def test_full_layout_preserves_physical_axes_and_source_data() -> None:
    panels = _panels()
    original = deepcopy(panels)
    canvas, inches, rendered, route = _canvas_layout(panels, _extraction())
    assert canvas == (1245, 950)
    assert inches == (12.45, 9.5)
    assert route.endswith("_full_canvas")
    assert panels == original
    for source, output in zip(panels, rendered):
        assert output is not source
        assert output["series"] is source["series"]
        for coordinate, old_extent, new_extent in (
            (0, 1245, 1245),
            (1, 900, 950),
            (2, 1245, 1245),
            (3, 900, 950),
        ):
            assert output["frame_percent"][coordinate] * new_extent == pytest.approx(
                source["frame_percent"][coordinate] * old_extent
            )


@pytest.mark.parametrize("requested", ["legacy", "invalid", True, 3])
def test_candidate_cannot_override_source_canvas(requested) -> None:
    with pytest.raises(ValueError, match="must match"):
        _canvas_layout(_panels(), _extraction(), requested)


def test_full_candidate_rejects_legacy_source() -> None:
    with pytest.raises(ValueError, match="must match"):
        _canvas_layout(_panels(), _extraction("legacy"), "full")


@pytest.mark.parametrize(
    "change",
    [
        {"canvas_size": [1245, 900]},
        {"pdf_clip_points": [95.0, 48.3333333333, 510.0, 348.3333333333]},
        {"fig3_canvas_mode": "invalid"},
    ],
)
def test_inconsistent_source_geometry_fails_closed(change: dict) -> None:
    with pytest.raises(ValueError):
        _canvas_layout(_panels(), {**_extraction(), **change})


def test_full_canvas_changes_render_identity_without_data_changes() -> None:
    fingerprints = []
    for mode in ("legacy", "full"):
        canvas, inches, _, route = _canvas_layout(_panels(), _extraction(mode))
        identity = _render_identity_payload(
            figure="fig3",
            route={"route": route, "canvas_size": canvas, "page_size_inches": inches},
            source_crop_sha256="same-source-crop",
            fresh_data_sha256="same-data",
        )
        fingerprints.append(render_parameter_fingerprint(identity))
    assert fingerprints[0] != fingerprints[1]


def test_cli_defaults_to_legacy_and_accepts_explicit_full(monkeypatch) -> None:
    arguments = ["extractor", "--source-pdf", "unused.pdf", "--output-dir", "unused"]
    monkeypatch.setattr("sys.argv", arguments)
    assert extractor._parse_args().fig3_canvas_mode == "legacy"
    monkeypatch.setattr("sys.argv", [*arguments, "--fig3-canvas-mode", "full"])
    assert extractor._parse_args().fig3_canvas_mode == "full"


def test_candidate_can_explicitly_confirm_full_source() -> None:
    assert _canvas_layout(_panels(), _extraction(), "full")[0] == (1245, 950)
