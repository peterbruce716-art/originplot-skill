from __future__ import annotations

from pathlib import Path

from scripts.origin_candidate_worker import require_template_search_record


def test_shipped_template_metadata_is_not_current_asset_inspection() -> None:
    root = Path(__file__).resolve().parents[1]
    candidate = root / "benchmarks" / "aa2195" / "examples" / "candidates" / "fig3.json"
    gate = require_template_search_record(
        "fig3", {"template_search_record": "../template_search.json"}, candidate
    )
    assert gate["status"] == "pass"
    assert gate["evidence_scope"] == "historical_reference_metadata"
    assert gate["current_assets_verified"] is False
    assert gate["current_origin_inspection_verified"] is False
    assert gate["administrator_editable_open_verified"] is False
    assert gate["recorded_administrator_editable_open"] is True
    assert gate["reference_audit_date"] == "2026-07-12"
