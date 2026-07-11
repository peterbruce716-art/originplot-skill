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

## Provenance

- `live_same_run` is eligible only when one run creates the OPJU, pre-save export, post-reopen export, readback, visual metrics, and manifest with consistent IDs and hashes.
- `inherited_diagnostic` covers copied OPJUs, seed files, old exports, and cross-run comparisons. It cannot pass.
- Approximate reconstruction must be labelled `digitized_approximate`, `semantic_reconstruction`, or `reconstructed_approximate`, never `source_exact`.

## Editable route gate

- Paper-like reproduction starts with an official OriginLab Graph Gallery search and a local official/installed-template search. The run records inspected candidates and evidence before construction.
- Fig12/Fig15/Fig16 candidates reference a validated `originplot.template_search_record.v1`; the worker records its SHA256 and selected template IDs in the manifest.
- Data-bearing and geometry-bearing plots use direct Origin Worksheet-to-Plot bindings.
- A workbook inventory without live plot binding readback is insufficient.
- Pixel traces, source-image pages, and raster backgrounds are forbidden as final editable graphs.
- GraphObjects may carry text where the benchmark contract permits it; data geometry remains Worksheet-bound.
- The global direct-plot Worksheet budget is 5,000 rows per figure, verified after reopen.

## Fail-closed conditions

Fail or remain incomplete when required inputs are missing, the requested builder is unknown, session policy is violated, OPJU reopen fails, a declared plot is unbound, the row budget is exceeded, evidence is inherited, exports are blank, or required visual/semantic gates fail.

Stable codes include `E100_SCHEMA_INVALID`, `E120_ENVIRONMENT_MISMATCH`, `E121_ATTACH_POLICY_VIOLATION`, `E122_ORIGIN_DEMO_EXPORT_BLOCKED`, `E130_TEMPLATE_SEARCH_REQUIRED`, `E220_BUILD_FAILED`, `E300_ORIGIN_ATTACH_FAILED`, `E400_STRUCTURE_MISMATCH`, `E410_SERIALIZATION_DRIFT`, `E420_VISUAL_MISMATCH`, `E440_PLOT_FAMILY_NOT_IMPLEMENTED`, `E470_LIVE_SAME_RUN_REQUIRED`, `E480_EVIDENCE_PACKAGE_INCOMPLETE`, `E510_NO_IMPROVEMENT`, `E540_PAGE_UNIT_SCALE_MISMATCH`, and `E541_LAYER_UNIT_SCALE_MISMATCH`.

## Required live outputs

A promoted run includes `candidate.opju`, pre-save and post-reopen Origin exports, `candidate_readback.json`, `candidate_visual_metrics.json`, `candidate_manifest.json`, and the standard evidence directory. Reports must distinguish offline validation from live Origin E2E.
