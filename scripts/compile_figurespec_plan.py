from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from compile_reference_geometry import compile_source_geometry
from validate_figurespec_v2 import load_document, validate


def _route(origin: dict[str, Any], category: str) -> str:
    routes = origin.get("operation_routes") or {}
    return str(routes.get(category, "auto"))


def compile_plan(spec: dict[str, Any]) -> dict[str, Any]:
    validation = validate(spec)
    if validation["status"] != "pass":
        return {"status": "invalid_spec", "validation": validation, "operations": []}

    try:
        compiled_spec, geometry_diagnostics = compile_source_geometry(spec)
    except Exception as exc:
        return {
            "status": "geometry_compile_failed",
            "validation": validation,
            "geometry_error": {"error_class": exc.__class__.__name__, "message": str(exc)},
            "operations": [],
        }

    origin = compiled_spec["origin"]
    operations: list[dict[str, Any]] = []
    seq = 0

    def add(stage: str, op: str, category: str, **payload: Any) -> None:
        nonlocal seq
        seq += 1
        operations.append(
            {
                "seq": seq,
                "stage": stage,
                "op": op,
                "adapter_route": _route(origin, category),
                "category": category,
                **payload,
            }
        )

    add(
        "session",
        "start_clean_session",
        "session",
        target_version=origin["target_version"],
        adapter_policy=origin["adapter_policy"],
        capability_profile=origin.get("capability_profile"),
    )
    add("session", "load_calibration_profile", "session", path=origin.get("calibration_profile"))
    add("session", "assert_capabilities", "session", required_categories=["data", "graph", "axis", "plot", "object", "save", "reopen", "inspect", "export"])

    for data in compiled_spec.get("data", []):
        add(
            "data",
            "create_data_object",
            "data",
            data_id=data.get("id"),
            object=data.get("object", "worksheet"),
            source=data.get("source"),
            format=data.get("format"),
            roles=data.get("roles"),
            expected_name=data.get("origin_name"),
        )

    add(
        "graph_base",
        "create_primary_graph",
        "graph",
        graph_name=origin["primary_graph"],
        seed_template=origin.get("seed_template"),
        seed_project=origin.get("seed_project"),
    )
    add("graph_base", "remove_seed_placeholders", "graph", graph_name=origin["primary_graph"], before_real_plots=True)
    add("graph_base", "apply_page_and_layer_base_style", "style", style=compiled_spec.get("style"), geometry_safe_only=True)

    page = compiled_spec.get("page") or {}
    add(
        "geometry",
        "set_page_geometry",
        "graph",
        page_id=page.get("id"),
        size_mm=page.get("size_mm"),
        coordinate_system=page.get("coordinate_system"),
    )
    for layer in compiled_spec.get("layers", []):
        add(
            "geometry",
            "create_or_configure_layer",
            "graph",
            layer_id=layer.get("id"),
            origin_name=layer.get("origin_name"),
            position_abs_mm=layer.get("position_abs_mm"),
            link=layer.get("link"),
        )

    for plot in sorted(compiled_spec.get("plots", []), key=lambda item: item.get("draw_order", 0)):
        add(
            "plots",
            "add_plot",
            "plot",
            plot_id=plot.get("id"),
            layer=plot.get("layer"),
            plot_type=plot.get("type"),
            data_ref=plot.get("data_ref"),
            mapping=plot.get("map"),
            draw_order=plot.get("draw_order"),
            rescale_policy="defer",
        )
        add("plots", "apply_plot_style", "style", plot_id=plot.get("id"), style=plot.get("style"), group_style=plot.get("group_style"))

    add("plots", "group_and_order_plots", "plot", graph_name=origin["primary_graph"])
    add("axes", "rescale_plots_once", "axis", graph_name=origin["primary_graph"], reason="initialize_from_real_data")
    for layer in compiled_spec.get("layers", []):
        add(
            "axes",
            "set_final_axes",
            "axis",
            layer_id=layer.get("id"),
            x=layer.get("x"),
            y=layer.get("y"),
            frame=layer.get("frame"),
        )
        add("axes", "apply_axis_style", "style", layer_id=layer.get("id"), axis_style=layer.get("axis_style"), global_style=compiled_spec.get("style"))
    add("axes", "freeze_axes_and_layer_geometry", "axis", graph_name=origin["primary_graph"], lock_rescale=True, snapshot_expected=True)

    annotations = compiled_spec.get("annotations", [])
    for ann in sorted(annotations, key=lambda item: (item.get("origin_object") or {}).get("z_order", 0)):
        route = ann.get("editable_route", "graph_object")
        if route == "data_plot":
            add(
                "annotations",
                "add_overlay_plot_no_rescale",
                "plot",
                annotation_id=ann.get("id"),
                layer=ann.get("layer"),
                origin_object=ann.get("origin_object"),
                data_plot=ann.get("data_plot"),
                style=ann.get("style"),
                assert_axis_snapshot_unchanged=True,
            )
        elif route == "template_object":
            add(
                "annotations",
                "configure_template_object",
                "object",
                annotation_id=ann.get("id"),
                layer=ann.get("layer"),
                origin_object=ann.get("origin_object"),
                style=ann.get("style"),
            )
        else:
            add(
                "annotations",
                "create_named_graph_object",
                "object",
                annotation_id=ann.get("id"),
                layer=ann.get("layer"),
                origin_object=ann.get("origin_object"),
                style=ann.get("style"),
            )
        add("annotations", "assert_axes_unchanged", "axis", after_annotation=ann.get("id"))

    add("finalize", "apply_legend_and_colorbar_text", "object", annotations=[ann.get("id") for ann in annotations if ann.get("type") in {"legend", "colorbar"}])
    add("finalize", "enforce_draw_order", "object", graph_name=origin["primary_graph"])
    add("finalize", "assert_no_rescale_after_annotations", "axis", graph_name=origin["primary_graph"])
    add("finalize", "export_primary_graph", "export", graph_name=origin["primary_graph"], export=compiled_spec.get("export"), export_role="pre_save")
    add("finalize", "save_opju", "save", project_path=(compiled_spec.get("runtime") or {}).get("project_path"), absolute_path_required=True)
    add("round_trip", "close_and_release_session", "session")
    add("round_trip", "reopen_opju_clean_session", "reopen", project_path=(compiled_spec.get("runtime") or {}).get("project_path"), read_only=False)
    add("round_trip", "inspect_opju_structure", "inspect", contract=compiled_spec.get("contracts"), output="opju_inspection.json")
    add("round_trip", "export_reopened_primary_graph", "export", graph_name=origin["primary_graph"], export_role="round_trip")
    add("qa", "run_image_qa_v3", "qa", reference_geometry=compiled_spec.get("reference_geometry"), export=compiled_spec.get("export"))
    add("qa", "generate_visual_correction_plan", "qa", visual_correction=compiled_spec.get("visual_correction"))
    add("qa", "finalize_manifest", "qa")

    correction = compiled_spec.get("visual_correction") or {}
    invariants = {
        "placeholder_removal_before_real_plots": True,
        "single_generic_rescale_before_final_axes": True,
        "no_generic_rescale_after_axes_freeze": True,
        "axis_snapshot_checked_after_each_annotation": True,
        "round_trip_export_is_qa_target": True,
    }
    return {
        "schema": "originplot.operation_plan.v4",
        "status": "ok",
        "validation": validation,
        "geometry_compilation": geometry_diagnostics,
        "compiled_spec": compiled_spec,
        "invariants": invariants,
        "correction_loop": {
            "max_iterations": correction.get("max_iterations", 3),
            "stage_order": correction.get("stage_order", ["structure", "geometry", "typography_color"]),
            "automatic_changes_must_be_bounded": True,
        },
        "operations": operations,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile FigureSpec v2/v3 into a deterministic Origin operation plan.")
    parser.add_argument("spec", type=Path)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--compiled-spec-out", type=Path)
    args = parser.parse_args()
    result = compile_plan(load_document(args.spec))
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    if args.compiled_spec_out and result.get("compiled_spec"):
        args.compiled_spec_out.parent.mkdir(parents=True, exist_ok=True)
        args.compiled_spec_out.write_text(json.dumps(result["compiled_spec"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(payload)
    return 0 if result["status"] == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
