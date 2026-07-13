from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "assets" / "journal_style_profiles.json"
SCHEMA_ID = "originplot.publication_contract.v1"
ARCHETYPES = {
    "quantitative_grid",
    "schematic_led_composite",
    "image_plate_quant",
    "asymmetric_mixed_modality",
    "single_panel",
}
PANEL_KINDS = {"quantitative", "image", "schematic", "mixed"}
SOURCE_KINDS = {"worksheet", "image", "computed", "reconstructed_geometry"}
EXPORT_FORMATS = {"opju", "pdf", "svg", "eps", "tiff", "png"}
VECTOR_FORMATS = {"pdf", "svg", "eps"}
RASTER_FORMATS = {"tiff", "png"}


def _load(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        value = json.loads(text)
    else:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise SystemExit("PyYAML is required to validate YAML contracts") from exc
        value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError("contract root must be an object")
    return value


def _profiles() -> dict[str, Any]:
    value = json.loads(PROFILE_PATH.read_text(encoding="utf-8-sig"))
    return value["profiles"]


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def validate(contract: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []

    def error(code: str, message: str) -> None:
        errors.append({"code": code, "message": message})

    def warning(code: str, message: str) -> None:
        warnings.append({"code": code, "message": message})

    if contract.get("schema") != SCHEMA_ID:
        error("E001_SCHEMA", f"schema must be {SCHEMA_ID}")
    conclusion = contract.get("core_conclusion")
    if not _nonempty(conclusion) or len(conclusion.strip()) < 12:
        error("E010_CONCLUSION", "core_conclusion must be a substantive one-sentence claim")
    if contract.get("figure_archetype") not in ARCHETYPES:
        error("E011_ARCHETYPE", "figure_archetype is unsupported")

    profile_name = contract.get("style_profile")
    profiles = _profiles()
    if profile_name not in profiles:
        error("E020_STYLE_PROFILE", f"unknown style_profile: {profile_name!r}")
    elif profile_name == "custom":
        tokens = contract.get("custom_style_tokens")
        required = set(profiles["custom"]["required_tokens"])
        missing = sorted(required - set(tokens or {}))
        if missing:
            error("E021_CUSTOM_STYLE", f"custom_style_tokens missing: {', '.join(missing)}")

    target_journal = contract.get("target_journal")
    if not _nonempty(target_journal):
        error("E022_TARGET_JOURNAL", "target_journal is required; use 'unspecified' when undecided")
    journal_specific = profile_name not in {None, "source_fidelity", "custom"}
    requirements = contract.get("journal_requirements") or {}
    if journal_specific:
        if not _nonempty(requirements.get("source_url")):
            error("E023_JOURNAL_SOURCE", "journal_requirements.source_url is required for a journal profile")
        checked_on = requirements.get("checked_on")
        if not _nonempty(checked_on) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", checked_on):
            error("E024_JOURNAL_DATE", "journal_requirements.checked_on must be YYYY-MM-DD")

    size = contract.get("final_size_mm")
    if not isinstance(size, list) or len(size) != 2 or any(
        not isinstance(item, (int, float)) or isinstance(item, bool) or item <= 0 for item in size
    ):
        error("E030_FINAL_SIZE", "final_size_mm must be two positive numbers")

    panels = contract.get("panels")
    panel_ids: set[str] = set()
    panel_kinds: dict[str, str] = {}
    questions: set[str] = set()
    if not isinstance(panels, list) or not panels:
        error("E040_PANELS", "panels must be a nonempty list")
        panels = []
    for index, panel in enumerate(panels):
        if not isinstance(panel, dict):
            error("E041_PANEL_OBJECT", f"panels[{index}] must be an object")
            continue
        panel_id = str(panel.get("id", "")).strip()
        question = str(panel.get("question", "")).strip()
        kind = panel.get("kind")
        if not panel_id or panel_id in panel_ids:
            error("E042_PANEL_ID", f"panels[{index}].id is missing or duplicated")
        else:
            panel_ids.add(panel_id)
            panel_kinds[panel_id] = str(kind)
        if kind not in PANEL_KINDS:
            error("E043_PANEL_KIND", f"panel {panel_id!r} has unsupported kind")
        if not question or question.casefold() in questions:
            error("E044_PANEL_QUESTION", f"panel {panel_id!r} requires a distinct question")
        questions.add(question.casefold())

    hierarchy = contract.get("evidence_hierarchy") or {}
    hero = hierarchy.get("hero")
    validation = hierarchy.get("validation", [])
    controls = hierarchy.get("controls", [])
    if hero not in panel_ids:
        error("E050_HERO", "evidence_hierarchy.hero must reference one panel")
    if not isinstance(validation, list) or not isinstance(controls, list):
        error("E051_HIERARCHY_LIST", "validation and controls must be lists")
        validation, controls = [], []
    mapped = [hero] + list(validation) + list(controls)
    if any(item not in panel_ids for item in mapped if item is not None):
        error("E052_HIERARCHY_REFERENCE", "evidence_hierarchy references an unknown panel")
    if len(mapped) != len(set(mapped)):
        error("E053_HIERARCHY_DUPLICATE", "a panel may appear in only one evidence tier")
    if set(mapped) != panel_ids:
        error("E054_HIERARCHY_COVERAGE", "every panel must appear in the evidence hierarchy")

    sources = contract.get("source_data")
    covered_panels: set[str] = set()
    source_ids: set[str] = set()
    if not isinstance(sources, list) or not sources:
        error("E060_SOURCE_DATA", "source_data must be a nonempty list")
        sources = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            error("E061_SOURCE_OBJECT", f"source_data[{index}] must be an object")
            continue
        source_id = str(source.get("id", "")).strip()
        if not source_id or source_id in source_ids:
            error("E062_SOURCE_ID", f"source_data[{index}].id is missing or duplicated")
        source_ids.add(source_id)
        if source.get("kind") not in SOURCE_KINDS:
            error("E063_SOURCE_KIND", f"source {source_id!r} has unsupported kind")
        if not _nonempty(source.get("location")):
            error("E064_SOURCE_LOCATION", f"source {source_id!r} requires a portable location")
        source_panels = source.get("panels")
        if not isinstance(source_panels, list) or not source_panels:
            error("E065_SOURCE_PANELS", f"source {source_id!r} must map to panels")
            continue
        if any(item not in panel_ids for item in source_panels):
            error("E066_SOURCE_REFERENCE", f"source {source_id!r} references an unknown panel")
        covered_panels.update(item for item in source_panels if item in panel_ids)
    if covered_panels != panel_ids:
        error("E067_SOURCE_COVERAGE", "every panel must map to at least one source_data item")

    families = contract.get("editable_object_families")
    if not isinstance(families, list) or not families or any(not _nonempty(item) for item in families):
        error("E070_EDITABLE_FAMILIES", "editable_object_families must be a nonempty string list")

    stats = contract.get("statistics_and_uncertainty")
    stats_by_panel: dict[str, dict[str, Any]] = {}
    if not isinstance(stats, list):
        error("E080_STATISTICS", "statistics_and_uncertainty must be a list")
        stats = []
    for item in stats:
        if not isinstance(item, dict) or item.get("panel") not in panel_ids:
            error("E081_STATISTICS_PANEL", "each statistics item must reference a known panel")
            continue
        panel_id = item["panel"]
        if panel_id in stats_by_panel:
            error("E082_STATISTICS_DUPLICATE", f"duplicate statistics declaration for panel {panel_id!r}")
        stats_by_panel[panel_id] = item
    for panel_id, kind in panel_kinds.items():
        if kind not in {"quantitative", "mixed"}:
            continue
        item = stats_by_panel.get(panel_id)
        if item is None:
            error("E083_STATISTICS_COVERAGE", f"panel {panel_id!r} requires a statistics declaration")
        elif item.get("applicable") is True:
            missing = [key for key in ("n_definition", "center", "spread", "test") if not _nonempty(item.get(key))]
            if missing:
                error("E084_STATISTICS_FIELDS", f"panel {panel_id!r} missing: {', '.join(missing)}")
        elif item.get("applicable") is False:
            if not _nonempty(item.get("reason")):
                error("E085_STATISTICS_REASON", f"panel {panel_id!r} requires a reason when statistics are not applicable")
        else:
            error("E086_STATISTICS_APPLICABLE", f"panel {panel_id!r} requires boolean applicable")

    accessibility = contract.get("accessibility") or {}
    for key in ("color_vision_safe", "grayscale_legible", "non_color_encoding"):
        if not isinstance(accessibility.get(key), bool):
            error("E090_ACCESSIBILITY", f"accessibility.{key} must be boolean")
        elif accessibility[key] is False:
            if profile_name == "source_fidelity":
                warning("W091_SOURCE_ACCESSIBILITY", f"source_fidelity preserves a reference that fails {key}")
            else:
                error("E091_ACCESSIBILITY_FAIL", f"publication profile requires {key}=true")

    formats = contract.get("export_formats")
    normalized_formats: set[str] = set()
    if not isinstance(formats, list):
        error("E100_EXPORTS", "export_formats must be a list")
    else:
        normalized_formats = {str(item).lower() for item in formats}
        unsupported = normalized_formats - EXPORT_FORMATS
        if unsupported:
            error("E101_EXPORT_FORMAT", f"unsupported export formats: {', '.join(sorted(unsupported))}")
        if "opju" not in normalized_formats or not (normalized_formats & VECTOR_FORMATS):
            error("E102_EXPORT_BUNDLE", "export_formats must include opju and at least one vector format")
        if any(kind in {"image", "mixed"} for kind in panel_kinds.values()) and not (normalized_formats & RASTER_FORMATS):
            error("E103_RASTER_EXPORT", "image or mixed panels require tiff or png export")

    risks = contract.get("reviewer_risks")
    if not isinstance(risks, list) or not risks or any(not _nonempty(item) for item in risks):
        error("E110_REVIEWER_RISKS", "reviewer_risks must contain at least one substantive item")

    tracks = contract.get("acceptance_tracks") or {}
    for key in ("source_fidelity", "publication_style"):
        if not isinstance(tracks.get(key), bool):
            error("E120_ACCEPTANCE_TRACK", f"acceptance_tracks.{key} must be boolean")
    if profile_name == "source_fidelity" and tracks.get("source_fidelity") is not True:
        error("E121_SOURCE_TRACK", "source_fidelity profile requires the source_fidelity acceptance track")
    if profile_name != "source_fidelity" and tracks.get("publication_style") is not True:
        error("E122_PUBLICATION_TRACK", "journal/custom profiles require the publication_style acceptance track")

    if contract.get("domain_profile", "generic") == "materials_ebsd":
        warning("W130_MATERIALS_QA", "apply references/materials-figure-qa.md before claim promotion")

    return {
        "schema": "originplot.publication_contract.validation.v1",
        "contract_schema": contract.get("schema"),
        "status": "ok" if not errors else "failed",
        "error_count": len(errors),
        "warning_count": len(warnings),
        "errors": errors,
        "warnings": warnings,
        "panel_count": len(panel_ids),
        "source_count": len(source_ids),
        "style_profile": profile_name,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate an OriginPlot publication contract.")
    parser.add_argument("contract", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    try:
        report = validate(_load(args.contract))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        report = {
            "schema": "originplot.publication_contract.validation.v1",
            "status": "failed",
            "error_count": 1,
            "warning_count": 0,
            "errors": [{"code": "E000_LOAD", "message": str(exc)}],
            "warnings": [],
        }
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
