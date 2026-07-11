# OriginPlot FigureSpec v5 Protocol

This protocol is the active contract for OriginPlot Skill v5.3 - Semantic Figure Benchmark.

## Schemas

- `originplot.figurespec.v5`: user-facing figure contract.
- `originplot.compiled_ir.v5`: compiler output that preserves the FigureSpec and normalized operation IDs.
- `originplot.operation_plan.v5`: ordered worker operations with adapter routes.
- `originplot.capabilities.v5`: route-first local capability profile.
- `originplot.inspection.v5`: clean-session OPJU inspection result.
- `originplot.run_manifest.v5`: final execution evidence and gate status.
- `originplot.artifacts.v1`: cross-process artifact handoff.
- `originplot.semantic_figure_benchmark.v1`: six-layer semantic benchmark input.
- `originplot.deviation_ledger.v1`: structured blocking/nonblocking deviation ledger.

The JSON schemas live in `schemas/`.

## Operation IDs

All operation IDs must come from `operation_registry/operation_registry_v1.json`. Adapters, recipes, patches, and QA reports must refer to the same IDs.

## Runtime Gates

`overall_status` is `pass` only when live execution makes all of these gates `pass`:

- `preflight_status`
- `build_status`
- `round_trip_status`
- `structure_status`
- `serialization_status`
- `visual_status`
- `semantic_benchmark_status`

`incomplete` means evidence is missing. `failed` means a stable error code is recorded. Neither state may be described as visually close or complete.

Dry-run must return `overall_status=incomplete`; it may set `simulation_status=pass` but cannot satisfy build, round-trip, structure, serialization, or visual gates.

## v5.3 Recipe Fields

Complex paper figures should set `figure.recipe` and provide `required_objects`, `rois`, and `benchmark`.

Active recipes:

- `recipe.schematic.dual_panel_curve.v1`
- `recipe.bar.grouped_stacked_three_panel.v1`
- `recipe.contour.discrete_three_panel.v1`

`required_objects` defines semantic coverage gates such as `panel_label`, `axis_arrow`, `stage_marker`, `legend_entry`, `group_box`, `colorbar_title`, `region_label`, and `contour_label`.

`rois` defines panel, legend, colorbar, caption, and object regions that must be scored independently. Whole-image scores cannot override ROI or semantic failures.

`benchmark.path` points to an `originplot.semantic_figure_benchmark.v1` JSON file consumed by `scripts/semantic_figure_benchmark.py`.

## Six-Layer Benchmark Gate

The semantic benchmark report contains:

- `structure_score`
- `data_score`
- `geometry_score`
- `style_score`
- `semantic_coverage`
- `visual_score`

Any blocking failure in `deviation_ledger.json` fails the figure even when `visual_score` is high. Typical blocking failures include wrong graph page count, missing required semantic objects, missing stacked bar groups, missing colorbars, missing contour labels, and missing legend objects.

## Workers

Build and inspect must be separate runtime entrypoints:

- `scripts/originplot_orchestrator.py`
- `scripts/origin_build_worker.py`
- `scripts/origin_inspect_worker.py`
- `scripts/qa_controller.py`

The local file-queue agent calls `scripts/originplot_orchestrator.py` and forwards adapter mapping/config files. Workers exchange only through `run_artifacts.json`.

## Live Line Vertical Slice

The first supported live slice is Origin 2022, one workbook, one worksheet, one graph page, one layer, and one line plot. Use:

- `examples/originplot_figurespec_v5_minimal.json`
- `examples/data/fig_demo_line.csv`
- `examples/adapter_modules_v5_2.example.json`
- `examples/adapter_configs_v5_2.example.json`

Run `origin_doctor.py --mode live_originpro` to generate machine-local capabilities before live execution.

## v5.3 Benchmark Recipes

Use these example contracts as starting points:

- `examples/benchmarks/fig15_dual_panel_curve_benchmark.example.json`
- `examples/benchmarks/fig16_grouped_stacked_bar_benchmark.example.json`
- `examples/benchmarks/fig12_discrete_contour_benchmark.example.json`

## Migration

Legacy v2/v3/v4 artifacts must run through `migration/*_to_v5.py`. Silent execution of old plans is not allowed.
