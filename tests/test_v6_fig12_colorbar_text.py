from __future__ import annotations

from copy import deepcopy
from unittest.mock import Mock, call

import pytest

from benchmarks.aa2195.builders import fig12_builder
from scripts.acceptance_hardening import render_parameter_fingerprint
from scripts.origin_candidate_worker import (
    _effective_builder_route,
    _render_identity_payload,
)


@pytest.fixture(
    params=[
        (0, "PSC", [27.90, 35.55, 41.08, 54.00], (333.0, 82.0, 367.0, 188.0)),
        (1, "UC", [30.20, 37.79, 45.19, 56.90], (720.0, 82.0, 754.0, 188.0)),
        (2, "TR", [45.70, 49.77, 60.17, 67.20], (520.0, 358.0, 554.0, 470.0)),
    ],
    ids=["PSC", "UC", "TR"],
)
def colorbar_case(request, monkeypatch):
    panel_index, panel_name, levels, bbox = request.param
    panel = {
        "name": panel_name,
        "levels": levels,
        "matrix": [[27.9, 35.55], [41.08, 54.0]],
        "mechanisms": [(292, 0.44, "GF")],
    }
    original_panel = deepcopy(panel)
    matrix = panel["matrix"]
    label_sizes = {"colorbar_title": 10.0, "colorbar_tick": 8.0}
    layer = object()
    draw_rectangle = Mock(return_value={"attach": 2})
    add_label = Mock(return_value=True)
    monkeypatch.setattr(fig12_builder, "_draw_page_rectangle", draw_rectangle)
    monkeypatch.setattr(fig12_builder, "_add_page_label", add_label)
    contracts = {}
    expected_names = []
    inventory = fig12_builder._add_colorbar_overlay(
        layer, panel, panel_index, bbox, label_sizes, contracts, expected_names
    )
    assert panel == original_panel
    assert panel["matrix"] is matrix
    assert panel["levels"] is levels
    assert label_sizes == {"colorbar_title": 10.0, "colorbar_tick": 8.0}
    return {
        "panel_index": panel_index,
        "panel": panel,
        "bbox": bbox,
        "layer": layer,
        "draw_rectangle": draw_rectangle,
        "add_label": add_label,
        "contracts": contracts,
        "expected_names": expected_names,
        "inventory": inventory,
    }


def test_colorbar_moves_only_title_and_tick_source_y(colorbar_case):
    case = colorbar_case
    panel_index = case["panel_index"]
    panel = case["panel"]
    x0, y0, x1, y1 = case["bbox"]
    segment_height = (y1 - y0) / 3.0
    prefix = f"fig12_cb_{'abc'[panel_index]}"
    colors = ["#fcbf6e", "#b1df89", "#c6dfec"]
    box_records = [
        {
            "name": f"{prefix}_b{index + 1}",
            "bbox": (
                x0,
                y0 + index * segment_height,
                x1,
                y0 + (index + 1) * segment_height,
            ),
            "color": color,
        }
        for index, color in enumerate(colors)
    ]
    title_anchor = {
        "name": f"{prefix}_ttl",
        "text": "lnZ",
        "source_x": [338.0, 725.0, 525.0][panel_index],
        "source_y": [55.0, 55.0, 331.0][panel_index],
    }
    tick_values = [f"{value:.2f}" for value in reversed(panel["levels"])]
    tick_anchors = [
        {
            "name": f"{prefix}_k{index + 1}",
            "text": value,
            "source_x": x1 + 10.0,
            "source_y": y0 + index * segment_height - 8.0,
        }
        for index, value in enumerate(tick_values)
    ]
    assert tick_anchors[0]["source_y"] == [74.0, 74.0, 350.0][panel_index]
    assert title_anchor["source_y"] == (y0 - 18.0) - 9.0
    for index, anchor in enumerate(tick_anchors):
        assert anchor["source_y"] == (y0 + index * segment_height + 4.0) - 12.0
    assert case["draw_rectangle"].call_args_list == [
        call(case["layer"], record["name"], record["bbox"], record["color"])
        for record in box_records
    ]
    assert case["add_label"].call_args_list == [
        call(
            case["layer"],
            anchor["name"],
            anchor["text"],
            anchor["source_x"],
            anchor["source_y"],
            size,
        )
        for anchor, size in [(title_anchor, 10.0)]
        + [(anchor, 8.0) for anchor in tick_anchors]
    ]
    assert case["inventory"] == {
        "panel": panel["name"],
        "panel_index": panel_index,
        "bbox": case["bbox"],
        "box_records": box_records,
        "title_object_name": title_anchor["name"],
        "tick_values": tick_values,
        "title_text_anchor": title_anchor,
        "tick_text_anchors": tick_anchors,
    }
    assert case["expected_names"] == [record["name"] for record in box_records] + [
        anchor["name"] for anchor in [title_anchor, *tick_anchors]
    ]
    assert case["contracts"] == {
        **{record["name"]: {"attach": 2} for record in box_records},
        **{
            anchor["name"]: {"attach": 2, "text_contains": anchor["text"]}
            for anchor in [title_anchor, *tick_anchors]
        },
    }


@pytest.mark.parametrize("anchor_kind", ["title", "tick"])
def test_text_anchor_inventory_changes_render_fingerprint(colorbar_case, anchor_kind):
    route = {
        "route": "worksheet_xyz_source_calibrated_three_panel_contour",
        "canvas_size": [805, 590],
        "colorbar_inventory": [colorbar_case["inventory"]],
    }
    previous_route = deepcopy(route)
    inventory = previous_route["colorbar_inventory"][0]
    if anchor_kind == "title":
        inventory["title_text_anchor"]["source_y"] += 9.0
    else:
        for anchor in inventory["tick_text_anchors"]:
            anchor["source_y"] += 12.0
    identities = []
    for candidate_route in (route, previous_route):
        effective = _effective_builder_route({"builder_route": candidate_route})
        assert effective["colorbar_inventory"] == candidate_route["colorbar_inventory"]
        identities.append(
            render_parameter_fingerprint(
                _render_identity_payload("fig12", effective, "a" * 64, "b" * 64)
            )
        )
    assert identities[0]["fingerprint"] != identities[1]["fingerprint"]
    assert (
        identities[0]["effective_parameter_digest"]
        != identities[1]["effective_parameter_digest"]
    )
