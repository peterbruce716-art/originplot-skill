# Current Contract

This is the active OriginPlot v5.8.9-p14 contract. Older protocol files are inputs only where a current script or schema explicitly consumes them.

## Result semantics

Every candidate manifest exposes these independent fields:

- `command_success`: input validation or execution completed without a worker error.
- `structure_pass`: the reopened OPJU satisfies declared page, layer, object, Worksheet, row-budget, and direct-binding contracts.
- `visual_pass`: same-run visual gates passed. It is false for dry-run.
- `live_origin_verified`: a licensed Origin run saved, released, reopened, inspected, and exported the editable project.
- `pass_eligible`: all required live, structure, visual, provenance, and artifact gates passed.
- `overall_status`: `planned_not_executed`, `offline_validated`, `live_structure_pass`, `live_visual_pass`, `incomplete`, or `failed`.

`command_success` never implies reproduction success. Dry-run must use `planned_not_executed`, with all live, structure, visual, and pass-eligibility fields false.

## Batch audit

The five named AA2195 routes have a batch-level gate in `scripts/audit_five_figure_batch.py`. It rejects incomplete figure sets, Origin PID drift, mixed skill versions, inherited provenance, and any figure whose reopened structure, visual gate, or release status is false. This audit supplements per-figure metrics; it does not relax them.

## Provenance

- `live_same_run` is eligible only when one run creates the OPJU, pre-save export, post-reopen export, readback, visual metrics, and manifest with consistent IDs and hashes.
- `inherited_diagnostic` covers copied OPJUs, seed files, old exports, and cross-run comparisons. It cannot pass.
- The five-figure live runner accepts only a new or empty output root. It records `fresh_output_root_verified=true` and fails with `E126_STALE_OUTPUT_ROOT` before Origin attach when prior files are present. Old OPJUs, exports, Worksheets, and readbacks may be comparators only; they cannot enter the new run directory.
- Approximate reconstruction must be labelled `digitized_approximate`, `semantic_reconstruction`, or `reconstructed_approximate`, never `source_exact`.

## Editable route gate

- Paper-like reproduction starts with an official OriginLab Graph Gallery search and a local official/installed-template search. The run records inspected candidates and evidence before construction.
- Fig12/Fig15/Fig16 candidates reference a validated `originplot.template_search_record.v1`; the worker records its SHA256 and selected template IDs in the manifest.
- Data-bearing and geometry-bearing Plots use direct Origin Worksheet-to-Plot bindings.
- Continuous curves, NaN-separated paths, categorical fields, and local fills declare `originplot.source_geometry_groups.v1`. Each group has one canonical source; deterministic plot views remain in the same reopened Workbook/Worksheet and GraphObject views retain an explicit source derivation plus object gate.
- A workbook inventory without live plot binding readback is insufficient.
- Every data-bearing subplot declares `subplot_worksheet_contracts`. Reopen validation records each subplot ID and layer, its exact editable plot count, the declared long-name Workbook and resolved Origin short-name alias, Worksheet name, and every X/Y(/Z) column binding. Missing layers, swapped panel workbooks, unbound plots, or aggregate-only evidence fail closed.
- Fig12 live readback also verifies each reopened type-243 plot's exact declared nonuniform contour levels and zero minor levels; plot type and XYZ binding do not substitute for this check.
- Pixel traces, source-image pages, and raster backgrounds are forbidden as final editable graphs.
- Geometry-only GraphObjects are not Plots. They require a verified editable object type and explicit post-reopen type/geometry contracts. Fig12 type-34 overlays are source-derived visual geometry imported through unique transient SVG files; the underlying contour data remains Worksheet-bound and the transient files are deleted immediately after import.
- Legends are plot-derived editable Origin labels, not independent datasets. Fig3 uses `\l(plot)` references to its actual colored PSC/UC/TR curves; Fig14 references its line/marker plots; Fig16 references its real WH/DRV/DRX native columns. A legend-only Workbook, Worksheet, plot, or swatch-data column is forbidden.
- Fig16's reopened export calibrates the plot-reference samples as geometry, not merely text anchors: WH/DRV share one 2 px black border, DRV/DRX retain a 3 px white gap, and the first border remains inside the white page.
- Fig14 uses nine direct Worksheet-backed plots: three NaN-separated editable lines, three zero-line-width marker overlays, and three editable error paths. This separation preserves dashed UC/TR semantics across Origin 2022 save/reopen while keeping every data-bearing element independently editable.
- The global direct-plot Worksheet budget is 5,000 rows per figure, verified after reopen.
- Reopened `source_geometry_group_validation` and `subplot_worksheet_validation` are hard structure gates. Missing consumers, cross-Worksheet views, wrong declared columns, duplicate canonical consumers, undeclared derivations, missing editable subplot layers, or a subplot bound to another panel's Workbook fail closed.

## Fail-closed conditions

Fail or remain incomplete when required inputs are missing, the requested builder is unknown, session policy is violated, OPJU reopen fails, a declared plot is unbound, a declared Fig12 contour level drifts after reopen, the row budget is exceeded, evidence is inherited, exports are blank, or required visual/semantic gates fail.

Stable codes include `E100_SCHEMA_INVALID`, `E120_ENVIRONMENT_MISMATCH`, `E121_ATTACH_POLICY_VIOLATION`, `E122_ORIGIN_DEMO_EXPORT_BLOCKED`, `E126_STALE_OUTPUT_ROOT`, `E130_TEMPLATE_SEARCH_REQUIRED`, `E220_BUILD_FAILED`, `E300_ORIGIN_ATTACH_FAILED`, `E400_STRUCTURE_MISMATCH`, `E410_SERIALIZATION_DRIFT`, `E420_VISUAL_MISMATCH`, `E440_PLOT_FAMILY_NOT_IMPLEMENTED`, `E470_LIVE_SAME_RUN_REQUIRED`, `E480_EVIDENCE_PACKAGE_INCOMPLETE`, `E510_NO_IMPROVEMENT`, `E540_PAGE_UNIT_SCALE_MISMATCH`, and `E541_LAYER_UNIT_SCALE_MISMATCH`.

## Required live outputs

A promoted run includes `candidate.opju`, pre-save and post-reopen Origin exports, `candidate_readback.json`, `candidate_visual_metrics.json`, `candidate_manifest.json`, and the standard evidence directory. Reports must distinguish offline validation from live Origin E2E.
