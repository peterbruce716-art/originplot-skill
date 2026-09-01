# OriginPlot v5.3 Semantic Figure Benchmark Protocol

OriginPlot v5.3 upgrades the pass gate from "Origin produced an image" to six independent checks:

- L1 structure: graph pages, layers, plots, matrices, object counts.
- L2 data: workbook/matrix binding, column roles, category groups, stack relationships.
- L3 geometry: page size, panel boxes, axis frames, object coordinates.
- L4 style: colors, line widths, fonts, fills, dash styles, legend/colorbar style.
- L5 semantics: panel labels, stage markers, legends, captions, arrows, region labels.
- L6 visual: MAE, RMSE, nonwhite density, edge F1, ROI-level image evidence.

Any blocking failure keeps the benchmark failed even when the visual MAE is low.

## Active Recipes

### recipe.schematic.dual_panel_curve.v1

Used for Fig15-like mechanism schematics. Required gates:

- One graph page.
- Two panel layers.
- Curve shape evidence for each panel.
- Critical semantic object coverage equals 1.0.
- Axis arrows, vertical guides, stage circles, panel labels, and legend text are named Origin objects.

### recipe.bar.grouped_stacked_three_panel.v1

Used for Fig16-like grouped stacked bar schematics. Required gates:

- One graph page.
- Three panel layers or an equivalent verified panel layout.
- Seven stage groups across PSC/CP/TR.
- WH/DRV/DRX stack semantics.
- Legend, group boxes, H/S relation labels, and stage markers exist as named editable objects.

If grouped stacked columns are not implemented, the benchmark must report `PLOT_FAMILY_NOT_IMPLEMENTED`.

### recipe.contour.discrete_three_panel.v1

Used for Fig12-like contour figures. Required gates:

- One graph page.
- Three layers.
- Three contour plots from matrix or gridded XYZ data.
- Three discrete colorbars.
- Contour lines, contour labels, and GF/GR/GF+GR text labels.

If a run produces three separate graph pages for the three panels, structure fails before visual scoring can pass.

## Evidence Layout

Each benchmark run should keep evidence separate from the core skill package:

```text
benchmarks/<figure_id>/<run_id>/
  source_crop.png
  pre_save.png
  post_reopen.png
  result.opju
  figurespec.json
  compiled_ir.json
  operation_plan.json
  inspection.json
  qa_report.json
  semantic_benchmark_report.json
  deviation_ledger.json
  registered_export.png
  alpha_overlay.png
  absolute_diff.png
  edge_overlay.png
  comparison_board.png
```

The core skill ZIP must not include run evidence, raster images, OPJU files, caches, or local capability outputs.
