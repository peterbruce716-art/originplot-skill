from __future__ import annotations

from typing import Any


SCHEMA = "originplot.source_geometry_groups.v1"
_CONTINUITY_MODES = {
    "single_xy",
    "nan_separated_xy",
    "closed_xy",
    "xyz_grid",
    "categorical_region_field",
    "stacked_columns",
}


def source_geometry_contract(groups: list[dict[str, Any]]) -> dict[str, Any]:
    """Wrap builder-declared canonical sources and their editable consumers."""
    return {"schema": SCHEMA, "groups": groups}


def validate_source_geometry_groups(
    readback: dict[str, Any],
    contract: dict[str, Any] | None,
) -> dict[str, Any]:
    """Validate source-group declarations against reopened Origin bindings.

    A group has one canonical scientific source. Origin-specific plot views may
    use different columns only when they remain in the same Worksheet and name
    their deterministic derivation. This covers plot-family constraints without
    allowing independently redrawn line, marker, border, or local-fill data.
    """
    if not contract:
        return {"status": "not_required", "schema": SCHEMA, "groups": [], "mismatches": []}

    mismatches: list[dict[str, Any]] = []
    if contract.get("schema") != SCHEMA:
        mismatches.append({"property": "schema", "expected": SCHEMA, "actual": contract.get("schema")})
    groups = contract.get("groups")
    if not isinstance(groups, list) or not groups:
        mismatches.append({"property": "groups", "expected": "nonempty list", "actual": groups})
        groups = []

    plots: dict[tuple[int, int], dict[str, Any]] = {}
    graph_objects: set[str] = set()
    for layer in readback.get("layers", []):
        layer_index = int(layer.get("index", -1))
        for fallback_index, plot in enumerate(layer.get("plot_details", [])):
            plot_index = int(plot.get("index", fallback_index))
            plots[(layer_index, plot_index)] = plot
        graph_readback = layer.get("graph_object_readback", {})
        for collection in ("objects", "enumerated_objects"):
            for record in graph_readback.get(collection, []):
                name = record.get("name") if isinstance(record, dict) else None
                if name:
                    graph_objects.add(str(name).casefold())

    group_results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for group in groups:
        before = len(mismatches)
        if not isinstance(group, dict):
            mismatches.append({"property": "group", "expected": "object", "actual": group})
            continue
        group_id = str(group.get("group_id", ""))
        if not group_id or group_id in seen_ids:
            mismatches.append({"group_id": group_id, "property": "group_id", "expected": "unique nonempty id", "actual": group_id})
        seen_ids.add(group_id)
        if group.get("continuity") not in _CONTINUITY_MODES:
            mismatches.append({"group_id": group_id, "property": "continuity", "expected": sorted(_CONTINUITY_MODES), "actual": group.get("continuity")})
        canonical_source = group.get("canonical_source")
        if not isinstance(canonical_source, dict) or not canonical_source.get("source_id"):
            mismatches.append({"group_id": group_id, "property": "canonical_source.source_id", "expected": "nonempty", "actual": canonical_source})
        consumers = group.get("consumers")
        if not isinstance(consumers, list) or not consumers:
            mismatches.append({"group_id": group_id, "property": "consumers", "expected": "nonempty list", "actual": consumers})
            consumers = []

        plot_bindings: list[dict[str, Any]] = []
        canonical_plot_count = 0
        for consumer in consumers:
            if not isinstance(consumer, dict):
                mismatches.append({"group_id": group_id, "property": "consumer", "expected": "object", "actual": consumer})
                continue
            kind = consumer.get("kind")
            view = consumer.get("view")
            if view == "canonical":
                canonical_plot_count += 1
            elif view == "derived" and not consumer.get("derivation"):
                mismatches.append({"group_id": group_id, "consumer_id": consumer.get("consumer_id"), "property": "derivation", "expected": "nonempty for derived view", "actual": consumer.get("derivation")})
            if kind == "plot":
                try:
                    key = (int(consumer["layer_index"]), int(consumer["plot_index"]))
                except (KeyError, TypeError, ValueError):
                    mismatches.append({"group_id": group_id, "consumer_id": consumer.get("consumer_id"), "property": "plot selector", "expected": "integer layer_index and plot_index", "actual": consumer})
                    continue
                actual = plots.get(key)
                if actual is None:
                    mismatches.append({"group_id": group_id, "consumer_id": consumer.get("consumer_id"), "property": "plot exists", "expected": True, "actual": False})
                    continue
                for field in ("data_workbook", "data_worksheet", "x_column", "y_column"):
                    if not actual.get(field):
                        mismatches.append({"group_id": group_id, "consumer_id": consumer.get("consumer_id"), "property": field, "expected": "nonempty reopened binding", "actual": actual.get(field)})
                for field in ("x_column", "y_column", "z_column"):
                    if field in consumer and actual.get(field) != consumer[field]:
                        mismatches.append({"group_id": group_id, "consumer_id": consumer.get("consumer_id"), "property": field, "expected": consumer[field], "actual": actual.get(field)})
                plot_bindings.append({"consumer": consumer, "actual": actual})
            elif kind == "graphobject":
                object_name = str(consumer.get("object_name", ""))
                if not object_name or object_name.casefold() not in graph_objects:
                    mismatches.append({"group_id": group_id, "consumer_id": consumer.get("consumer_id"), "property": "graphobject exists", "expected": object_name or "nonempty name", "actual": False})
            else:
                mismatches.append({"group_id": group_id, "consumer_id": consumer.get("consumer_id"), "property": "kind", "expected": "plot or graphobject", "actual": kind})

        if canonical_plot_count != 1:
            mismatches.append({"group_id": group_id, "property": "canonical consumer count", "expected": 1, "actual": canonical_plot_count})
        if group.get("same_worksheet", True) and plot_bindings:
            worksheets = {
                (item["actual"].get("data_workbook"), item["actual"].get("data_worksheet"))
                for item in plot_bindings
            }
            if len(worksheets) != 1:
                mismatches.append({"group_id": group_id, "property": "same reopened Worksheet", "expected": 1, "actual": sorted(str(item) for item in worksheets)})
        canonical = next((item for item in plot_bindings if item["consumer"].get("view") == "canonical"), None)
        if canonical is not None:
            for item in plot_bindings:
                if item["consumer"].get("same_columns_as_canonical") is True:
                    for field in ("x_column", "y_column", "z_column"):
                        if field in canonical["actual"] and item["actual"].get(field) != canonical["actual"].get(field):
                            mismatches.append({"group_id": group_id, "consumer_id": item["consumer"].get("consumer_id"), "property": f"same canonical {field}", "expected": canonical["actual"].get(field), "actual": item["actual"].get(field)})
        group_results.append({"group_id": group_id, "status": "ok" if len(mismatches) == before else "failed"})

    return {
        "status": "ok" if not mismatches else "failed",
        "schema": SCHEMA,
        "group_count": len(groups),
        "groups": group_results,
        "mismatches": mismatches,
    }
