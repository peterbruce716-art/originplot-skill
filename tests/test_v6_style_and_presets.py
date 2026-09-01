from __future__ import annotations

from originplot.presets import match_presets
from originplot.spec.style import resolve_style


def test_domain_presets_are_semantic_hints_only() -> None:
    assert "stress_strain" in match_presets(["Engineering Strain (%)", "Engineering Stress (MPa)"])
    assert "xrd" in match_presets(["2Theta", "Intensity"])


def test_style_precedence_is_user_reference_preset_default() -> None:
    result = resolve_style(
        defaults={"theme": "publication", "legend": {"visible": True}, "series": {"s1": {"color": "#111111"}}},
        preset={"series": {"s1": {"color": "#222222", "line_width_pt": 1.0}}},
        reference={"legend": {"visible": False}, "series": {"s1": {"color": "#333333"}}},
        user={"series": {"s1": {"color": "#444444"}}},
    )
    assert result["style"]["series"]["s1"]["color"] == "#444444"
    assert result["style"]["series"]["s1"]["line_width_pt"] == 1.0
    assert result["style"]["legend"]["visible"] is False
    assert result["sources"]["series.s1.color"] == "user"


def test_reference_style_cannot_inject_scientific_content() -> None:
    result = resolve_style(
        reference={
            "series": {"s1": {"color": "#333333", "fit": "invented"}},
            "x": [1, 2, 3],
            "phase": "FCC",
            "legend": {"position": "upper-right", "label": "copied paper label"},
        }
    )
    assert result["style"] == {
        "series": {"s1": {"color": "#333333"}},
        "legend": {"position": "upper-right"},
    }
    assert {item["path"] for item in result["rejected"]} >= {"x", "phase", "series.s1.fit", "legend.label"}
