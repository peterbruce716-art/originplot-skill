from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from benchmarks.aa2195.builders.common_origin_utils import (
    MAX_EXPORT_SUPERSAMPLE,
    export_page_png,
    resolve_export_supersample,
)
from scripts.origin_candidate_worker import _effective_builder_route
from scripts.acceptance_hardening import render_parameter_fingerprint


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


@pytest.mark.parametrize("factor", [2, 3, 4])
def test_successful_supersample_has_exact_canvas_and_nonblank_pixels(
    tmp_path, factor
) -> None:
    class Page:
        width = None

        def save_fig(self, path, *, type, replace, width) -> None:
            self.width = width
            image = Image.new("RGB", (width, width * 4 // 5), "white")
            ImageDraw.Draw(image).line(
                (0, 0, width - 1, width * 4 // 5 - 1), fill="black", width=3
            )
            image.save(path)

    page = Page()
    output = tmp_path / "export.png"
    record = export_page_png(page, output, [100, 80], supersample=factor)
    assert page.width == 100 * factor
    assert record["rendered_size"] == [100 * factor, 80 * factor]
    assert record["resampled"] is True
    assert record["resampled_to"] == [100, 80]
    with Image.open(output) as image:
        assert image.size == (100, 80)
        assert image.convert("L").getextrema()[0] < 255


def test_supersample_produces_a_distinct_render_fingerprint() -> None:
    fingerprints = []
    for factor in (1, 3):
        route = _effective_builder_route(
            {
                "builder_route": {
                    "route": "demo",
                    "canvas_size": [100, 80],
                    "export_supersample": factor,
                }
            }
        )
        fingerprints.append(
            render_parameter_fingerprint({"effective_builder_route": route})[
                "fingerprint"
            ]
        )
    assert fingerprints[0] != fingerprints[1]


@pytest.mark.parametrize(
    ("native_size", "canvas_size", "factor"),
    [
        ((299, 240), [100, 80], 3),
        ((301, 240), [100, 80], 3),
        ((300, 238), [100, 80], 3),
        ((300, 242), [100, 80], 3),
        ((300, 300), [100, 80], 3),
        ((299, 240), [100], 3),
        ((301, 240), [100], 3),
        ((200, 158), [100, 80], 2),
        ((200, 162), [100, 80], 2),
        ((399, 320), [100, 80], 4),
        ((401, 320), [100, 80], 4),
        ((400, 317), [100, 80], 4),
        ((400, 323), [100, 80], 4),
    ],
)
def test_supersample_rejects_native_geometry_before_resize_or_save(
    tmp_path, monkeypatch, native_size, canvas_size, factor
) -> None:
    operations = []
    original_resize = Image.Image.resize
    original_save = Image.Image.save

    def track_resize(image, *args, **kwargs):
        operations.append(("resize", image.size))
        return original_resize(image, *args, **kwargs)

    def track_save(image, *args, **kwargs):
        operations.append(("save", image.size))
        return original_save(image, *args, **kwargs)

    monkeypatch.setattr(Image.Image, "resize", track_resize)
    monkeypatch.setattr(Image.Image, "save", track_save)

    class Page:
        def save_fig(self, path, *, type, replace, width) -> None:
            assert width == 100 * factor
            Image.new("RGB", native_size, "white").save(path)

    output = tmp_path / "wrong_geometry.png"
    with pytest.raises(ValueError, match="native raster"):
        export_page_png(Page(), output, canvas_size, supersample=factor)

    assert operations == [("save", native_size)]
    with Image.open(output) as image:
        assert image.size == native_size


@pytest.mark.parametrize(
    ("factor", "height_rounding"),
    [(2, -1), (2, 1), (3, -1), (3, 1), (4, -1), (4, 1), (4, -2), (4, 2)],
)
def test_supersample_tolerates_half_target_pixel_height_rounding(
    tmp_path, factor, height_rounding
) -> None:
    native_size = (100 * factor, 80 * factor + height_rounding)

    class Page:
        def save_fig(self, path, *, type, replace, width) -> None:
            assert width == native_size[0]
            Image.new("RGB", native_size, "white").save(path)

    output = tmp_path / "rounded_height.png"
    record = export_page_png(Page(), output, [100, 80], supersample=factor)

    assert record == {
        "supersample": factor,
        "export_width": 100 * factor,
        "rendered_size": list(native_size),
        "resampled": True,
        "resampled_to": [100, 80],
    }
    with Image.open(output) as image:
        assert image.size == (100, 80)


@pytest.mark.parametrize("canvas_size", [[100], [100, 0], [100, -1]])
@pytest.mark.parametrize(
    "native_height, expected_height", [(239, 80), (242, 81), (1, 1)]
)
def test_supersample_infers_height_from_native_aspect(
    tmp_path, canvas_size, native_height, expected_height
) -> None:
    class Page:
        def save_fig(self, path, *, type, replace, width) -> None:
            assert width == 300
            Image.new("RGB", (width, native_height), "white").save(path)

    output = tmp_path / "inferred_height.png"
    record = export_page_png(Page(), output, canvas_size, supersample=3)

    assert record["rendered_size"] == [300, native_height]
    assert record["resampled_to"] == [100, expected_height]
    with Image.open(output) as image:
        assert image.size == (100, expected_height)


@pytest.mark.parametrize("options", [{}, {"supersample": 1}])
def test_factor_one_preserves_direct_export_without_geometry_inspection(
    tmp_path, monkeypatch, options
) -> None:
    calls = []

    class Page:
        def save_fig(self, *args, **kwargs) -> None:
            calls.append((args, kwargs))

    def reject_inspection(*args, **kwargs):
        raise AssertionError("Factor one must not inspect or resample the raster")

    monkeypatch.setattr(Image, "open", reject_inspection)
    monkeypatch.setattr(Image.Image, "resize", reject_inspection)
    monkeypatch.setattr(Image.Image, "save", reject_inspection)
    output = tmp_path / "direct.png"
    record = export_page_png(Page(), output, [100, 80], **options)

    assert calls == [((str(output),), {"type": "png", "replace": True, "width": 100})]
    assert record == {"supersample": 1, "export_width": 100, "resampled": False}
