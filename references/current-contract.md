# Current Contract

This is the active OriginPlot v5.8.9-p18 contract, distributed by release v5.8.9-p18.2. The release revision does not alter the p18 live-evidence identity. Read `release_version`, `contract_version`, and `evidence_version` from `version.json`; older protocol files are inputs only where a current script or schema explicitly consumes them.

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

The five named AA2195 routes have a batch-level gate in `scripts/audit_five_figure_batch.py`. It rejects incomplete figure sets, Origin PID drift, mixed skill versions, inherited construction evidence, a missing/invalid source-data gate, and any figure whose reopened structure, visual gate, or release status is false. This audit supplements per-figure metrics; it does not relax them.

## Provenance

- `live_same_run` is eligible only when one run creates the OPJU, pre-save export, post-reopen export, readback, visual metrics, and manifest with consistent IDs and hashes.
- `inherited_diagnostic` covers copied OPJUs, seed files, old exports, and cross-run comparisons. It cannot pass.
- The five-figure live runner accepts only a new or empty output root. It records `fresh_output_root_verified=true` and fails with `E126_STALE_OUTPUT_ROOT` before Origin attach when prior files are present. Old OPJUs, exports, Worksheets, and readbacks may be comparators only; they cannot enter the new run directory.
- The five-figure runner declares `source_data_policy` as `fresh_extract`, `validated_reuse`, or `validated_crop_reextract`. Fresh extraction requires `-SourcePdf`. Both reuse modes require `-ReuseBatchRoot`; `build_validated_data_reuse_record.py` accepts only a prior batch with a clean five-figure audit and per-figure structure, visual, live, provenance, and release passes. `validated_crop_reextract` additionally runs `reextract_validated_source_bundle.py`, which may change only Fig14 data using the hash-verified Fig14 crop and must retain every unrelated data hash. The worker verifies parent manifest, bundle, crop, reuse-record, and per-figure data hashes before Origin attach, otherwise it fails with `E128_SOURCE_DATA_REUSE_REJECTED`.
- An explicit user request to reproduce again, re-digitize, or not use old data forces `fresh_extract`. In that mode the batch must read the original PDF into its own new output root, the source manifest must declare `fresh_extraction=true` without parent/reuse/validated-source lineage, and no prior extracted data may feed construction. Historical artifacts remain diagnostic comparators only.
- Validated reuse applies only to curves, markers, error bars, fields, bar segments, and their source crops. The current run must still build new Worksheets/OPJUs, save, detach, reopen, read back, export, and pass visual gates. Old OPJUs, exports, readbacks, and metrics cannot enter the new run as pass evidence.
- Approximate reconstruction must be labelled `digitized_approximate`, `semantic_reconstruction`, or `reconstructed_approximate`, never `source_exact`.

## Editable route gate

- A formal live run has one administrator privilege envelope from initial preflight through template retrieval/inspection, candidate materialization, Origin build/save/reopen/readback/export, evidence packaging, and cleanup. `admin_preflight.json` must show `is_admin=true`; no non-administrator helper or inherited artifact can enter the run.
- Paper-like reproduction starts with an official OriginLab Graph Gallery search and a local official/installed-template search. The run records inspected candidates and evidence before construction.
- A single search, parser, redirect, or download failure cannot close template discovery. The search record must preserve a bounded retry matrix with at least three failed attempts per exhausted official URL, at least two retrieval methods, alternate semantically close candidates when available, content/ZIP/SHA256 validation, and both local searches. Retrying stops when an attempt succeeds. A successful download still requires compatible Origin open/reopen inspection.
- Fig12/Fig15/Fig16 candidates reference a validated `originplot.template_search_record.v1`; the worker records its SHA256 and selected template IDs in the manifest.
- Data-bearing and geometry-bearing Plots use direct Origin Worksheet-to-Plot bindings.
- Continuous curves, NaN-separated paths, categorical fields, and local fills declare `originplot.source_geometry_groups.v1`. Each group has one canonical source; deterministic plot views remain in the same reopened Workbook/Worksheet and GraphObject views retain an explicit source derivation plus object gate.
- A workbook inventory without live plot binding readback is insufficient.
- Every data-bearing subplot declares `subplot_worksheet_contracts`. Reopen validation records each subplot ID and layer, its exact editable plot count, the declared long-name Workbook and resolved Origin short-name alias, Worksheet name, and every X/Y(/Z) column binding. Missing layers, swapped panel workbooks, unbound plots, or aggregate-only evidence fail closed.
- Column/bar FigureSpecs declare `column_arrangement` per layer as `side_by_side`, `cumulative_stack`, or `nested_overlap`. `nested_overlap` is noncumulative: all series share the zero baseline, wider columns render behind narrower columns, and plot order plus per-series width/gap settings are contractual. Touching columns alone are not evidence of stacking.
- Every identifiable morphology whose proportions affect source fidelity declares a `morphology_ratio_contracts` entry before construction. The contract identifies its scope, metric, normalization reference, expected ratios, tolerance, audit stage, and any visible ordering. This applies generically to nested widths, stacked shares, panel/object dimensions, gaps, regional occupancy, and other measurable shape relationships. Post-reopen final-size export or declared reopened-native-geometry measurements must report normalized actual ratios and deviations. Missing declarations, missing measurements, or out-of-tolerance ratios fail the visual-structure gate.
- In Origin 2022, native Y error bars serialize as a type-203 column plus a separate type-231 error plot. Every contract declares `binding_mode`. In default `dataset_linked` mode (`colyerr`), the error plot's X dataset/column resolves to the column plot's Y dataset/column and its Y column is the declared Error column. In `implicit_error_column` mode, used for grouped or intentionally overlapped columns created before their error plots, the appended type-231 member must follow its corresponding column, share its Workbook/Worksheet, and reopen with the declared Error column as both X and Y; same-run visual QA must also prove that Origin placed its caps on the corresponding bar tops. Count both plots and validate them with `validate_native_yerror_pairs`; never accept a visually similar line path as native YErr. Record the native error-cap width control and require the rendered cap to be strictly narrower than the corresponding visible column at final export size.
- Fig12 live readback also verifies each reopened type-243 plot's exact declared nonuniform contour levels and zero minor levels; plot type and XYZ binding do not substitute for this check.
- Pixel traces, source-image pages, and raster backgrounds are forbidden as final editable graphs.
- Geometry-only GraphObjects are not Plots. They require a verified editable object type and explicit post-reopen type/geometry contracts. Fig12 type-34 overlays are source-derived visual geometry imported through unique transient SVG files; the underlying contour data remains Worksheet-bound and the transient files are deleted immediately after import.
- Legends are plot-derived editable Origin labels, not independent datasets. Fig3 uses `\l(plot)` references to its actual colored PSC/UC/TR curves; Fig14 references its line/marker plots; Fig16 references its real WH/DRV/DRX native columns. A legend-only Workbook, Worksheet, plot, or swatch-data column is forbidden.
- Fig16's reopened export calibrates the plot-reference samples as geometry, not merely text anchors: WH/DRV share one 2 px black border, DRV/DRX retain a 3 px white gap, and the first border remains inside the white page.
- Fig14 uses nine direct Worksheet-backed plots: three NaN-separated editable lines, three zero-line-width marker overlays, and three editable error paths. This separation preserves dashed UC/TR semantics across Origin 2022 save/reopen while keeping every data-bearing element independently editable.
- Fig14 declares `plot_style_contracts` for its three PID 202 marker overlays. Post-reopen LabTalk shape/size readback must return shapes 1/2/3 and size 10.5 with `plot_style_validation=ok`; missing or drifted marker semantics fail both the figure structure gate and the five-figure batch audit.
- The global direct-plot Worksheet budget is 5,000 rows per figure, verified after reopen.
- Reopened `source_geometry_group_validation`, `subplot_worksheet_validation`, and every declared `plot_style_validation` are hard structure gates. Missing consumers, cross-Worksheet views, wrong declared columns, duplicate canonical consumers, undeclared derivations, missing editable subplot layers, a subplot bound to another panel's Workbook, or persisted style drift fail closed.

## Fail-closed conditions

Fail or remain incomplete when required inputs are missing, the requested builder is unknown, session policy is violated, OPJU reopen fails, a declared plot is unbound, a declared Fig12 contour level drifts after reopen, the row budget is exceeded, evidence is inherited, exports are blank, or required visual/semantic gates fail. A demo-watermark result invalidates the entire run. Its manifest must require a new-run administrator restart from preflight and must prohibit reuse of that run's OPJU, exports, readback, run ID, and output root.

Stable codes include `E100_SCHEMA_INVALID`, `E120_ENVIRONMENT_MISMATCH`, `E121_ATTACH_POLICY_VIOLATION`, `E122_ORIGIN_DEMO_EXPORT_BLOCKED`, `E126_STALE_OUTPUT_ROOT`, `E127_FRESH_SOURCE_REQUIRED`, `E128_SOURCE_DATA_REUSE_REJECTED`, `E130_TEMPLATE_SEARCH_REQUIRED`, `E131_TEMPLATE_RETRIEVAL_EXHAUSTED`, `E220_BUILD_FAILED`, `E300_ORIGIN_ATTACH_FAILED`, `E400_STRUCTURE_MISMATCH`, `E410_SERIALIZATION_DRIFT`, `E420_VISUAL_MISMATCH`, `E440_PLOT_FAMILY_NOT_IMPLEMENTED`, `E470_LIVE_SAME_RUN_REQUIRED`, `E480_EVIDENCE_PACKAGE_INCOMPLETE`, `E510_NO_IMPROVEMENT`, `E540_PAGE_UNIT_SCALE_MISMATCH`, and `E541_LAYER_UNIT_SCALE_MISMATCH`.

## Required live outputs

A promoted run includes `candidate.opju`, pre-save and post-reopen Origin exports, `candidate_readback.json`, `candidate_visual_metrics.json`, `candidate_manifest.json`, and the standard evidence directory. Reports must distinguish offline validation from live Origin E2E.
