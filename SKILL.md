---
name: originplot
description: "Use when a task requires Origin or OriginPro: editable OPJU projects, live same-run Origin evidence, Graph Gallery/template selection, originpro/LabTalk adapters, workbook/matrix/graph automation, OPJU save/reopen/export, inspection, visual QA, or Origin attach/runtime troubleshooting."
---

# originplot Skill

OriginPlot Skill v5.8.9-p13 - Acceptance Hardening and Fig12 Targeted Optimization. The active protocol set is `originplot.figurespec.v5`, `originplot.compiled_ir.v5`, `originplot.operation_plan.v5`, `originplot.run_manifest.v5`, `originplot.capabilities.v5`, `originplot.inspection.v2`, `originplot.inspection.v5`, `originplot.qa_report.v1`, `originplot.artifacts.v1`, `originplot.semantic_figure_benchmark.v1`, `originplot.benchmark_actual.v1`, `originplot.visual_evidence.v2`, `originplot.operation_maturity.v1`, `originplot.benchmark_evidence_package.v1`, `originplot.deviation_ledger.v1`, `originplot.visual_editable_acceptance.v1`, `originplot.official_template_reuse_truth.v1`, and `originplot.origin_object_readback.v1`.

Older v2/v3/v4 artifacts are legacy inputs only and must pass through an explicit migration report before execution. This is a Verified Origin Runtime skill: it exists to create editable Origin projects, not Python/R redraws.

## Core Principle

Use this skill only for Origin/OriginPro reproduction and automation. The deliverable is an editable Origin project (`.opju`) with workbook or matrix data, Origin graph pages, layers, plots, axes, legends, annotations, export evidence, and a fail-closed manifest. Do not use this skill for open-code redraw workflows; route those tasks to `scientific-figure-reproduction`.

For formal benchmark claims, v5.8 allows only two provenance states:

- `live_same_run`: the current run created the OPJU, exported pre-save evidence, released Origin, reopened the OPJU in a new session, inspected it, exported post-reopen evidence, and produced QA/benchmark artifacts from that same run.
- `inherited_diagnostic`: any seed OPJU, old export, old inspection, copied comparison board, or cross-run artifact. This can be useful for diagnosis, but it is never eligible for pass.

If any artifact has `inherited_from_run`, `verified_seed_opju_copy`, missing `run_id`, mismatched `run_id`, or `eligible_for_pass=false`, the overall benchmark status is capped at `incomplete`.

## v5.8 Visual Editable Closure

Use `visual_editable` as the default acceptance mode when a paper figure does not publish raw data or a source Origin project. This mode requires an editable OPJU and a same-run Origin export that is visually close to the source crop, while explicitly marking data as `digitized_approximate`, `semantic_reconstruction`, or `reconstructed_approximate`. Never call this `source_exact`.

Every figure-specific OPJU must contain only workbook/matrix data, declared editable base graph pages, and editable Origin native graph families, worksheet-backed plots/paths, matrices, text/labels/arrows/boxes, or verified template objects. The final OPJU must not contain source image pages, pixel-trace pages, black/white diagnostic pages, copied preview pages, failed probe pages, or GraphObject/pixel-canvas primitive pages as the primary result.

The default execution route is official-template/native-layer first for `native_chart` figures and official-template-informed worksheet-backed semantic objects for `semantic_schematic` figures. GraphObject primitives, source-coordinate pixel canvases, and hand-tuned rectangle/line primitives are diagnostic or fallback-only artifacts. They may be produced only behind an explicit diagnostic/fallback switch, must set `origin_primitive_pass_eligible=false`, and must not appear in `primary_editable_graph_pages`, `origin_rendered_export_targets`, or any pass-eligible visual benchmark target.

This is a route gate, not a preference. Before an Origin build starts, each figure spec must pass an official/native/semantic contract check: `figure_class` is either `native_chart` or `semantic_schematic`, `official_template_reuse_required=true`, a declared official template candidate with manifest GIDs, a primary route name containing the official/native/GID family for native charts or official/GID/semantic/worksheet family for semantic schematics, `origin_primitive_final_route_allowed=false`, and `primitive_route_policy=diagnostic_or_fallback_only_not_pass_eligible`. Any primary graph page or export target whose name contains diagnostic, fallback, primitive, pixel, source image, visual reference, or trace terms must fail fast as `E490_OPERATION_MATURITY_UNVERIFIED`.

Worksheet-backed overlays, native grouped/stacked columns, native contour/matrix layers, verified template annotations, and worksheet-driven Origin drawing objects are allowed in the primary route for `semantic_schematic` figures when the source figure is itself a schematic and the run records object tables, same-run Origin export, reopen validation, and visual QA. GraphObject pixel canvases, source-image traces, and unverified primitive pages remain diagnostic or emergency fallback only; they must be excluded from final OPJU primary pages, same-run rendered export targets, pass metrics, and any claim that the result is close to the source.

Route experiments are not automatically promoted. If a worksheet-driven drawing-object route or any other semantic object route is visually worse than the current best same-run Origin export, it must stay behind an explicit diagnostic switch and the default route must remain the better recorded route.

For semantic bar schematics, do not claim a closed worksheet line plot is a filled editable bar unless same-run Origin export proves the fill. In Origin 2022, line plots with polygon-like coordinate loops export as outline-only when only object properties are set. Use native column/stacked-column, verified donor bar objects, or worksheet-backed closed rectangles with LabTalk pattern fill commands (`set -pf`) that have passed a same-run probe/export; keep unverified closed-line or fill-area attempts diagnostic-only.

Official-template migration must be evidenced as object-family migration, not just a filename citation. Each run must record an `originplot.official_native_migration_contract.v1` entry with: official donor GIDs, donor project files and SHA256 records from the local downloader catalog, required Origin object families, implemented Origin object families, and blocking native gaps. It must also record `originplot.official_template_reuse_truth.v1` with `donor_project_opened`, `donor_graph_page_found`, `donor_object_tree_dumped`, and `donor_objects_transplanted`. If any of those truth fields are false, the route status is `official_template_reference_only`; do not name or describe it as official-template migration.

Origin text labels, axis titles, tick labels, legends, and colorbar labels are part of the native/template or semantic-schematic route only after their Origin 2022 export size and coordinate behavior is verified. v5.8.5 keeps Origin text labels gated off by default after same-run Origin 2022 evidence showed scale-attached labels can export at uncontrolled size. Keep label tables in the workbook/manifest, mark the affected text route as blocking, and only enable text labels after same-run export proves coordinate and font-size behavior.

## v5.8.5 Reconstruction Engine Patch

v5.8.4 freezes broad rule expansion and fixes implementation gates that previously made visual closure impossible:

- A deviation ledger blocks pass only when an item has `severity=blocking`. Approximate reconstructed data are a provenance warning in `visual_editable` mode, not an automatic blocking failure.
- Origin object readback must not rely only on `len(gl)`. It must try indexed plot enumeration and property probes; if a page expects editable plots and readback returns zero, the run records `E400_STRUCTURE_MISMATCH` and cannot pass visual or structure gates.
- Donor references are truth-gated. If `donor_project_opened`, `donor_object_tree_dumped`, or `donor_objects_transplanted` are false, primary route names must use `native_*_reconstruction` or `worksheet_semantic_*_reconstruction` with a `reference_family`, not `official_*_migration`.
- The correction loop must not re-export an unchanged page and call it optimization. Each iteration records a concrete clean-rebuild candidate parameter set; identical export/readback signatures stop with `E510_NO_IMPROVEMENT`.
- Fig12 uses a fixed three-region palette plan and must not silently fall back to continuous `Candy`/`Maple` palettes while claiming discrete source-like regions.
- Fig15 uses a two-layer semantic schematic route with panel-local worksheet paths and calibrated labels.
- Fig16 defaults to one semantic drawing-object family for bar rectangles, group boxes, and separators; text labels remain gated until Origin 2022 export size is verified. Worksheet overlay group boxes/separators must not be added again when drawing-object boxes are already present.

The build loop is mandatory:

```text
editable OPJU
-> same-run Origin export
-> source crop comparison
-> visual evidence board/diff/overlay
-> deviation ledger
-> bounded correction or explicit not-passed result
```

The correction loop must be real or stop. Every iteration records a `correction_parameter_snapshot` and export/readback signature. If two consecutive iterations have identical export SHA256, metrics, and object readback signatures, stop immediately with `E510_NO_IMPROVEMENT`; never repeat the same export several times and present it as refinement.

A run may be described as closer than baseline only when the same-run export improves the recorded baseline metrics. For this workspace's Fig. 12/15/16 benchmark, Run94 is the current comparator until a better validated run supersedes it.

## v5.8.6 Calibration and Clean Rebuild Gate

v5.8.6 treats run124 as the last uncalibrated baseline. The next valid implementation must not assume source-image pixels equal Origin page or layer units. Before text labels, GraphObjects, contour palettes, or plot readback can pass, the run must produce an Origin 2022 calibration profile from `scripts/origin_calibration_probe.py` or an equivalent same-run probe manifest.

- Mandatory probes: coordinate mapping, text metrics, plot readback, GraphObject readback, and contour palette. Missing or planned-only probe output caps the result at incomplete.
- Figure layers should use page-percent geometry and internal normalized `0..1` layer-scale coordinates. Source pixel tables may remain as provenance inputs, but final Origin object coordinates must be converted before graph construction.
- Fig15 is the first closure target: two visible source-proportional layers, both curves present, axis arrows/stage circles present, and text labels enabled only after the text probe passes. Normalized local paths are probe-gated; if a normalized export is blank or near-blank, default back to the visible source-coordinate worksheet path route.
- Fig16 defaults to worksheet-backed polygon/line objects with source-coordinate semantic geometry. Drawing-object rectangles and normalized layer-scale coordinates are probe-gated until the same-run GraphObject coordinate probe proves that rectangles, group boxes, and separators export with correct colors, white background, and geometry. `expected_plot_count=0` is not enough; post-reopen GraphObject readback must verify 21 bar rectangles, 3 group boxes, and 2 separators before a drawing-object route can pass.
- Fig12 must stop relying on an unverified `CONTOUR` template palette. It requires a proven three-region contour palette route before color-region or colorbar claims can pass.
- The correction loop must perform real clean rebuilds. If candidate parameters are only recorded and not applied in independent blank-project rebuilds, the run must stop with `E520_CLEAN_REBUILD_WORKER_REQUIRED`; repeated export of an unchanged page is forbidden.
- A clean rebuild candidate must emit its own OPJU, export PNG, readback JSON, visual metrics JSON, and candidate manifest. Promotion selects the best candidate by same-run evidence, not by report text.

## v5.8.7 Implementation Closure Patch

v5.8.7 converts the run127 diagnosis into executable gates. Do not add new protocol-only claims unless the scripts and tests prove the behavior.

- The global normalized-coordinate flag must not be a dead variable. Fig15 normalized mode is enabled by default and the manifest must record `fig15_two_layer_panel_route.coordinate_mode=normalized_0_1_panel_coordinates`. Labels, circles, guides, and curves must all use the same normalized local layer coordinate system.
- Fig15 source-coordinate mode is allowed only as an explicit fallback after the normalized route exports blank or fails coordinate calibration. A fallback run must record `normalized_route_fallback_reason`; it is not a pass-eligible improvement over the normalized route.
- Behavior tests must inspect generated payloads or manifests. String-only tests that merely search for default values are insufficient. Contract tests must assert the effective route values, blank-export gate, candidate uniqueness, and required error codes.
- `scripts/origin_calibration_probe.py` must produce a concrete profile. Dry-run mode may remain non-pass-eligible, but live mode must create an OPJU/probe plan, record five probe result objects, and fail closed with stable error codes only for the probe families that are not verified.
- `scripts/origin_candidate_worker.py` is the clean rebuild boundary. Each candidate must have a unique parameter SHA256 and must emit a candidate manifest. A live candidate is pass-eligible only after it builds from a blank project/session, saves OPJU, reopens, exports PNG, writes readback JSON, and writes visual metrics JSON.
- Fig16 closed-line pattern-fill plots are diagnostic-only because run127 produced a large unintended fill component. Default Fig16 must use verified GraphObject rectangles when `graphobject_readback_verified=true`, otherwise a donor-readback-verified native grouped/stacked-column route. Worksheet closed-line pattern fill must set `pass_eligible=false` and may not be the default.
- Fig16 QA must detect unexpected connected fill components. A single non-white or orange-like component covering more than 10% of the figure canvas fails with `E530_UNEXPECTED_FILL_COMPONENT`.
- Fig12 must separate categorical region fill from continuous contour lines. Palette claims require either a verified categorical contour profile or editable region polygons plus a separate editable colorbar object; pure red, pure blue, or purple dominant regions cannot pass as the AA2195 three-region palette.

## v5.8.7-p2 Execution-Layer Patch

v5.8.7-p2 is an execution patch over v5.8.7, not a new visual-success claim. It addresses the run128/run129 diagnosis by making candidate selection and probe language stricter:

- Select best evidence per figure, not per whole run. A final review package may combine `fig12_selected_from`, `fig15_selected_from`, and `fig16_selected_from` from different candidate runs, but every selected figure must carry its own same-run OPJU, Origin export, readback, visual metrics, and hard-gate result.
- Candidate selection runs hard gates before metrics: reject blank exports, missing expected semantic objects, unexpected legends/frames, and failed structure readback before calculating MAE/RMSE/nonwhite deltas. A low MAE blank export is never a candidate.
- `origin_calibration_probe.py` must not mark coordinate mapping or text metrics as verified merely because a minimal OPJU/PNG and one label were created. Such evidence is `minimal_smoke_pass`; full verification requires page/layer/export scale probes, post-reopen measurements, text-size probes, and plot/object readback.
- Fig15 must first pass a dedicated normalized single-curve probe with candidates A/B/C: default layer unit, `layer.unit=1` percent-box, and `set_float` percent-box without a unit override. Only a route that exports nonblank after reopen, has a detected line bbox, and has zero unexpected legends/axis titles can become the default normalized route.
- Fig15 legend removal must use both `legend -r;` and `label -r legend;`, and a post-reopen `unexpected_legend_count == 0` gate is required before visual scoring.
- Fig16 native grouped/stacked candidates must use the H/S row model: each stage has an H row with WH only and an S row with stacked DRV/DRX. The old three-series group model is not a valid GID399-style reproduction claim.
- Fig12 palette work must be gated by a separate contour palette probe over a 0/1/2 matrix. Test custom palette, categorical contour, level-fill colors, and controlled color scale; only a route preserving orange/green/blue after save/reopen and controlling/removing the default colorbar can support Fig12 palette claims.
- `origin_candidate_worker.py` is the clean rebuild boundary and must call a real single-figure builder entrypoint such as `build_origin_figure(...)`. A worker that only creates `op.new_graph(template="LINE")` is a smoke test and must return `E524_LIVE_CANDIDATE_WORKER_REQUIRED` or a non-promoted status.
- The clean rebuild plan schema for this patch is `originplot.clean_rebuild_candidate_plan.v587_p2`; it records `selection_scope=per_figure_independent_best_candidate`, hard-gate order, candidate SHA values, and required artifacts per candidate.

## v5.8.8 Post-Reopen Calibration Closure

v5.8.8 freezes Fig12/Fig15/Fig16 visual retuning until Origin 2022 persistence and readback are independently verified.

- Plot inspection must use `list(GLayer.plot_list())` as the primary route. `len(layer)` is not a plot count. Activate the layer, run LabTalk `layer -c`, read `count`, record both counts, and report any disagreement as `W402_PLOT_READBACK_DISAGREEMENT`.
- Every plot record must include index, type, Origin range/data binding when available, visibility when available, and key style properties. If `plot_list()` contains plots, inspection must never report zero plots.
- Calibration pass requires a saved OPJU to be fully released, reopened by `origin_calibration_inspect_worker.py` in a new hidden Origin session, read back, and exported again. Pre-save or same-session evidence fails with `E526_POST_REOPEN_EVIDENCE_REQUIRED`.
- The plot probe contains one line, two lines, one matrix contour, and one column plot. Expected post-reopen counts are exactly 1 and 2 for the line cases and at least 1 for contour and column.
- The GraphObject probe requires the named objects `probe_rect_01`, `probe_line_01`, `probe_text_01`, and `probe_circle_01`, including type, attachment, coordinates, colors/fill, and text when applicable.
- The text probe covers 6, 8, 10, and 12 pt for page, layer-frame, and layer-scale attachment. All 12 post-reopen cases need exported bounding boxes and pre/post coordinate deltas before labels are enabled in production figures.
- The contour palette probe uses a minimal 0/1/2 matrix and reports orange/green/blue IoU, dominant purple absence, default-red absence, color-scale control, and pre/post palette stability. Failed palette evidence blocks Fig12 color claims.
- `origin_candidate_worker.py` may load only the packaged `builders/aa2195` implementation. An undocumented workspace-relative builder or mandatory environment variable is a package failure.
- Packaged tests must pass through `scripts/run_all_tests.py` with zero skips, and plain `pytest` collection from the skill root must succeed. Existing run132 OPJUs remain diagnostic evidence and must not be overwritten.

## v5.8.9 Authorized Attach and Visual Closure

v5.8.9 applies the verified v5.8.8 calibration results to the AA2195 Fig. 12/15/16 production builders.

- When `attach_existing_authorized=true`, both build and post-save reopen phases must call `op.attach()` and release in `finally` with `op.detach()`. They must not call `op.set_show(False)` or `op.exit()`.
- Authorized attach must fail closed with `E121_ATTACH_POLICY_VIOLATION` if any phase silently switches to a hidden session. Hidden sessions remain diagnostic-only.
- The target OPJU must not already be open, and an active lock file blocks save/reopen.
- Formal reopen must be editable and saveable, not a read-only inspection shortcut. Before `op.open`, clear any read-only file attribute on the target `.opju`; call `op.open(..., readonly=False, asksave=False)`; immediately verify same-path save with `op.save(str(opju))`; and record `editable_open_evidence.same_path_save_verified_after_reopen=true`. A pass-eligible OPJU cannot be claimed from a read-only reopen.
- Every delivered graph page must open fitted to its Origin edit window. Execute `win -z0` before the first save and again after editable reopen, then save the same OPJU once more. Record both phases in `editable_view_evidence`. This is an edit-view zoom operation and does not change page geometry, layer geometry, or fixed export dimensions; leaving a small white page surrounded by a large gray graph-window workspace is not an acceptable editable handoff.
- Fig. 12 uses packaged source-calibrated matrices, explicit `xymap`, three native contour layers, discrete orange/green/blue regions, log strain-rate axes, and editable labels.
- Fig. 15 uses packaged source-calibrated two-panel worksheet paths for axes, guides, curves, stage circles, and editable labels in one normalized coordinate system.
- Fig. 16 may use named rectangle, line, ellipse, and text GraphObjects only because v5.8.8 verified their post-reopen coordinate and readback behavior. Every critical bar and group object must be named and read back. Unverified pixel traces or anonymous drawing primitives remain forbidden.
- Post-reopen export width must match the source crop width: Fig. 12 `805`, Fig. 15 `850`, and Fig. 16 `720` pixels.
- `candidate_visual_metrics.json` must contain canvas, MAE, RMSE, SSIM, layout, edge, color, bounding-box, registration, non-white, and `demo_cyan_ratio` results. Artifact existence alone is not visual QA.
- Canvas mismatch, demo markings, missing source crop, structure failure, or per-figure visual-threshold failure makes the candidate non-promotable.
- Reconstructed fields and schematic coordinates retain `reconstructed_approximate` provenance and must not be described as source-exact data.

## v5.8.9-p1 Page and Text Unit Hotfix

Origin 2022 unit handling is a hard contract. `page.width/page.height are dots`, not inches or export pixels. Compute physical page dots from the live page resolution: `page.width = width_inches * page.resx` and `page.height = height_inches * page.resy`. At 600 dpi, an 8.5 x 3.35 inch page is 5100 x 2010 dots. Writing `8.5` and `3.35` collapses the graph page; writing `850` and `335` creates only a 1.42 x 0.56 inch page and makes text/lines appear several times too large. `layer.unit=1 uses 0..100 page percent` for layer `left`, `top`, `width`, and `height`; `layer.unit=3` is centimeters and must not be used for percentage frames. Plot data may still use normalized `0..1` layer-scale coordinates. `text fsize is points`; use the intended 6-18 pt value directly after the physical page size is correct.

- Builders must read `page.resx/page.resy`, calculate dots from the declared physical size, and reject missing, zero, or inconsistent resolution with `E540_PAGE_UNIT_SCALE_MISMATCH`.
- Export width does not repair an incorrectly sized Origin page. Page dots, layer percent frames, plot coordinates, and text points must each be validated before save/reopen/export.
- Post-reopen QA must verify the exact source canvas, page aspect ratio, major-content bounding box, and plausible text bounding boxes. A graph concentrated in the upper-left corner or labels occupying a large fraction of a panel is a blocking scale failure.

## v5.8.9-p2 Fig15 Object Persistence Patch

Fig15 must use post-reopen object contracts, not only whole-page image similarity.

- Use the documented `layer.axis.showAxes`, `showLabels`, and `ticks` properties to suppress the template axes. Origin 2022 keeps native `arrow.show=0` in the verified attach/save/reopen probe, so the production route uses explicit worksheet arrowhead paths in the same normalized coordinate system as the curves. Post-reopen readback must show no default frame, ticks, or tick labels, and both worksheet arrowhead paths must remain present.
- Origin 2022 exported `add_label` text only for layer-scale attachment in the verified persistence probe; page and layer-frame attachments survived readback but were invisible. Therefore Fig15 uses a named scale-attached spanning caption in the left source-calibrated layer. Its name, `attach=2`, text, and unclipped caption ROI must survive save/reopen. Do not claim page attachment when the export is blank.
- Greek letters and subscripts use Origin escape sequences such as `\g(s)`, `\g(e)`, and `\-(p)`. ASCII substitutions such as `sigma`, `epsilon`, or `sigma_p` fail the Fig15 semantic text gate. Header stage circles and their descriptions are separate editable objects so title and description bounds cannot collapse into one label.
- The axis-arrow route must be machine-readable after reopen. Plain worksheet axis lines without the declared worksheet arrowhead paths do not satisfy the arrow contract.
- PSC and UC/TR curves use source-calibrated digitized centerline control points with `reconstructed_approximate` provenance. A dedicated curve-shape ROI must check the early hardening knee, peak/plateau level, and steady-state segment; plot existence alone is insufficient.
- Cyan demo markings are an Origin authorization/environment failure, never a styling defect. Record `E122_ORIGIN_DEMO_EXPORT_BLOCKED`, set `environment_blocked=true`, forbid promotion, and require a licensed authorized Origin session. Do not hide, crop, recolor, or cover the watermark in code.

## v5.8.9-p3 Readback and Shareability Patch

- Record each reopened plot's Origin type code, normalized plot family, visibility, line color/style/width, raw data range, workbook, worksheet, and X/Y columns when available. Preserve `unknown` rather than inventing a semantic family for an unverified type code.
- Normalize the Origin GraphObject type-name typo `Unknow` to `Unknown`, and map verified numeric object codes to `text`, `line`, `rectangle`, `ellipse`, or `polygon`.
- For Fig15, require every declared `fig15_*` object exactly once. Reject missing names, duplicate names, and undeclared `fig15_*` objects, while allowing unrelated Origin-generated objects and avoiding an exact total-object-count gate.
- When building a shareable review package, rewrite packaged artifact references in JSON to their package-relative POSIX paths. Do not emit machine-local absolute paths inside package JSON.
- Keep the Fig15 geometry, candidate parameters, canvas, layer frames, control points, labels, and thresholds frozen while resolving an Origin authorization gate. Demo cyan must be removed by using a properly licensed Origin environment, never by image masking or retuning.

## v5.8.9-p4 Default Administrator Attach Policy

Formal production runs default to administrator attach-existing from start to finish. The active Python/Codex process must be running with administrator privileges before importing `originpro`, constructing Origin COM objects, compiling live workers, building OPJUs, reopening OPJUs, exporting PNGs, or running post-reopen readback. The target Origin instance must already be the administrator-opened visible Origin process, and every formal phase must use `op.attach()` followed by `op.detach()` in `finally`.

Before importing `originpro`, formal builders must verify that a visible `Origin*` process exists. If no visible administrator-opened Origin process is available, return `E121_ATTACH_POLICY_VIOLATION`, set `origin_attach_not_attempted=true`, set `opju_generation_allowed=false`, and instruct the operator to open Origin as administrator. Do not auto-create hidden Origin sessions, do not use `OriginExt` constructors as a substitute, and do not let a missing visible process degrade into a generic COM failure.

Hidden sessions, newly created hidden Origin instances, `op.set_show(False)`, `op.exit()`, `OriginExt.ApplicationSI()`, and any route that silently starts a separate Origin process are diagnostic-only. They are forbidden on the default primary route and must set `pass_eligible=false` if explicitly enabled for troubleshooting. A formal run that requests `attach_existing_authorized=false` fails closed with `E121_ATTACH_POLICY_VIOLATION` before OPJU generation.

If administrator Python is not available, the worker must fail before importing or instantiating `originpro` or any Origin COM bridge. It must return `E120_ENVIRONMENT_MISMATCH`, set `origin_attach_not_attempted=true`, set `opju_generation_allowed=false`, and stop. Do not degrade this into a hidden-session fallback, seed OPJU fallback, copied OPJU, or surrogate export.

For Fig. 12/15/16 AA2195 production builders, the default session mode is `administrator_attach_existing_authorized_two_phase`: attach/build/save/detach, then attach/reopen/readback/export/detach. Any diagnostic hidden run must use an explicit `allow_diagnostic_hidden` switch, must be labeled `diagnostic_new_hidden_not_pass_eligible`, and cannot be promoted or used as same-run pass evidence.

Formal OPJU reopen paths must be editable, never read-only. Before `op.open(...)`,
clear the file read-only attribute when present; call
`op.open(path, readonly=False, asksave=False)`; immediately save back to the same
path; and record `editable_open_evidence` with `readonly_before`,
`readonly_after`, `readonly_attribute_cleared`,
`origin_open_readonly_requested=false`, and
`same_path_save_verified_after_reopen=true`. This applies to production builders,
inspection reopen, calibration readback workers, and any future official-template
round trip. A run that only opens a copied OPJU in read-only mode is diagnostic
only and cannot be promoted.

## v5.8.9-p5 Fig15 Freeze and Fig16 Object Contract

The licensed Run015 Fig15 evidence closed the environment gate with the unchanged Run010 candidate SHA256 `fc0fe92dc204e9b85105b12a6a2cecbb42cff4f91e2f4d9830842a23c19e7143`, `demo_cyan_ratio=0`, canvas `850 x 335`, and `pass_eligible=true`. The worker now treats this exact SHA as `fig15_status=frozen_regression_baseline` only when stricter no-regression gates also pass: `MAE <= 0.040`, `SSIM >= 0.810`, `layout >= 0.985`, `color >= 0.925`, `|dx| <= 4 px`, `|dy| <= 2 px`, and `demo_cyan_ratio <= 0.0005`. Current p10 Run047 preserves that candidate SHA, keeps `demo_cyan_ratio=0`, verifies `speed_mode_state.all_off=true`, and improves the frozen baseline evidence to `MAE=0.03250`, `SSIM=0.85278`, `layout=0.98878`, and `color=0.99378`. Text A/D/E experiments are diagnostic because they slightly degraded MAE/SSIM/edge/color versus Run015/Run047; do not promote them as defaults.

Fig16 no longer relies on a shallow total GraphObject count. The default semantic schematic route must create and read back all 59 controlled `fig16_*` objects exactly once: 21 bar rectangles, 3 group boxes, 3 baselines, 3 group labels, 2 H/S headers, 3 legend boxes, 3 legend labels, 7 stage circles, 7 stage labels, and 7 relation labels. Missing, duplicate, or undeclared `fig16_*` objects fail the graph-object contract, while unrelated Origin internal objects remain allowed. This contract preserves the calibrated GraphObject route and avoids reverting to the older native grouped-column diagnostic route unless a future same-run A/B comparison proves it is closer.

## v5.8.9-p6 Exact Layer Structure and Fig12 Reopen Contract

The structure gate now requires exact plot counts, both for the whole page and for each declared layer. Fig12 must reopen with one contour plot in each of three layers, Fig15 with five worksheet-backed plots in each of two layers, and Fig16 with zero plots in its GraphObject-only layer. Extra plots, missing plots, or a correct total distributed across the wrong layers fail the structure gate.

Fig12 labels are now controlled editable objects. Every panel marker, contour label, and mechanism label receives a stable `fig12_label_*` name, layer-scale attachment, and post-reopen presence contract. Panel and mechanism labels also preserve their semantic text. All three Fig12 layers must read back `y.type=2`, so a visually plausible export with a silently linearized strain-rate axis cannot pass.

## v5.8.9-p7 Fig16 Native Geometry and Visual Closure

Fig16 object existence is not a visual-success substitute. The Run019 diagnosis showed that LabTalk `draw` coordinate mutation could collapse rectangle heights, `label -a` arguments could leak into rendered text, and ellipse names could disappear after reopen even while a shallow object-count gate looked nearly complete.

- Fig16 rectangles, baselines, and stage circles use native `GraphObjects.Add` object families with verified type codes `8`, `4`, and `9`. Source-calibrated `x1/y1/x2/y2` values are written through object properties before styling. LabTalk `draw` remains fallback-only when the native collection is unavailable and is not pass-eligible without same-run persistence evidence.
- Fig16 semantic text uses `layer.add_label()` with an exact text payload, stable object name, `attach=2`, calibrated coordinates, and point size. Rendered text containing command fragments or coordinate arguments is a blocking failure.
- Origin may normalize drawing-object names to uppercase after reopen. Contract matching is case-insensitive, while duplicate-name and undeclared-prefix checks remain case-insensitive and strict.
- Fig16 requires a post-reopen axis contract with native axes, labels, ticks, and arrowheads hidden. Numeric default axes or tick labels fail structure and visual gates.
- The 59-object contract remains unchanged: 21 bar rectangles, 3 group boxes, 3 baselines, 3 group labels, 2 headers, 3 legend boxes, 3 legend labels, 7 stage circles, 7 stage labels, and 7 relation labels. The patch fixes creation and readback; it does not weaken the contract.
- Promotion requires a same-run visual comparison against the Fig16 source crop after the structure gate passes. Large bar-height errors, missing dashed group boxes, missing circles, misplaced legends, text collisions, or command-fragment text are blocking deviations even when all objects reopen.

## v5.8.9-p8 Fig16 Stacked Semantics and Visible Group Frames

v5.8.9-p8 converts the source-calibrated Fig16 geometry into the actual H/S schematic semantics visible in the paper figure:

- Every stage uses two horizontal slots: a left WH rectangle and a right stacked DRV/DRX column. DRV and DRX must share the same x bounds and meet exactly at one y boundary; gaps or overlaps fail the Fig16 geometry contract.
- The seven stages remain distributed as PSC stages 1-3, CP stages 1-2, and TR stages 1-2. Their source-pixel bboxes are versioned geometry inputs and must be changed only through a visual comparison iteration.
- PSC, CP, and TR group frames are blue dashed rectangles with no opaque fill. Transparent group frames must retain the requested blue outline; a later black-color assignment or an invisible transparent border is a regression.
- WH/DRV/DRX rectangles keep black outlines and their semantic fill colors. The baseline, group labels, relation labels, legend, and circled stage markers remain separate editable Origin objects under the unchanged 59-object contract.
- Run020 is the p7 diagnostic baseline for this patch: it passed the post-reopen structure gate but remained visually blocked because the DRV/DRX geometry was not contiguous and the blue dashed group frames were absent. p8 promotion requires a new same-run Origin export that improves those deviations.

## v5.8.9-p9 Fig16 Persistent Rectangle Geometry

Run022 proved that Origin 2022 rectangle objects do not preserve the requested
layer-scale height when positioned through `x1/y1/x2/y2` or LabTalk `draw -b`.
Those routes reopened with collapsed `y1 == y2` geometry and rendered short bars.
The verified persistent route is the native OriginExt rectangle object with
`SetX`, `SetY`, `SetDX`, and `SetDY`.

- Fig16 rectangles use center coordinates plus full layer-scale spans:
  `X=(x0+x1)/2`, `Y=375-(y0+y1)/2`, `DX=x1-x0`, and `DY=y1-y0`.
- Bar rectangles, group frames, and legend swatches must reopen with matching
  `x/y/dx/dy` values within the declared tolerance. Object existence alone is
  insufficient.
- If `GraphObjects.Add(8)` is unavailable, formal Fig16 construction fails with
  `E401_GRAPHOBJECT_READBACK_UNVERIFIED`. It must not silently fall back to
  LabTalk `draw -b`, because that route is known to distort rectangle height.
- Inspection records direct `GetX/GetY/GetDX/GetDY` and
  `GetLeft/GetTop/GetWidth/GetHeight` values in addition to legacy numeric
  properties.
- Run021 is the p8 comparator. p9 promotion requires a same-run post-reopen
  export with source-like bar heights and passing rectangle geometry contracts.

## v5.8.9-p10 Fig16 Visible Segmented Frames and Cyan QA

Run024 and Run025 proved two Origin 2022 drawing limitations that affect Fig16:
transparent rectangle outlines can disappear after save/reopen, and native
`lineStyle` values do not reliably export as dashed lines. The pass-eligible
Fig16 group frame route is therefore a set of short named editable line
segments, not a transparent rectangle or a single native dashed line.

- Group frames use segmented `GraphObjects.Add(4)` line objects with short
  names such as `fig16_f_psc_top_01`. Long controlled names can be truncated by
  Origin and then fail post-reopen name/geometry contracts.
- Readback contracts must verify each line segment's `x1/y1/x2/y2` geometry,
  not only object existence. Rectangle and ellipse contracts continue to verify
  center-span `x/y/dx/dy` geometry from `SetX`, `SetY`, `SetDX`, and `SetDY`.
- Stage circles use native ellipse objects positioned with the same center-span
  route and a white fill. Endpoint-style ellipse geometry is diagnostic-only
  because it can reopen/export as distorted slanted ovals.
- Demo-watermark QA uses a strict cyan detector: it must catch true cyan demo
  markings while ignoring the Fig16 DRV green fill. A broad `G>150 && B>150`
  mask is invalid because it falsely blocks licensed Fig16 exports.
- Fig16 relation text uses the source semantic relation `H≈S` where applicable;
  ASCII approximations such as `H~S` fail the semantic text contract.
- Run029 font probing showed the default `add_label` route already exports
  source-like serif text; unverified LabTalk font assignment must not be added
  to production labels. In particular, the non-string LabTalk font assignment
  can change labels to a visually wrong sans-serif style.
- Run030 is the current p10 Fig16 comparator: it passed same-run build,
  save/reopen, object readback, canvas, demo, and visual gates with
  `MAE=0.07650`, `SSIM=0.68975`, `layout=0.99039`, `color=0.87297`, and
  `demo_cyan_ratio=0`. It improves over Run028 by reducing excessive pure-black
  outline weight while preserving the visible segmented blue frames.
- Run031's attempted 6 px legend downshift was structurally valid but visually
  worse than Run030 (`MAE=0.07754`, `layout=0.97706`, `color=0.87155`), so it is
  a rejected experiment. Do not move the Fig16 legend away from the Run030
  geometry unless a future same-run candidate beats Run030.
- Run045's text/legend/stage upshift candidate was structurally valid and
  slightly improved edge/color, but it worsened MAE and SSIM
  (`MAE=0.07671`, `SSIM=0.68793`) relative to Run030, so it is a rejected
  diagnostic experiment. The bounded `fig16_tuning` parameter hook may remain
  for future A/B runs, but default geometry must stay at the Run030 positions
  until a same-run candidate beats Run030.
- Run046 keeps the Run030 default geometry and visual metrics exactly
  (`MAE=0.07650`, `SSIM=0.68975`, `layout=0.99039`, `edge=0.58238`,
  `color=0.87297`) while fixing post-reopen Speed Mode readback to
  `page.speedMode=0`, `layer.speedMode=0`, and `speed_mode_state.all_off=true`.
  Use Run046 rather than Run030 as the runtime-quality comparator when checking
  Speed Mode evidence.
- Run048 is the current default p10 Fig16 visual comparator. It applies the bounded
  bar-height tuning `fig16_tuning.bar_top_dy=-1.0` and
  `fig16_tuning.bar_bottom_dy=1.0`, passed same-run build, save/reopen,
  object readback, canvas, demo, Speed Mode, and visual gates with
  `MAE=0.07438`, `SSIM=0.69798`, `layout=0.99039`, `edge=0.60254`,
  `color=0.86634`, and `demo_cyan_ratio=0`. This improves MAE, SSIM, and edge
  over Run046 while slightly lowering color score. The packaged Fig16 builder's
  no-parameter default must use this Run048 bar-height tuning; explicit candidate
  parameters may still override it for A/B tests. Future promotion must beat
  Run048 overall or explicitly justify any color tradeoff.
- Run050 verifies the no-parameter Fig16 default in a live authorized Origin
  session: the candidate input omits `fig16_tuning`, but manifest/readback record
  `effective_builder_route.fig16_tuning.bar_top_dy=-1.0` and
  `bar_bottom_dy=1.0`, with the same Run048 metrics, `speed_mode_state.all_off=true`,
  `demo_cyan_ratio=0`, and `pass_eligible=true`.
- Run051 promotes the Fig16 source-sampled fill colors to the default:
  `WH=#ff9830`, `DRV=#00ff98`, and `DRX=#d098ff`. The live same-run color
  candidate passed build/save/reopen/readback/canvas/demo/Speed Mode gates and
  improved over Run050 with `MAE=0.06592`, `SSIM=0.69907`, and `color=0.95742`;
  `layout=0.99039` was unchanged and `edge=0.59898` was a small accepted tradeoff
  because the color and MAE gains are substantial and no new visual artifact was
  observed. Future Fig16 color experiments must beat Run051 or stay diagnostic.
- Run053/Run054 verify the Fig16 candidate-only text-size route. The builder may
  accept `fig16_text_size_offsets` or absolute `fig16_text_sizes`, and the
  effective values must be recorded in `effective_builder_route.fig16_text_sizes`.
  Run053 (`header=9.5`, `legend=9.25`, `stage=8.75`, `relation=9.5`) was
  pass-eligible and slightly improved SSIM/color but worsened MAE and edge:
  `MAE=0.06615`, `SSIM=0.70042`, `edge=0.59247`, `color=0.95760`. Run054
  (`header=9.75`, `relation=9.75`) matched Run052 metrics exactly. Therefore
  Fig16 defaults remain the Run052/Run051 color route; text-size experiments must
  beat Run052 across the accepted visual tradeoff before promotion.
- Fig12 native contour matrices require a horizontal matrix-order compensation
  before import because the Origin 2022 route used by this builder renders the
  numpy column order opposite to the source x direction. The accepted route
  returns `np.fliplr(np.clip(...))`; removing this compensation reintroduces
  the Run023/early-p10 left-right color-field error.
- Fig12 must run `layer.rescale()` before the final axis range, log-y,
  z-level, colorbar, and palette commands. A final rescale after palette
  assignment can reset the contour/colorbar state and revive default continuous
  palette behavior.
- AA2195 Fig12/Fig15/Fig16 production builders must disable Origin Speed Mode
  on the graph page and every formal layer before save/reopen/export. The
  post-reopen readback `speed_mode_state.all_off` must be true for pass-eligible
  evidence; a source-like export with `page.speedMode=1` remains a runtime
  defect even when no visible overlay is present.
- Run040 is the current p10 Fig12 comparator: it passed same-run build,
  save/reopen, object readback, canvas, demo, and visual gates with
  `MAE=0.05963`, `SSIM=0.76229`, `layout=0.90057`, `color=0.89830`, and
  `demo_cyan_ratio=0`, improving over Run033 and Run023.
- Run032's attempted reconstructed-field retuning was visually and metrically
  worse than Run031/Run033 (`MAE=0.07314`, `color=0.81624`) and must remain a
  rejected experiment unless a future same-run candidate beats Run040.
- Run041 and Run042's attempted overlay axis-title replacements were structurally
  valid but visually worse than Run040. Run041's large overlay titles degraded
  `MAE`, `SSIM`, and `layout`; Run042's smaller rotated y titles still degraded
  layout because Origin 2022 exported the rotated text with poor spacing. Do not
  promote rotated overlay axis-title routes unless a future same-run candidate
  beats Run040.
- Run055/Run057 promote the Fig12 PSC colorbar horizontal placement to the
  default. Run055 moved only the PSC colorbar from `(365,82,399,188)` to
  `(333,82,367,188)` through candidate `fig12_colorbar_offsets.PSC.dx=-32`,
  passed build/save/reopen/readback/canvas/demo/Speed Mode/visual gates, and
  improved over Run044 with `MAE=0.05661`, `SSIM=0.76304`, and `color=0.89846`
  while keeping `layout=0.90057`; `edge=0.73226` is a small accepted tradeoff.
  Run057 verifies that the no-parameter Fig12 default now emits the same PSC
  colorbar bbox and the same metrics with `fig12_colorbar_offsets` all zero.
  Future Fig12 colorbar experiments must beat Run057 or remain diagnostic.
- Run058/Run059 verify the Fig12 candidate-only label-size route. The builder
  may accept `fig12_label_size_offsets` or absolute `fig12_label_sizes`, and the
  effective values must be recorded in `effective_builder_route.fig12_label_sizes`.
  Run058 increased contour, mechanism, and colorbar label sizes and slightly
  improved layout/color, but worsened MAE, SSIM, and edge versus Run057. Run059
  increased only mechanism labels and also failed to beat Run057. Therefore
  Fig12 defaults remain the Run057 route; label-size experiments must beat
  Run057 before promotion.
- Run060/Run061/Run062 verify the Fig12 candidate-only matrix-bias route. The
  builder may accept per-panel `fig12_matrix_biases`, and the effective values
  must be recorded in `effective_builder_route.fig12_matrix_biases` and each
  panel inventory item. Run060's PSC `+2.0` bias worsened color and introduced a
  non-source-like blue band, so it is rejected. Run061's PSC `-1.5` bias improved
  MAE and color versus Run057 (`MAE=0.05628`, `color=0.90451`) with unchanged
  layout, nearly unchanged edge, and a small accepted SSIM tradeoff. Run062
  verifies that the no-parameter Fig12 default now emits PSC matrix bias `-1.5`
  and the same metrics. Future Fig12 field-tuning experiments must beat Run062.
- When a scalar bias cannot align both boundaries of a three-region contour,
  use bounded per-panel `fig12_matrix_contrasts` around the two central contour
  levels. Requested and effective contrasts must be recorded in normalization,
  panel inventory, builder route, and render fingerprint. This remains a native
  Worksheet XYZ transformation and must never be replaced by a raster overlay.

## v5.8.9-p11 Origin 2022 Deep Plot Readback

- Live post-reopen inspection activates each graph layer and uses Origin 2022 LabTalk `layer.plotn.pid`, `layer.plotn.show`, and `layer.plotn.name$` as the authoritative plot-type, visibility, and Y-dataset route. The Python wrapper's `Plot.lt_range()` is retained separately as `graph_plot_range`; it identifies the graph plot and must not be reported as source worksheet binding.
- Resolve the X dataset with the Origin 2022-compatible string-register form `%A=xof(Ydataset)`. Save and restore the string register in `finally`, so inspection cannot leave user LabTalk state changed. Parse internal dataset names such as `Book2_B` and `Book2_B@2` into workbook, worksheet index/name, and columns; record explicit semantic-readback errors instead of inventing unverified bindings.
- This patch preserves all p10 exact layer-count, editable reopen/save, Speed Mode, GraphObject geometry/name, cyan-watermark, and visual comparator gates. It changes readback evidence only; it does not retune the frozen Fig15 route or the current Fig12/Fig16 defaults.

## v5.8.9-p12 Portable Release and Live Evidence Closure

- Regression tests resolve their default `SKILL_ROOT` from `Path(__file__).resolve().parents[1]`; `ORIGINPLOT_SKILL_ROOT` remains an explicit override only. A release candidate must copy to a random temporary directory, run `scripts/run_all_tests.py` there with the override unset, execute at least 101 tests, and report zero errors and zero skips.
- Run `scripts/validate_release_candidate.py` as the authoritative release gate. It executes compileall, the complete test suite, random-directory portability, shareable-package validation, absolute-path scanning, cache/temp scanning, version consistency, three benchmark-evidence validations, and live readback validation. Any failed gate yields only `not_release_ready`.
- Windows absolute-path detection requires `^[A-Za-z]:[\\/]`. Semantic labels such as `H: Hardening level` and `S: Softening level` are not paths. Formal manifests, readbacks, reports, and packaged JSON use package-relative POSIX paths and contain no machine-local user-profile paths.
- Every formal figure run materializes exactly the standard p12 live evidence set: `result.opju`, `source_crop.png`, `pre_save.png`, `post_reopen.png`, `inspection.json`, `qa_report.json`, `benchmark_actual.json`, `semantic_benchmark_report.json`, `deviation_ledger.json`, `comparison_board.png`, `figurespec.json`, `compiled_ir.json`, `operation_plan.json`, `run_artifacts.json`, and `run_manifest.json`. Every JSON file carries the same nonempty `run_id`, `figure_id`, and `skill_version=5.8.9-p12`.
- The Fig15 p12 canary reuses the frozen Run047 candidate parameters without visual retuning. After authorized build/save/detach and editable reopen/export/detach, all 10 plots must have non-null `plot_type_code`, a known `plot_family`, visibility, X/Y datasets, workbook, worksheet and worksheet index, X/Y columns, and `graph_plot_range`. `Plot.lt_range()` is graph identity evidence only and never worksheet binding.
- Keep Fig15 Run047 frozen and Fig16 Run052 provisionally frozen. Keep Fig12 Run062 as the old reference baseline until the p12 release and evidence gates pass. Do not run matrix-bias candidates before creating a clean canonical source crop and recalculating `Run062_clean_reference_baseline`.
- After release closure, optimize Fig12 in this order: global vertical/layout calibration; colorbar and label geometry; label font sizes; contour/matrix topology; then PSC/UC/TR local field parameters. Candidate promotion still requires a clean same-run Origin rebuild and measurable improvement.
- The only release-ready state is `release_ready_for_fig12_targeted_optimization`. Do not claim all figures complete or portable unless all three standard evidence directories and the Fig15 live-readback gate pass.

## v5.8.9-p13 Acceptance Hardening and Fig12 Targeted Optimization

- Open-source/shareable packages resolve relative `source_crop` paths from the
  candidate JSON directory before consulting the current working directory.
  Runtime-only resolved paths must not replace the portable path recorded in
  public candidate parameters. Release archives exclude generated `outputs/`,
  OPJU, images, caches, local interpreters, and proprietary template downloads.

- Formal evidence separates `runtime_release_ready`, `structure_pass`, and `visual_baseline_promoted`. `overall_release_pass` and deprecated `pass_eligible` are derived from all three; runtime or structure success alone cannot promote a visual baseline.
- Visual gates are target-specific and include MAE, SSIM, layout, edge, color, registration shift, content bbox, and non-white occupancy. Fig15 requires its frozen render identity; Fig16 remains provisional and is never treated as final visual completion in p13.
- Frozen identity uses `originplot.render_identity.v1`, a SHA256 fingerprint of normalized effective rendering parameters, effective builder route, data/geometry version, source-crop SHA256, Origin version, export profile, template IDs, font profile, and visual feature flags. Candidate IDs, run IDs, timestamps, requested values, output paths, and host metadata are excluded.
- Fig12 formal candidates use strict parameter validation. Out-of-range values fail before Origin build. Diagnostic mode may clamp only with explicit requested/effective records and is not promotion-eligible. Run095 replay uses effective scale `8.0`, not requested scale `10.0`.
- `effective_builder_route` records Fig12 matrix resolution, smoothing, mode, Y minor ticks, panel layout offsets, matrix biases, and contour/mechanism label offsets.
- `scripts/validate_release_bundle.py` validates the final outer directory or ZIP for cache artifacts, machine absolute paths, and broken bundle references. Runtime release readiness depends on this final bundle gate.
- Fig12 ROI evidence uses `originplot.fig12_roi_definition.v1` and `originplot.fig12_roi_metrics.v1` for PSC/UC/TR plot and colorbar regions plus axis-title, mechanism-label, and contour-label regions. Overlay output is debug-only and is never a formal comparison input.
- Fig15 and Fig16 default visual parameters are frozen during p13. After acceptance closure, Fig12 layout candidates vary only one `fig12_panel_layout_offsets` dimension per clean same-run rebuild before colorbar or field tuning.
- Every final Origin reproduction must include at least one visible WorksheetBook that contains the editable source or semantic object data used by the figure. Each builder declares `required_worksheet_books` and `worksheet_binding_inventory`; after save/reopen, every declared worksheet must be found and every worksheet must have a declared association mode, otherwise the structure gate fails. Direct plots must use `direct_worksheet_plot_binding`; matrix contours must retain a worksheet copy of the exact matrix source with a recorded worksheet-to-matrix contour association and data digest; drawing-object schematics must provide a row-keyed geometry/semantic worksheet mapped to named Origin objects. A MatrixBook or GraphObject inventory alone never satisfies the worksheet requirement.

## Installation Target

The active install is the `originplot-skill` directory under the current Codex skills root (`$CODEX_HOME/skills` when configured, otherwise the current user's `.codex/skills` directory). When updating `originplot`, synchronize the latest validated version there, not to an ad hoc output directory. Staged packages may still be produced for review or sharing, but the callable Codex skill must be updated when the user asks to update the local OriginPlot skill.

Never overwrite this install path with an older staged package. Before synchronizing, compare the staged `SKILL.md` and scripts against the installed copy; if the installed copy contains newer validated rules or hotfixes, preserve them and only merge the intended update.

## V4 Runtime Engine Gate

The legacy v4 runtime remains supported for migration and dry-run diagnostics. It uses `originplot.figurespec.v4`, `originplot.compiled_ir.v4`, `originplot.operation_plan.v4`, and `originplot.run_manifest.v4`. Capability checks are fail-closed: missing adapter operations return `E110_CAPABILITY_MISSING`, serialization drift returns `E410_SERIALIZATION_DRIFT`, and runtime patches must be an Executable Patch with `rollback_on_no_improvement`.

The v4 execution surface includes `MultiAdapterRouter`, `Build Worker`, `Inspect Worker`, pre-save export, post-reopen inspection, `scripts/originplot_runtime_v4.py`, and `scripts/validate_shareable_package_v4.py`. v4 is not the preferred current benchmark route, but these files must stay runnable so older packages can be audited and migrated.

## Local Origin Agent 503 Fallback Gate

When the external approval path reports approval_service_503, Do not treat approval 503 as Origin execution failure. Queue the job through the file-queue local agent at `scripts/originplot_local_agent.py`, and record `approval_status`, `fallback_status`, `agent_status`, and `approval_service_503` in the manifest/status JSON. The file-queue local agent may use read-only examples from the installed skill `examples/` directory for dry-run input, while all writable outputs remain inside the job workspace.

## Origin COM Repair Execution Gate

If Origin COM initialization reports `origin_com_server_initialization_blocked`, same elevation mismatch, repeated `Origin64.exe -Embedding` leftovers, or an `OriginExt.ApplicationSI()` constructor hang, mark `origin_com_repair_required=true` and do not generate OPJUs. Repair must be done through a project-local repair wrapper that runs one narrow `regserver` or equivalent Origin registration command under explicit user authorization. If elevated setup cannot be created, record `elevated_task_creation_failed` and stop fail-closed.

## Explicit User Reauthorization Retry Gate

After explicit user administrator reauthorization, allow at most one bounded retry of the same narrow command. If the approval channel still returns `approval_service_503_after_reauthorization`, do not repeat equivalent escalated commands and do not use scheduled tasks, helper launchers, or indirect wrappers to bypass the failed approval channel.

## Default Architecture

```text
source figure/data
-> official OriginLab reference search
-> FigureSpec v5
-> recipe contract + semantic object inventory
-> operation maturity matrix + capability profile + doctor
-> compiled IR v5
-> operation plan v5
-> originplot_orchestrator.py
-> Origin build worker in its own Python process
-> pre-save export
-> OPJU save
-> Origin session release
-> clean-session reopen / inspect worker in a new Python process
-> post-reopen export
-> inspection v2/v5 deep object readback
-> benchmark_materializer.py creates read-only benchmark_actual.json
-> visual_evidence_engine.py creates aspect-preserved page + ROI evidence
-> semantic_figure_benchmark.py creates six-layer scores and deviation_ledger.json
-> validate_benchmark_evidence_package.py
-> run manifest v5
```

## Required Artifacts

Each completed p12 figure needs a self-contained evidence folder or ZIP with package-relative paths only:

- `result.opju`
- `source_crop.png`
- `pre_save.png`
- `post_reopen.png`
- `inspection.json`
- `qa_report.json`
- `benchmark_actual.json`
- `semantic_benchmark_report.json`
- `deviation_ledger.json`
- `comparison_board.png`
- `figurespec.json`
- `compiled_ir.json`
- `operation_plan.json`
- `run_artifacts.json`
- `run_manifest.json`

Evidence packages must not reference a machine-local user-profile path, another run directory, an external PDF, or an external workspace path.

## Tool Routing

- Use `scripts/origin_doctor.py` before build; offline mode only validates package shape, not Origin availability.
- Use `scripts/operation_maturity.py` before compiling complex operations. Registry presence alone is not capability. An operation is verified only when registry, adapter implementation, doctor probe, inspector readback, and integration test are all true.
- Use `scripts/originplot_compile_v5.py` to compile FigureSpec v5 into compiled IR v5 and operation plan v5.
- Use `scripts/originplot_orchestrator.py` for live execution. Build, inspect, and QA must run in separate Python worker processes.
- Use `runtime/artifact_manifest.py` and `run_artifacts.json` for all cross-process handoff.
- Use `scripts/benchmark_materializer.py` before semantic benchmarking. Production runs must not provide handwritten `actual`.
- Use `scripts/visual_evidence_engine.py` as the active visual engine. It must preserve aspect ratio, compare page and ROI regions, use tolerance-aware Edge F1, foreground-weighted SSIM, and apply recipe `visual_thresholds`.
- Use `scripts/semantic_figure_benchmark.py` for evidence-linked benchmark closure. It must reject seed/cross-run artifacts as pass-eligible evidence.
- Use `scripts/validate_benchmark_evidence_package.py` for benchmark evidence ZIPs or folders.
- Use `scripts/build_combined_review_package.py` for review packages that bundle skill ZIPs and comparison images; all ZIP entries must use POSIX paths.
- Use `scripts/build_shareable_package.py` and `scripts/validate_shareable_package_v5.py` for core skill ZIPs.
- Use `scripts/run_all_tests.py` as the release validation entrypoint. It must discover both `tests/**/*.py` and `scripts/tests/**/*.py`, run at least the configured minimum number of tests, and finish with zero failures and zero critical skips.

## Runtime Closure

The runtime is fail-closed:

- Administrator Codex/Python is mandatory for every Origin attach/export automation path. Before `originpro.attach()`, PowerShell COM, `OriginExt.ApplicationSI()`, `OriginExt.Application`, `OriginExt.ApplicationCOMSI`, or a live Origin build/export worker is attempted, the worker must verify `ctypes.windll.shell32.IsUserAnAdmin()` is true on Windows.
- If the current Codex/Python process is not elevated, return `E120_ENVIRONMENT_MISMATCH`, set `origin_attach_not_attempted=true`, `opju_generation_allowed=false`, and do not import or instantiate `originpro`, `OriginExt`, or PowerShell COM. Do not let this degrade into `E300_ORIGIN_ATTACH_FAILED`.
- In administrator attach-existing mode, if no Origin process is running and the configured Origin executable exists, start that visible Origin GUI with a bounded wait before calling `originpro.attach()`. Record `origin_auto_start` / `authorized_attach_origin_auto_start_used`. If the configured GUI cannot start, return `authorized_attach_origin_auto_start_failed` fail-closed; do not use seed/surrogate OPJUs.
- If the visible Origin instance is elevated and the current Python process is not elevated, treat this as a same-elevation failure. The recovery route is to run Codex/Python or the narrow project runner from an administrator terminal, not to retry COM constructors.
- If the external approval service returns `503` while requesting administrator execution, record `E503_APPROVAL_SERVICE_UNAVAILABLE` and stop fail-closed. Seed OPJU, copied OPJU, source-image pages, or COM surrogate projects must not be used to claim success.
- Dry-run can prove protocol only; it must never produce final `overall_status=pass`.
- `overall_status=pass` requires preflight, build, round-trip, structure, serialization, semantic, visual, and evidence-package gates all passing.
- Seed OPJU fallback may create files only for artifact continuity. It must set `provenance=inherited_diagnostic`, `eligible_for_pass=false`, `origin_export_pass=false`, and `overall_status` no higher than `incomplete`.
- `live_same_run` requires same run IDs and matching SHA256 records for OPJU, pre-save export, post-reopen export, inspection, QA, actual, semantic report, ledger, and manifest.
- Patch loops must run `validate -> apply -> rebuild -> evaluate -> commit_or_rollback`; a patch without rollback guard is rejected.
- Live runtime scripts must expose bounded timeout controls, including `--phase-timeout-seconds`, worker/runtime timeout knobs, child-process isolation, and delayed cleanup for stuck `Origin64.exe -Embedding` processes.
- Formal multi-figure runs must prefer per-figure bounded workers. A timeout or attach failure in one figure must produce that figure's manifest/error record and must not erase successful evidence from other figures.
- `OriginExt.ApplicationSI()`, attach-existing, and COM bridge probes are allowed only inside bounded workers or bounded smoke tests. A hanging SWIG constructor is a failed route, not a reason to block the whole reproduction.

## Official Reference Gate

For paper-like figure reproduction, search official OriginLab Graph Gallery first. A gallery entry is a complete project reference only after its downloaded project/archive has been extracted, opened in a compatible Origin version, and inspected for workbook data, graph pages, layers, plots, legends, annotations, and analysis outputs. A screenshot, `.otp`, or `.otpu` alone is support material, not the baseline.

When the workspace contains `OriginLab官方相似模板_下载器与匹配清单`, treat it as the authoritative local official-template catalog. Use its downloader links, manifest, and match notes before older ad hoc template choices.

For the Fig. 12/15/16 benchmark used by this workspace, the required official template set is:

- Fig12: `GID499` XYZ Contour as the primary contour donor, `GID459` categorical/discrete contour as fill supplement, and `GID27` panel graph as layout supplement.
- Fig15: `GID1609` Annotations on Graph as the primary curve/arrow/text donor and `GID27` as the two-panel layout supplement.
- Fig16: `GID399` Grouped Stack Column Graph as the primary stacked bar donor and `GID1652` Faceted Grouped Column Chart as the PSC/CP/TR layout supplement.

Older `GID1663`/`GID1664` references are legacy diagnostics for this benchmark and must not be used as the primary route when the official downloader catalog is available.

The official downloader catalog is an execution input, not merely a citation. A final OPJU route must record which official project supplied the editable mechanism family, then instantiate target-specific editable Origin objects from that family: contour/matrix or filled-region contour for Fig12, worksheet-backed annotation/arrow/curve/text routes for Fig15, and grouped/stacked column or faceted column routes for Fig16. If an Origin GraphObject primitive exports with distorted coordinates in Origin 2022, the route must switch to a verified editable alternative such as Origin native matrix contour, worksheet-backed plot paths, grouped/stacked column, or faceted-column layouts; distorted rectangle exports are not pass-eligible.

For the current benchmark, the required default primary routes are:

- Fig12: one OPJU graph page named as a native three-panel matrix-contour reconstruction route, with three Origin contour/matrix layers derived from the GID499/GID459/GID27 reference family. Three separate contour pages and primitive contour schematics are diagnostic only.
- Fig15: a GID1609/GID27 reference-family annotation route with two Origin graph layers, worksheet-backed panel-local editable paths, and Origin text/annotation objects. Primitive pixel-canvas schematics are diagnostic only.
- Fig16: a `semantic_schematic` route informed by GID399/GID1652. Use one source-sized, axisless Origin graph layer with editable Origin rectangle drawing objects for WH/DRV/DRX bars, group boxes, separators, legend labels, relation labels, and stage labels. This route is not pixel trace. Worksheet-backed polygon/path overlays are allowed only when the drawing-object family is disabled or explicitly diagnostic; do not draw both families for the same group boxes/separators. A native `StackColumn`/GID1652 route may replace it only after donor object readback and same-run export evidence prove it is closer.

For Fig12, the migration contract must show GID499/GID459/GID27 donors and an implemented Origin matrix sheet + `xymap` + native contour layer route. Colorbar labels and GF/GR/GF+GR text labels remain blocking gaps until verified in Origin 2022 exports, but they must not be replaced by pixel canvases.

For Fig16, the migration contract must show GID399/GID1652 donors and an implemented worksheet-backed semantic route or a donor-readback-verified native `StackColumn`/faceted-column route. The semantic route must use a single coordinate system; do not mix StackColumn category coordinates with pixel overlay paths. Relation labels, legend labels, group boxes, and stage markers are required Origin objects. Route changes are evidence-gated: if a route is visually worse than Run94 or the current best same-run export, restore the better route and record the worse one as not pass-eligible.

For this benchmark, line-band fills, default text primitives on the pixel canvas, and rectangle-coordinate variants may be tried only as explicitly logged experiments. If a route is worse than the best same-run/baseline evidence, restore the better route and record the worse route as not pass-eligible; do not keep it as the default merely because it is more editable.

## v5.5 Recipe Gates

Each FigureSpec must declare `figure_class`:

- `native_chart`: contour, matrix, scatter, line, and true chart figures. Use official/native Origin plot families first.
- `semantic_schematic`: mechanism diagrams, conceptual curves, and schematic bar figures. Use worksheet-backed line/polygon/path data plus Origin text objects as the formal editable route; this is allowed when objects are semantic and source-image/pixel-trace routes are absent.

Fig15-like dual-panel curve schematics are the first live closure priority. A pass requires:

- no seed fallback;
- one graph page;
- two layers;
- two curve plots;
- all key objects created as real Origin objects;
- 100% critical semantic coverage;
- 100% key object name/readback coverage;
- panel A/B and caption ROI visual comparison;
- self-contained evidence package validation.

Fig16-like grouped stacked bar schematics must use the `semantic_schematic` single-canvas worksheet-backed route or a donor-readback-verified native grouped/stacked column route. The default route is WH/DRV/DRX editable rectangle drawing objects plus editable group boxes; worksheet-backed polygon segments are fallback only after same-run export evidence beats the drawing-object route. Pixel trace, raster background routes, and GraphObject/pixel-canvas primitives are forbidden as final editable base graphs.

Fig12-like contour figures must first pass the structure gate: one graph page, three panels/layers, source-derived or matrix-backed contour/region objects, log Y axes, contour lines/labels, discrete colorbars, and GF/GR/GF+GR region labels. If data are digitized or reconstructed, set `reproduction_mode=digitized_approximate`; do not claim `source_exact`.

For the current Fig. 12/15/16 benchmark:

- Fig12: build one three-panel OPJU graph. Separate contour pages are diagnostic only.
- Fig15: rebuild as an object-level schematic; arrows, curves, dashed guides, stage markers, panel labels, and text must be Origin editable objects or worksheet-backed editable paths.
- Fig16: rebuild as grouped/stacked bars or worksheet-backed editable rectangles; legends, relation labels, group boxes, and stage markers must be editable objects.
- Every final run must emit source/export comparison boards and a distance report with OPJU open status, export status, MAE/RMSE/nonwhite delta, Run94 improvement status, and blocking deviations.

Every final run must emit `origin_object_readback` for primary graph pages. Donor template claims must emit `official_template_reuse_truth`; when donor truth remains reference-only, the result may still be a valid semantic or native reconstruction, but it must not be described as donor object transplantation.

## Error Codes

Use stable machine-readable codes:

- `E100_SCHEMA_INVALID`
- `E110_CAPABILITY_MISSING`
- `E120_ENVIRONMENT_MISMATCH`
- `E121_ATTACH_POLICY_VIOLATION`
- `E122_ORIGIN_DEMO_EXPORT_BLOCKED`
- `E130_DOCTOR_FAILED`
- `E210_OPERATION_UNSUPPORTED`
- `E220_BUILD_FAILED`
- `E300_ORIGIN_ATTACH_FAILED`
- `E310_ORIGIN_MODAL_BLOCKED`
- `E330_SEED_OPJU_FALLBACK_USED`
- `E430_SEMANTIC_BENCHMARK_FAILED`
- `E440_PLOT_FAMILY_NOT_IMPLEMENTED`
- `E450_SEMANTIC_OBJECT_COVERAGE_FAILED`
- `E460_PANEL_STRUCTURE_MISMATCH`
- `E470_LIVE_SAME_RUN_REQUIRED`
- `E480_EVIDENCE_PACKAGE_INCOMPLETE`
- `E490_OPERATION_MATURITY_UNVERIFIED`
- `E400_STRUCTURE_MISMATCH`
- `E401_GRAPHOBJECT_READBACK_UNVERIFIED`
- `E410_SERIALIZATION_DRIFT`
- `E420_VISUAL_MISMATCH`
- `E500_PATCH_REJECTED`
- `E510_NO_IMPROVEMENT`
- `E503_APPROVAL_SERVICE_UNAVAILABLE`
- `E540_PAGE_UNIT_SCALE_MISMATCH`
- `E541_LAYER_UNIT_SCALE_MISMATCH`

## Completion Rules

### Worksheet-to-Plot direct-binding correction (supersedes all earlier benchmark route clauses)

Every final Origin reproduction, including semantic schematics, must use Origin-native
`Worksheet -> Plot` direct bindings for every data-bearing or geometry-bearing plot.
Merely adding a WorksheetBook is insufficient. Worksheet-to-Matrix association,
Worksheet-to-GraphObject lookup tables, named-object inventories, hashes, and declared
association modes do not satisfy this rule and are diagnostic-only.

After saving and reopening the OPJU, the hard gate must enumerate every plot in every
declared primary graph layer and resolve nonempty `data_workbook`, `data_worksheet`,
`x_column`, and `y_column` values from Origin's live `layer.plotN.name$` / `xof()` chain.
XYZ plots must additionally resolve `z_column`. A figure with zero plots, a Matrix-only
plot, or any unbound plot fails even if its GraphObjects and visible export are correct.

For the Fig12/15/16 benchmark, the required routes are:

- Fig12: three native XYZ-range Worksheet contour plots (Origin plot type 243), one per
  panel, each bound directly to X/Y/Z columns. MatrixBook contour type 226 is forbidden
  as the final route.
- Fig15: all curve, guide, arrow, and circle paths remain direct Worksheet XY line plots
  (Origin plot type 200). Text may remain editable Origin labels.
- Fig16: review the available official and local templates before construction. The
  verified default is official GID399 Grouped Stack Column (project SHA256
  `a4b3ba55ebe2d195e6ca4b15afb1745619ea23469bedbb60490b976aa9f097b6`) instantiated
  with the Origin 2022 local `STACKCOLUMN.otp`; GID1652 is the PSC/CP/TR faceted-layout
  reference. Bars use native Worksheet stacked-column plots (Origin plot type 213),
  with one H slot containing WH and one S slot containing stacked DRV+DRX per stage.
  Group frames and stage circles use direct Worksheet XY paths (type 200). Do not
  add a separate group baseline when the native column bottom borders already supply
  the visible bottom edge; duplicate baselines are a blocking visual defect.
  FLOATCOL type 203 is diagnostic-only for this figure and must not be the final bar
  mechanism. GraphObjects may be used for text only.

For Fig16 legends, every swatch must use a true Origin area/bar/column fill property with
Worksheet-to-Plot direct binding, square corners, and a separate Worksheet-bound XY
outline. Thick single-line swatches, dense or overlapping scanlines, hatches that merely
look solid at normal scale, and any other line-coverage simulation are forbidden as the
final route. The native fill must reach the inner edge of all four outline sides without
a white inset, and the top swatch outline must remain fully inside the exported canvas.
`Fill Area to Next Data Plot` is forbidden for isolated legend swatches: Origin 2022 may
reassociate the next plot during reopen or interactive refresh and fill across the main
figure. Use an isolated native bar/column plot (or another self-contained native filled
plot family) whose fill extent cannot depend on plot adjacency, and verify both the
post-reopen export and the interactively reopened editable graph show zero spill outside
the swatch bounding box. Do not rely on the native column's clipped top or bottom edge
as the only visible frame: draw a closed, slightly inset Worksheet-bound XY outline in
the same isolated micro-layer and require all four black sides, including the green
swatch top edge, to survive save, reopen, export, and interactive zoom.
Stage numerals must be calibrated from their exported glyph bounding boxes and centered
horizontally and vertically inside each reopened circle; a shared unmeasured offset does
not satisfy this rule.

For adjacent H/S columns in Fig16, inspect every stage at enlarged scale after editable
reopen. The S stack must not overlap or visually cover the WH right border. Apply
stage-local x calibration when only selected stages drift; different stages may require
opposite correction directions, so a global shift that disturbs already aligned stages
is forbidden. Record the effective per-stage S-slot offsets in the builder result and
verify them against the reopened export.

For Fig16 blue dashed group frames, compare the reopened frame-pixel count and apparent
stroke thickness against the source before changing any WH/DRV/DRX fill color. Excess
dark-blue pixels are a frame-width defect, not a palette defect. The verified native
Worksheet XY path default is `0.5 pt`; any future width change must be recorded in
`effective_builder_route` and the render fingerprint, then beat the current same-run
visual metrics without weakening the frame-presence gate.

Fig16 template selection must be evidence-backed rather than name-based: record every
candidate inspected, its project/template hash, reopen result, worksheet row count,
plot types, direct bindings, and selection reason. Reject a template that cannot retain
native stack semantics, direct Worksheet bindings, editable target layout, clean reopen,
or competitive same-run visual fidelity. Current verified evidence is GID399 with 32
reopened Worksheet rows and six type-213 plots, plus GID1652 with 110 rows as a layout
supplement. The final target project remains subject to the global 5,000-row hard gate.

This correction supersedes earlier statements that selected the Fig12 Matrix route,
the Fig16 GraphObject-only route, `expected_plot_count=0`, or a row-keyed geometry
Worksheet mapped to named objects. Tests and manifests must assert the reopened direct
binding contracts, not builder-declared associations.

### Direct-plot Worksheet row budget

Every final reproduced figure has a global hard limit of 5,000 Worksheet rows across
all WorksheetBooks declared as direct plot sources. The limit is per figure, not per
sheet or per plot. After OPJU reopen, the runtime must read each required Worksheet's
actual shape, sum its row count, and fail the structure gate when the total exceeds
5,000 or when any row count cannot be read. Builder-declared counts alone are not
evidence.

Preserve accuracy within this budget through structured sampling: retain extrema,
region boundaries, curve turning points, discontinuities, annotation anchors, and
category endpoints; use adaptive or stratified sampling where appropriate; then prove
accuracy with same-run Origin export and visual/ROI regression. Uniform oversampling,
duplicated points, and carrying legacy Matrix resolution into XYZ long-form Worksheets
are forbidden. Use the smallest row count that meets the visual and semantic gates.

For logarithmic XYZ contours, the matrix sampling rows and the Worksheet Y coordinates
must use the identical geometric grid. Classify and smooth source-derived regions at
source-crop resolution before reducing to the bounded Worksheet grid; never classify
only the final sparse grid. Fig12 uses at most 46 x 36 rows per panel, or 4,968 rows
across its three direct-bound Worksheet XYZ plots.

Origin cmap initialization may reset custom contour boundaries. Apply palette setup
first, then reapply each panel's explicit `plot.zlevels`. Because that final z-level
assignment can reset line properties again, reapply explicit `lineColorN`,
`lineWidthN`, and `showLines(1)` after the final z-level assignment and update the cmap
scale. Post-reopen inspection must record both ordering contracts. Equal-interval
fallback levels are not acceptable when the source publishes nonuniform boundaries.

Panel identifiers must be calibrated to their source position independently of the
contour data. For Fig12 they sit outside the upper-left plot frames; placing `(a)`,
`(b)`, or `(c)` inside the data rectangle is a layout and registration failure.

For Origin LabTalk cmap lines, `showLines(1)` shows major contour lines,
`showLines(2)` shows all lines, and `showLines(3)` hides all lines. Fig12 must use
major lines with explicit `lineColorN` and `lineWidthN` values; using method 3 is a
hard visual failure because it removes the source's region boundaries.

Fig12 plot-attached label sizes require a figure-specific Origin export calibration;
record the applied per-role scales in `effective_builder_route` and the render
fingerprint. Panel identifiers, contour values, and boxed mechanism labels must be
calibrated independently when their exported glyph and frame bounds differ.
Do not change the shared font helper to compensate, because that would silently resize
Fig15/Fig16 and colorbar/page labels. The verified Fig12 scales are panel `2.6`,
contour `2.6`, and mechanism `2.4`; mechanism labels use Origin rich-text bold.

Scientific axis units must use semantic glyphs and Origin-native rich text, not ASCII
spellings that merely approximate the source. For Fig12 the X title is
`Temperature/\u2103` (rendered as `Temperature/\u00b0C`) and the Y title uses Origin
rich text `Strain rate/s\\+(-1)` so the reopened export displays a true superscript
minus one. Literal `degC`, `s^-1`, separated degree/C glyphs, or baseline minus-one
text are blocking symbol-format defects. These title strings and font sizes must be
recorded in `effective_builder_route` and the render fingerprint.

Horizontal and vertical axis-title font sizes must be calibrated independently
when their reopened rendered extents differ. A single nominal Origin font size
is not a valid substitute for matching both title orientations; record both
effective sizes in the builder route and render fingerprint.

Do not call an OPJU reproduction complete unless Doctor/capability/maturity gates pass, all operations have verified routes, the OPJU is saved and reopened in a clean session, inspection confirms workbook/matrix/graph/layer/plot/object/data-binding contracts, post-reopen export is nonblank, visual QA passes, baseline-improvement gates pass, and the evidence package is self-contained.

Never paste the source image into Origin and call it an editable reproduction. Never use pixel trace as the final editable base graph. Never compare a current report against old-run exports without explicit inherited artifact records and `eligible_for_pass=false`. A copied seed OPJU is not a completed reproduction.



