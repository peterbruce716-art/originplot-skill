from __future__ import annotations

from pathlib import Path
from typing import Any

from . import fig3_builder, fig12_builder, fig14_builder, fig15_builder, fig16_builder
from .common_origin_utils import find_graph, fit_page_to_window
from .readback import (
    inspect_page,
    validate_axis_contract,
    validate_direct_worksheet_plot_bindings,
    validate_graphobject_contracts,
    validate_plot_derived_legends,
    validate_subplot_worksheet_bindings,
)
from .session import (
    assert_no_demo_watermark,
    has_visible_origin_process,
    is_administrator_python,
    origin_session,
)
from .source_geometry import validate_source_geometry_groups
from runtime.editable_opju import ensure_opju_file_editable, open_opju_editable


BUILDERS = {
    "fig3": fig3_builder.build,
    "fig12": fig12_builder.build,
    "fig14": fig14_builder.build,
    "fig15": fig15_builder.build,
    "fig16": fig16_builder.build,
}

MAX_DIRECT_PLOT_WORKSHEET_ROWS = 5_000


def _page_names(page: Any) -> set[str]:
    names: set[str] = set()
    for attribute in ("lname", "name"):
        try:
            value = getattr(page, attribute)
        except Exception:
            continue
        if value:
            names.add(str(value))
    return names


def _validate_required_worksheet_books(op: Any, expected_names: list[str]) -> dict[str, Any]:
    expected = [str(name) for name in expected_names if str(name)]
    if not expected:
        return {"status": "not_required", "expected": [], "found": [], "missing": [], "aliases": {}}

    found: set[str] = set()
    aliases: dict[str, list[str]] = {}
    try:
        for workbook in op.pages("w"):
            names = _page_names(workbook)
            found.update(names)
            for expected_name in expected:
                if expected_name in names:
                    aliases[expected_name] = sorted(names)
    except Exception:
        pass
    finder = getattr(op, "find_book", None)
    if callable(finder):
        for name in expected:
            if name in found:
                continue
            try:
                workbook = finder("w", name)
            except Exception:
                workbook = None
            if workbook is not None:
                found.add(name)
                names = _page_names(workbook)
                found.update(names)
                aliases[name] = sorted(names | {name})
    missing = [name for name in expected if name not in found]
    return {
        "status": "ok" if not missing else "failed",
        "expected": expected,
        "found": sorted(name for name in found if name in expected),
        "missing": missing,
        "aliases": {name: aliases.get(name, [name]) for name in expected if name not in missing},
    }


def _validate_worksheet_row_budget(
    op: Any,
    expected_names: list[str],
    limit: int = MAX_DIRECT_PLOT_WORKSHEET_ROWS,
) -> dict[str, Any]:
    expected = [str(name) for name in expected_names if str(name)]
    if not expected:
        return {"status": "not_required", "limit": int(limit), "total_rows": 0, "worksheets": []}
    finder = getattr(op, "find_book", None)
    enumerated_books: dict[str, Any] = {}
    try:
        for workbook in op.pages("w"):
            for page_name in _page_names(workbook):
                enumerated_books.setdefault(page_name, workbook)
    except Exception:
        pass
    records: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for name in expected:
        try:
            book = enumerated_books.get(name)
            if book is None and callable(finder):
                book = finder("w", name)
        except Exception as exc:
            book = None
            errors.append({"worksheet_book": name, "error": f"{exc.__class__.__name__}: {exc}"})
        if book is None:
            errors.append({"worksheet_book": name, "error": "worksheet book not found"})
            continue
        try:
            sheets = [book[index] for index in range(len(book))]
        except Exception:
            try:
                sheets = list(book)
            except Exception as exc:
                errors.append({"worksheet_book": name, "error": f"worksheet enumeration unavailable: {exc.__class__.__name__}: {exc}"})
                continue
        for index, sheet in enumerate(sheets):
            try:
                shape = tuple(int(value) for value in sheet.shape)
                rows = int(shape[0])
            except Exception as exc:
                errors.append({"worksheet_book": name, "worksheet_index": str(index), "error": f"row shape unavailable: {exc.__class__.__name__}: {exc}"})
                continue
            records.append({"worksheet_book": name, "worksheet_index": index, "rows": rows, "shape": list(shape)})
    total_rows = sum(int(record["rows"]) for record in records)
    status = "ok" if not errors and total_rows <= int(limit) else "failed"
    return {"status": status, "limit": int(limit), "total_rows": total_rows, "worksheets": records, "errors": errors}


def _validate_worksheet_binding_inventory(
    expected_names: list[str],
    inventory: list[dict[str, Any]],
) -> dict[str, Any]:
    expected = [str(name) for name in expected_names if str(name)]
    if not expected:
        return {"status": "not_required", "expected": [], "mapped": [], "missing": []}
    mapped = {
        str(record.get("worksheet_name", ""))
        for record in inventory
        if isinstance(record, dict)
        and record.get("worksheet_name")
        and record.get("association_mode")
    }
    missing = [name for name in expected if name not in mapped]
    return {
        "status": "ok" if not missing else "failed",
        "expected": expected,
        "mapped": sorted(name for name in mapped if name in expected),
        "missing": missing,
    }


def _ensure_opju_editable(path: Path) -> dict[str, Any]:
    return ensure_opju_file_editable(path)


def build_origin_figure(
    figure_id: str,
    candidate_params: dict[str, Any] | None = None,
    output_dir: Path | None = None,
    attach_existing_authorized: bool = True,
    require_administrator: bool = True,
    allow_diagnostic_hidden: bool = False,
) -> dict[str, Any]:
    if figure_id not in BUILDERS:
        return {
            "schema": "originplot.build_origin_figure.v588",
            "status": "failed",
            "error_code": "E100_SCHEMA_INVALID",
            "message": f"Unknown figure_id: {figure_id}",
        }
    if not attach_existing_authorized and not allow_diagnostic_hidden:
        return {
            "schema": "originplot.build_origin_figure.v588",
            "status": "failed",
            "error_code": "E121_ATTACH_POLICY_VIOLATION",
            "message": (
                "Formal OriginPlot runs default to administrator attach-existing. "
                "Hidden or newly created Origin sessions are diagnostic-only and cannot be promoted."
            ),
            "attach_existing_authorized": False,
            "opju_generation_allowed": False,
            "pass_eligible": False,
        }
    if require_administrator and not is_administrator_python():
        return {
            "schema": "originplot.build_origin_figure.v588",
            "status": "failed",
            "error_code": "E120_ENVIRONMENT_MISMATCH",
            "message": "Administrator Python is required before importing originpro or attaching to Origin.",
            "python_is_admin": False,
            "origin_attach_not_attempted": True,
            "opju_generation_allowed": False,
            "pass_eligible": False,
        }
    if attach_existing_authorized and not has_visible_origin_process():
        return {
            "schema": "originplot.build_origin_figure.v588",
            "status": "failed",
            "error_code": "E121_ATTACH_POLICY_VIOLATION",
            "message": (
                "No visible Origin process is available for administrator attach-existing. "
                "Open Origin as administrator before running a formal OriginPlot build."
            ),
            "origin_attach_not_attempted": True,
            "opju_generation_allowed": False,
            "pass_eligible": False,
            "required_origin_process": "administrator_opened_visible_origin",
        }
    import originpro as op  # type: ignore

    output_dir = Path(output_dir or Path.cwd()).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    opju = output_dir / f"{figure_id}_builder_result.opju"
    pre_png = output_dir / f"{figure_id}_builder_pre_save.png"
    png = output_dir / f"{figure_id}_builder_post_reopen.png"
    params = candidate_params or {}
    build_record: dict[str, Any] = {}
    build_session: dict[str, str] = {}
    editable_view_evidence: dict[str, Any] = {}
    with origin_session(
        op,
        attach_existing_authorized=attach_existing_authorized,
        require_administrator=False,
        allow_diagnostic_hidden=allow_diagnostic_hidden,
    ) as build_session:
        if attach_existing_authorized:
            op.new(asksave=False)
        build_record = BUILDERS[figure_id](op, params)
        page = find_graph(op, build_record["page_name"])
        if page is None:
            raise RuntimeError(f"Built graph page not found before save: {build_record['page_name']}")
        editable_view_evidence["pre_save"] = fit_page_to_window(page)
        export_width = int(build_record.get("canvas_size", (1200, 0))[0])
        page.save_fig(str(pre_png), type="png", replace=True, width=export_width)
        build_session["pre_save_demo_gate"] = assert_no_demo_watermark(pre_png)
        op.save(str(opju))

    readback: dict[str, Any] = {}
    worksheet_readback: dict[str, Any] = {}
    worksheet_row_budget: dict[str, Any] = {}
    reopen_session: dict[str, str] = {}
    editable_open_evidence: dict[str, Any] = {}
    with origin_session(
        op,
        attach_existing_authorized=attach_existing_authorized,
        require_administrator=False,
        allow_diagnostic_hidden=allow_diagnostic_hidden,
        expected_origin_pid=int(build_session["origin_pid"]) if attach_existing_authorized else None,
    ) as reopen_session:
        if attach_existing_authorized:
            op.new(asksave=False)
        editable_open_evidence = open_opju_editable(op, opju)
        page = find_graph(op, build_record["page_name"])
        if page is None:
            raise RuntimeError(f"Built graph page not found after reopen: {build_record['page_name']}")
        editable_view_evidence["post_reopen"] = fit_page_to_window(page)
        # Persist the fitted edit view in the delivered OPJU. This affects only
        # the Origin window zoom; the fixed page dimensions and exports are unchanged.
        op.save(str(opju))
        readback = inspect_page(
            op,
            page,
            expected_graphobject_names_by_layer=build_record.get("required_graphobject_names_by_layer"),
        )
        worksheet_readback = _validate_required_worksheet_books(
            op,
            build_record.get("required_worksheet_books", []),
        )
        worksheet_row_budget = _validate_worksheet_row_budget(
            op,
            build_record.get("required_worksheet_books", []),
            int(build_record.get("max_direct_plot_worksheet_rows", MAX_DIRECT_PLOT_WORKSHEET_ROWS)),
        )
        export_width = int(build_record.get("canvas_size", (1200, 0))[0])
        page.save_fig(str(png), type="png", replace=True, width=export_width)

    expected = int(build_record["expected_plot_count"])
    actual = int(readback.get("plot_count", 0))
    expected_plot_count_by_layer = {
        int(index): int(count)
        for index, count in build_record.get("expected_plot_count_by_layer", {}).items()
    }
    actual_plot_count_by_layer = {
        int(layer.get("index", index)): int(layer.get("plot_count", 0))
        for index, layer in enumerate(readback.get("layers", []))
    }
    layer_plot_count_mismatches = [
        {
            "layer_index": layer_index,
            "expected": expected_count,
            "actual": actual_plot_count_by_layer.get(layer_index),
        }
        for layer_index, expected_count in expected_plot_count_by_layer.items()
        if actual_plot_count_by_layer.get(layer_index) != expected_count
    ]
    layer_plot_count_validation = {
        "status": (
            "not_required"
            if not expected_plot_count_by_layer
            else "ok"
            if not layer_plot_count_mismatches
            else "failed"
        ),
        "expected": expected_plot_count_by_layer,
        "actual": actual_plot_count_by_layer,
        "mismatches": layer_plot_count_mismatches,
    }
    expected_graphobjects = int(build_record.get("expected_graphobject_count", 0))
    actual_graphobjects = sum(
        int(layer.get("graph_object_readback", {}).get("object_count", 0))
        for layer in readback.get("layers", [])
    )
    declared_checks = []
    declared_checks.append(actual == expected)
    if layer_plot_count_validation["status"] != "not_required":
        declared_checks.append(layer_plot_count_validation["status"] == "ok")
    if expected_graphobjects > 0:
        declared_checks.append(actual_graphobjects >= expected_graphobjects)
    axis_validation = validate_axis_contract(readback, build_record.get("axis_contract", []))
    if axis_validation["status"] != "not_required":
        declared_checks.append(axis_validation["status"] == "ok")
    graphobject_contract_validation = validate_graphobject_contracts(
        readback,
        build_record.get("required_graphobject_contracts", {}),
    )
    if graphobject_contract_validation["status"] != "not_required":
        declared_checks.append(graphobject_contract_validation["status"] == "ok")
    if worksheet_readback["status"] != "not_required":
        declared_checks.append(worksheet_readback["status"] == "ok")
    if worksheet_row_budget["status"] != "not_required":
        declared_checks.append(worksheet_row_budget["status"] == "ok")
    worksheet_binding_validation = validate_direct_worksheet_plot_bindings(
        readback, build_record.get("direct_worksheet_plot_contracts", [])
    )
    declared_checks.append(worksheet_binding_validation["status"] == "ok")
    subplot_worksheet_validation = validate_subplot_worksheet_bindings(
        readback,
        build_record.get("subplot_worksheet_contracts", []),
        worksheet_readback.get("aliases", {}),
    )
    if "subplot_worksheet_contracts" in build_record:
        declared_checks.append(subplot_worksheet_validation["status"] == "ok")
    legend_plot_reference_validation = validate_plot_derived_legends(
        readback, build_record.get("legend_plot_reference_contracts", [])
    )
    if "legend_plot_reference_contracts" in build_record:
        declared_checks.append(legend_plot_reference_validation["status"] in {"ok", "not_required"})
    source_geometry_validation = validate_source_geometry_groups(
        readback, build_record.get("source_geometry_groups")
    )
    declared_checks.append(source_geometry_validation["status"] == "ok")
    structure_ok = bool(declared_checks) and all(declared_checks)
    figure_result = {
        "status": "post_reopen_built" if structure_ok else "structure_readback_failed",
        "opju_path": str(opju),
        "origin_rendered_exports": [
            {"path": str(pre_png), "phase": "pre_save"},
            {"path": str(png), "phase": "post_reopen"},
        ],
        "origin_object_readback": {build_record["page_name"]: readback},
        "origin_object_readback_validation": {
            "status": "ok" if structure_ok else "failed",
            "expected_plot_count": expected,
            "actual_plot_count": actual,
            "layer_plot_count_validation": layer_plot_count_validation,
            "expected_graphobject_count": expected_graphobjects,
            "actual_graphobject_count": actual_graphobjects,
            "axis_contract_validation": axis_validation,
            "graphobject_contract_validation": graphobject_contract_validation,
            "worksheet_book_validation": worksheet_readback,
            "worksheet_row_budget_validation": worksheet_row_budget,
            "worksheet_binding_validation": worksheet_binding_validation,
            "subplot_worksheet_validation": subplot_worksheet_validation,
            "legend_plot_reference_validation": legend_plot_reference_validation,
            "source_geometry_group_validation": source_geometry_validation,
        },
        "origin_candidate_hard_gate": {"status": "pass" if structure_ok else "failed"},
        "origin_export_qa": [],
        "builder_route": build_record,
        "session_release": reopen_session["release"],
        "editable_open_evidence": editable_open_evidence,
        "editable_view_evidence": editable_view_evidence,
        "session_evidence": {
            "build": build_session,
            "reopen": reopen_session,
        },
        "pass_eligible": False,
    }
    return {
        "schema": "originplot.build_origin_figure.v588",
        "status": "built_post_reopen_not_promoted" if structure_ok else "failed",
        "session_mode": (
            "administrator_attach_existing_authorized_two_phase"
            if attach_existing_authorized
            else "diagnostic_new_hidden_origin_then_clean_reopen_not_pass_eligible"
        ),
        "default_origin_policy": "administrator_attach_existing_visible_origin",
        "attach_existing_authorized": bool(attach_existing_authorized),
        "require_administrator": bool(require_administrator),
        "allow_diagnostic_hidden": bool(allow_diagnostic_hidden),
        "per_figure": {figure_id: figure_result},
    }
