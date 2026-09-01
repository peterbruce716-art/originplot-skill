from __future__ import annotations

from pathlib import Path

from originplot.core.profiles import resolve_profile
from originplot.runtime.capabilities import resolve_origin_capabilities
from originplot.runtime.doctor import doctor


def test_admin_policy_is_unchanged_in_v6() -> None:
    assert resolve_profile("quick").require_admin_origin_worker is True
    assert resolve_profile("standard").require_admin_origin_worker is True
    release = resolve_profile("release")
    assert release.require_admin_origin_worker is True
    assert release.require_admin_controller is True


def test_origin_capabilities_are_version_gated() -> None:
    assert resolve_origin_capabilities("OriginPro 2022b")["compatibility"] == "verified_baseline"
    assert resolve_origin_capabilities("2024b")["compatibility"] == "compatible_unverified"
    assert resolve_origin_capabilities("2026")["compatibility"] == "experimental"
    assert resolve_origin_capabilities("2030")["plot_primitives"] == []


def test_capabilities_separate_compile_support_from_live_evidence() -> None:
    capabilities = resolve_origin_capabilities("2022")
    assert "heatmap" in capabilities["compile_primitives"]
    assert "multi_panel" in capabilities["compile_primitives"]
    assert "line" in capabilities["compile_primitives"]
    assert capabilities["live_evidence_primitives"] == []
    assert capabilities["primitive_maturity"]["heatmap"]["live_status"] == "blocked"
    assert capabilities["primitive_maturity"]["heatmap"]["reason"] == "regular_grid_adapter_not_live_verified"
    assert capabilities["primitive_maturity"]["multi_panel"]["live_status"] == "blocked"
    assert capabilities["primitive_maturity"]["multi_panel"]["reason"] == "panel_layout_adapter_not_live_verified"
    assert capabilities["primitive_maturity"]["line"]["live_status"] == "requires_same_run_verification"


def test_known_origin_versions_use_native_v6_capability_profiles() -> None:
    for version in ("2022", "2024", "2026"):
        capabilities = resolve_origin_capabilities(version)
        assert Path(capabilities["profile_path"]).name == f"origin-{version}-v6.json"
        assert capabilities["profile_schema"] == "originplot.capabilities.v6"
        assert capabilities["live_evidence_primitives"] == []


def test_doctor_never_relaxes_admin_requirement() -> None:
    result = doctor("2022")
    assert result["administrator"]["origin_worker_required"] is True
    assert result["administrator"]["release_controller_required"] is True
    assert result["administrator"]["policy_changed_in_v6"] is False
