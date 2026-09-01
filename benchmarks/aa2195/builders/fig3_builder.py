from __future__ import annotations

from typing import Any

from .common_origin_utils import create_hidden_graph_page, disable_speed_mode, page_dot_command, page_percent_layer_command, remove_default_labels, reveal_graph_page
from .fig3_data import COLORS, LINE_STYLES
from .fresh_source_data import load_fresh_figure_data
from .source_geometry import source_geometry_contract


FIG3_FONT = "Times New Roman"
FIG3_FONT_ID = 429


def _set_plot_style(plot: Any, color: str, line_style: int) -> None:
    try:
        plot.color = color
    except Exception:
        pass
    for prop, value in (("line.width", 3.5), ("width", 3.5)):
        try:
            plot.set_float(prop, value)
        except Exception:
            pass
    for prop in ("line.style", "style"):
        try:
            plot.set_int(prop, int(line_style))
        except Exception:
            pass
    try:
        plot.set_cmd(f"-d {int(line_style)}")
    except Exception:
        pass


def _name_label(
    label: Any,
    name: str,
    size: float = 9.0,
    *,
    color: str | None = None,
    bold: bool = False,
) -> None:
    if label is None:
        return
    try:
        label.obj.SetName(name)
    except Exception:
        pass
    try:
        label.set_int("attach", 2)
        label.set_float("fsize", size)
        label.set_int("font", FIG3_FONT_ID)
        label.set_int("fontWeight", 700 if bold else 400)
    except Exception:
        pass
    if color is not None:
        try:
            label.color = color
        except Exception:
            pass
    try:
        label.lt_exec(f"{name}.font=font({FIG3_FONT});")
    except Exception:
        pass


def _patterned_series(x: list[float], y: list[float], mode: str) -> tuple[list[float], list[float]]:
    if mode not in LINE_STYLES:
        raise ValueError(f"Unknown Fig3 line mode: {mode}")
    return list(x), list(y)


def _column_name(index: int) -> str:
    if not 0 <= index < 26:
        raise ValueError("Fig3 worksheet columns must remain within A:Z")
    return chr(ord("A") + index)


def _add_panel(
    op: Any,
    layer: Any,
    panel: dict[str, Any],
    layer_index: int,
) -> tuple[int, list[str], list[str], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    book_name = f"Fig3_{panel['name']}_source_calibrated_curves"
    sheet = op.new_book(lname=book_name)[0]
    column = 0
    plot_count = 0
    plot_styles: list[tuple[Any, str, int]] = []
    plot_contracts: list[dict[str, Any]] = []
    source_groups: list[dict[str, Any]] = []
    plot_numbers_by_mode: dict[str, list[int]] = {"PSC": [], "UC": [], "TR": []}
    for temperature in ("250", "300", "350", "400"):
        for mode in ("PSC", "UC", "TR"):
            record = panel["series"].get(temperature, {}).get(mode)
            if record is None:
                continue
            plot_x, plot_y = _patterned_series(record["x"], record["y"], mode)
            sheet.from_list(column, plot_x, lname=f"strain_{temperature}_{mode}", axis="X")
            sheet.from_list(column + 1, plot_y, lname=f"stress_{temperature}_{mode}", axis="Y")
            plot = layer.add_plot(sheet, colx=column, coly=column + 1, type="line")
            _set_plot_style(plot, COLORS[temperature], LINE_STYLES[mode])
            plot_styles.append((plot, COLORS[temperature], LINE_STYLES[mode]))
            plot_numbers_by_mode[mode].append(plot_count + 1)
            plot_contracts.append({
                "layer_index": layer_index,
                "plot_index": plot_count,
                "plot_type_code": 200,
                "x_column": _column_name(column),
                "y_column": _column_name(column + 1),
            })
            source_groups.append({
                "group_id": f"fig3.{panel['name']}.{temperature}.{mode}.curve",
                "canonical_source": {
                    "source_id": f"fresh_source_bundle.fig3.{panel['name']}.{temperature}.{mode}",
                    "kind": "fresh_pdf_vector_curve_anchors",
                },
                "continuity": "single_xy",
                "same_worksheet": True,
                "consumers": [{
                    "consumer_id": "curve",
                    "kind": "plot",
                    "view": "canonical",
                    "layer_index": layer_index,
                    "plot_index": plot_count,
                    "x_column": _column_name(column),
                    "y_column": _column_name(column + 1),
                }],
            })
            plot_count += 1
            column += 2

    # Origin may refresh grouped plot styles while subsequent plots are added.
    # Reapply after the group is complete so the saved OPJU retains mode dashes.
    for plot, color, line_style in plot_styles:
        _set_plot_style(plot, color, line_style)

    layer.set_xlim(0.0, 1.1)
    layer.set_ylim(0.0, float(panel["ymax"]))
    layer.lt_exec(page_percent_layer_command(tuple(panel["frame_percent"])))
    remove_default_labels(layer)
    y_major = 50
    layer.lt_exec(
        "layer.x.from=0; layer.x.to=1.1; layer.x.inc=0.2; layer.x.minorTicks=1; "
        f"layer.y.from=0; layer.y.to={float(panel['ymax']):g}; layer.y.inc={y_major}; layer.y.minorTicks=1; "
        "layer.x.opposite=1; layer.y.opposite=1; layer.x.showopposite=1; layer.y.showopposite=1; "
        "label -xb \"Equivalent strain\"; label -yl \"Equivalent stress/MPa\"; yl.rotate=90; "
        f"layer.x.label.font=font({FIG3_FONT}); layer.y.label.font=font({FIG3_FONT}); "
        f"xb.font=font({FIG3_FONT}); yl.font=font({FIG3_FONT}); "
        "layer.x.label.fsize=32; layer.y.label.fsize=32; xb.fsize=38; yl.fsize=38;"
    )
    labels: list[str] = []
    panel_label = layer.add_label(panel["panel"], -0.27, float(panel["ymax"]) * 1.04)
    panel_name = f"fig3_panel_{panel['name']}"
    _name_label(panel_label, panel_name, 38.0)
    labels.append(panel_name)
    modes = ("PSC", "UC") if panel["name"] == "d" else ("PSC", "UC", "TR")
    legend_contracts: list[dict[str, Any]] = []
    legend_y_fractions = {"PSC": 0.94, "UC": 0.86, "TR": 0.78}
    for mode in modes:
        legend_y = float(panel["ymax"]) * legend_y_fractions[mode]
        plot_numbers = plot_numbers_by_mode[mode]
        legend_text = "".join(f"\\l({number})" for number in plot_numbers) + f" {mode}"
        legend = layer.add_label(legend_text, 0.055, legend_y)
        legend_name = f"fig3_legend_{panel['name']}_{mode.lower()}"
        _name_label(legend, legend_name, 31.0)
        labels.append(legend_name)
        legend_contracts.append({
            "object_name": legend_name,
            "layer_index": layer_index,
            "plot_numbers": plot_numbers,
            "expected_plot_line_style": LINE_STYLES[mode],
            "text_contains": mode,
        })
    label_y = {temp: panel["series"][temp]["PSC"]["y"][-1] for temp in panel["series"]}
    for temperature, y_value in label_y.items():
        label = layer.add_label(f"{temperature}°C", 0.92, float(y_value))
        name = f"fig3_temp_{panel['name']}_{temperature}"
        _name_label(label, name, 31.0, color=COLORS[temperature], bold=True)
        labels.append(name)
    disable_speed_mode(layer)
    return plot_count, [book_name], labels, plot_contracts, source_groups, legend_contracts


def build(op: Any, candidate_params: dict[str, Any]) -> dict[str, Any]:
    fresh_source = load_fresh_figure_data(candidate_params, "fig3")
    panels = fresh_source["data"]["panels"]
    page_size_inches = (12.45, 9.0)
    page = create_hidden_graph_page(op, lname="Fig3_source_calibrated_four_panel", template="LINE")
    page.lt_exec(page_dot_command(*page_size_inches, page.get_float("resx"), page.get_float("resy")))
    layers = [page[0], page.add_layer(), page.add_layer(), page.add_layer()]
    counts: dict[int, int] = {}
    books: list[str] = []
    names_by_layer: dict[int, list[str]] = {}
    contracts: dict[str, dict[str, Any]] = {}
    plot_contracts: list[dict[str, Any]] = []
    source_groups: list[dict[str, Any]] = []
    subplot_contracts: list[dict[str, Any]] = []
    legend_contracts: list[dict[str, Any]] = []
    for index, (layer, panel) in enumerate(zip(layers, panels)):
        count, panel_books, names, panel_plot_contracts, panel_source_groups, panel_legend_contracts = _add_panel(op, layer, panel, index)
        counts[index] = count
        books.extend(panel_books)
        names_by_layer[index] = names
        contracts.update({name: {"attach": 2} for name in names})
        plot_contracts.extend(panel_plot_contracts)
        source_groups.extend(panel_source_groups)
        legend_contracts.extend(panel_legend_contracts)
        subplot_contracts.append({
            "subplot_id": f"fig3_panel_{panel['name']}",
            "layer_index": index,
            "expected_plot_count": count,
            "worksheet_books": panel_books,
            "worksheet_names": ["Sheet1"],
        })
    visibility = reveal_graph_page(page)
    return {
        "page_name": "Fig3_source_calibrated_four_panel",
        "expected_plot_count": sum(counts.values()),
        "expected_plot_count_by_layer": counts,
        "route": "worksheet_backed_source_calibrated_four_layer_line",
        "canvas_size": (1245, 900),
        "page_size_inches": page_size_inches,
        "required_worksheet_books": books,
        "direct_worksheet_plot_contracts": plot_contracts,
        "subplot_worksheet_contracts": subplot_contracts,
        "legend_plot_reference_contracts": legend_contracts,
        "source_geometry_groups": source_geometry_contract(source_groups),
        "required_graphobject_names_by_layer": names_by_layer,
        "required_graphobject_contracts": contracts,
        "expected_graphobject_count": len(contracts),
        "axis_contract": [],
        "construction_visibility": visibility,
        "reproduction_mode": (
            "fresh_source_reconstructed_approximate"
            if fresh_source["source_data_policy"] == "fresh_extract"
            else "validated_reuse_reconstructed_approximate"
        ),
        "source_data_policy": fresh_source["source_data_policy"],
        "data_provenance": "hash-verified AA2195 Fig. 3 source-bundle data",
        "fresh_source_data_sha256": fresh_source["data_sha256"],
        "fresh_source_bundle_sha256": fresh_source["bundle_data_sha256"],
        "fresh_source_pdf_sha256": fresh_source["source_pdf_sha256"],
        "font_profile": FIG3_FONT,
        "font_sizes": {"axis_tick": 32.0, "axis_title": 38.0, "panel": 38.0, "legend": 31.0, "temperature": 31.0},
        "candidate_params": candidate_params,
    }
