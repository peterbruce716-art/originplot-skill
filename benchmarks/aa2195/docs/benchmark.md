# AA2195 Benchmark Contract

The packaged AA2195 builders are specialized implementations, not proof that arbitrary source images can be converted automatically. Existing successful local reproductions may be reused for layout, typography, Origin object structure, plot types, calibration, curves, markers, error bars, fields, and bar segments when their prior live batch passed all structure, visual, provenance, and release gates and their hashes still match. Only missing, unvalidated, drifted, or visually inadequate parts require new extraction or reconstruction.

The p18 Fig14 fresh-source route clusters colored marker rows before selecting the data point, preventing the 250 degrees C markers from being averaged with the legend. Black error-bar pixels are selected by marker-local connected components at each shared x coordinate, and one-sided marker occlusion uses the maximum center-to-endpoint extent. Marker overlays use Origin's native scatter plot so a zero-width hairline cannot cover the dashed series. The route identity is `aa2195_fig14_component_errorbars_native_scatter_dash_v4`; it requires a new same-run Origin save/reopen validation before promotion.

The final p18 administrator-Origin 2022 batch completed all five figures against one visible Origin process with no audit findings. Every worker exited zero and passed live-Origin, save/reopen structure, source-data, visual, and release gates in the retained reference environment. The sanitized run hashes and scalar metrics are recorded in `aa2195-release-evidence.json`; local rasters and Origin projects remain outside the shareable package. The public file is a maintainer-attested index, so third parties can validate its schema and recorded values but cannot independently reproduce its pixels or infer live verification without the authorized complete evidence bundle.

## Fig3

- Four-layer source-calibrated stress-strain reconstruction with 44 direct Worksheet XY plots.
- PSC, UC, and TR retain one continuous editable X/Y source per curve. Their native Origin line styles are applied after plot insertion and must reopen as style codes 0 (solid), 2 (dotted), and 3 (dash-dot), respectively.
- The live gate retains strict MAE, layout, edge, color, and registration checks; the source-calibrated SSIM floor is 0.650.
- Every curve declares a canonical source group with `single_xy` continuity; line appearance is a plot property and does not fragment or duplicate the underlying data.
- Each of the four panels declares its own subplot-to-Worksheet contract and reopens against only that panel's curve Workbook. Its editable PSC/UC/TR legend rows use `\l(plot)` references to the actual colored curve plots, and every referenced plot must retain the row's native line style; no legend-only Workbook or Plot is permitted.

## Fig14

- One native XY page with nine direct Worksheet plots: three editable anchor line plots, three independent marker overlays, and three editable error paths.
- The line/marker split is deliberate: Origin 2022 can overwrite grouped line styles when line-symbol plots are inserted. Reopened readback must report type-200 line and error plots, type-201 native scatter marker overlays, nine direct Worksheet bindings, and native line-style code 1 for all three source-dashed series. A type-202 zero-width line-symbol overlay is forbidden because Origin may export its nominally zero-width connection as a hairline over the dashed series.
- PSC/UC/TR markers, source-calibrated values, error extents, axes, legend, and Times New Roman typography survive save/reopen readback.
- The current same-run Origin 2022 route passes structure and visual gates; it is an editable reconstruction of the published raster, not raw experimental data recovery.
- Each PSC/UC/TR family is one canonical source group. Its hash-verified anchor line, anchor-marker view, and error path are deterministic views in the same reopened Worksheet, whether freshly extracted or quality-validated for reuse.

## Template-first gate

Before any Fig3/Fig12/Fig14/Fig15/Fig16 build, use all four official research entrances: the Graph Gallery newest index, Chinese Origin documentation, official graphing videos, and Chinese graphing Quick Help. Then check the local `OriginLab官方相似模板_下载器与匹配清单` and installed templates. Inspect downloaded projects in administrator-run Origin, not only screenshots or template names. Record archive/project hashes, open/reopen status, workbook rows, plot families, direct bindings, and why each candidate was selected or rejected. Missing template-search evidence blocks construction and promotion.

Use `scripts/inspect_official_templates.py` for the compatible-open and object-structure record. Run it elevated against the same visible administrator Origin used for the build.

Sanitize the resulting metadata into `originplot.template_search_record.v1` and reference it from the candidate as `template_search_record`. Keep URLs, hashes, open results, rows, Plot types, binding counts, and selection reasons; remove local absolute paths and do not redistribute downloaded OriginLab projects. The candidate worker validates this record before dry-run planning or live construction.

Official entrances:

- `https://www.originlab.com/www/products/GraphGallery.aspx?s=0&sort=Newest`
- `https://docs.originlab.com/zh/`
- `https://www.originlab.com/videos/index.aspx?CID=11`
- `https://docs.originlab.com/quick-help/graphing/zh/`

## Fig12

- Current public state: the canonical editable route has administrator Origin 2022 structure, visual, and release-pass evidence in the recorded reference environment; this is not a cross-machine pixel-identity claim.
- One graph page with three native XYZ Worksheet contour plots, Origin type 243, each bound to X/Y/Z.
- The canonical grid is 46 by 36 per panel, 4,968 rows globally; the controlled limits are 32-46 X samples and 25-41 logarithmic Y samples. Reconstruction and Worksheet coordinates use identical geometric Y grids.
- Use the verified orange/green/blue categorical region plan with explicit nonuniform levels and major contour lines.
- The current Fig12 candidate uses a constrained region-anchor remap only for TR, `fig12_matrix_region_values={TR:[67.1,59.2,49.05]}`. It preserves the three native XYZ plots and 4,968 Worksheet rows while compensating the Origin 2022 interpolation that compressed the source TR orange region. Canonical v20 passes every declared visual gate after save/reopen.
- The optional `fig12_colorbar_offsets` parameter is retained for explicit per-panel geometry trials, but the default candidate leaves it unset because `dy=-5/-7` improved SSIM/edge while worsening MAE in same-run Origin 2022 A/B tests.
- `scripts/probe_graphobject_polygon.py` records the Origin 2022 path capability boundary: plain `draw -paths objName SVGPath` creates editable type-34 objects and persists across save/reopen; the tested `-s/-d` variants do not. `fig12_path_overlays=true` vectorizes the three palette regions and boundaries into filled Origin path objects while retaining the native XYZ Worksheets underneath. Every import uses a unique temporary directory that is removed after import, and save/reopen must verify object type 34 plus X/Y/DX/DY geometry. The canonical route uses `#708e57`, a 0.5 px boundary, page-coordinate Times New Roman axis titles, panel size 11, and mechanism size 10. Its post-reopen run passed all strict visual gates: MAE 0.035472, SSIM 0.801507, layout 0.992431, edge 0.745290, and color 0.977127. Edge is only 0.000290 above threshold and is therefore reported in `near_threshold_metrics`.
- Encode the three categorical regions with threshold-centered scalar values: the orange/green and green/blue interpolation midpoints must equal the two internal nonuniform contour levels. Simple interval midpoints shift boundaries when level spacing is unequal and are not the default route.
- Use `scripts/rank_fig12_matrix_candidates.py` to shortlist source-palette matrix parameters offline. The report retains exact boundary F1 and adds a pixel-tolerant boundary F1 for low-row grids. Offline ranking is diagnostic only and cannot promote defaults without a same-run administrator-Origin save, reopen, readback, and pre/post visual pass.
- Use `scripts/calibrate_fig12_origin_response.py` only to compare reconstructed matrices with historical Origin exports while diagnosing response differences. Its output is inherited diagnostic evidence, never promotion evidence.
- Apply palette and reapply `plot.zlevels`. The native-only fallback reapplies line color/width and `showLines(1)`; the canonical type-34 overlay route uses `showLines(0)` so the editable source-vectorized boundary is not doubled. `showLines(3)` is a hard failure.
- Each panel's XYZ contour and editable type-34 region fill/boundary share one classified-palette source group. The GraphObject view records its deterministic vectorization and retains the existing post-reopen type/geometry gate.
- PSC, UC, and TR each declare a subplot-to-Worksheet contract; panel-to-Workbook swaps fail even if the three XYZ plots and three Workbooks all exist globally.
- After save and reopen, read back every contour plot's `zlevels`: `minors` must be zero and the numeric levels must match that panel's declared nonuniform levels. Type 243 and XYZ bindings alone are insufficient. Historical runs that did not record `zlevels` cannot be retroactively treated as satisfying this gate.
- Panel IDs sit outside the upper-left frames. Panel, contour, and mechanism text scales are independently calibrated.
- Axis titles use semantic Origin text: `Temperature/\u2103` and `Strain rate/s\\+(-1)`.
- Official reference families: GID499, GID459, and GID27. A reference is not object transplantation unless donor truth is recorded.

## Fig15

- Current public state: frozen regression route retained; any new claim still requires same-run live evidence.
- One graph page, two calibrated layers, and ten direct Worksheet XY plots, five per layer.
- Curves, guides, worksheet arrowhead paths, and circles use plot type 200. Text remains editable Origin labels.
- Every continuous or NaN-separated path declares its canonical geometry source; multi-part paths remain one Worksheet X/Y pair with NaN separators.
- Both calibrated panels declare separate subplot-to-Worksheet contracts and must reopen with five editable Worksheet-bound plots each.
- Remove unexpected axes, titles, and legends; verify native axis state after reopen.
- Required object names and their persistence are checked after reopen. Origin demo watermarks fail with `E122_ORIGIN_DEMO_EXPORT_BLOCKED`.
- Official reference families: GID1609 and GID27.

## Fig16

- Current public state: the native structure route has a frozen regression identity; every pass still requires same-run live evidence.
- Use GID399 semantics through local `STACKCOLUMN.otp`, with GID1652 as layout reference.
- H/S row model: an H slot contains WH; the adjacent S slot stacks DRV and DRX. Native bar plots use type 213.
- Group frames and stage circles are direct Worksheet XY paths, type 200. Group-frame default is 0.5 pt.
- WH/DRV/DRX legend entries use editable `\l(plot)` references to the three real native stack-column plots. Legend-only micro-layers, swatch plots, and Worksheet columns are forbidden.
- Verify the post-reopen legend at exported pixels: the first black border is not clipped, WH and DRV share a 2 px border, and DRV and DRX are separated by exactly 3 white pixels at the 720 x 375 benchmark export.
- The native stack layer and geometry overlay declare subplot/layer-to-Worksheet contracts; all five data/geometry plots reopen against the declared stack-data Workbook.
- Do not duplicate the native column bottom edge with a second baseline.
- Use the source-derived S-slot centers directly; legacy stage-local left shifts are forbidden because they move individual DRV/DRX boundaries by up to 3 px. Keep numeral glyph centering calibrated from the reopened export.
- Detect all 21 WH/DRV/DRX colored segments after reopen and compare each left/top/right/bottom boundary with the source crop. Promotion requires no missing segment, maximum absolute boundary error at most 1 px, and mean absolute boundary error at most 0.5 px. The route identity is `aa2195_fig16_segment_boundary_calibrated_v7`.
- The final p18 live export detected all 21 source and 21 reconstructed segments with zero missing segments, 1 px maximum absolute boundary error, and 0.476190 px mean absolute boundary error. Its global visual metrics were MAE 0.045066, SSIM 0.792995, layout 0.987722, edge 0.676016, color 0.986775, foreground F1 0.987996, and edge F1 0.942612 at 720 x 375.
- Keep the 15% native column gap. Use the explicit Origin layer background `#fefefe` to match the current PDF raster's near-white antialiased mean without changing WH/DRV/DRX scientific colors or post-processing the PNG.
- Promotion requires all live visual gates plus a passing `source_data_gate`, source crop/data hashes, effective builder route, geometry version, Origin version, and export profile. A reused data bundle additionally requires a passing `originplot.aa2195_validated_data_reuse.v1` record. Metrics without that identity remain non-promoted.

## Cross-batch reproducibility

`render_identity.fingerprint` records the declared inputs (effective parameters, builder route, data digest, geometry version, source crop hash, Origin version, export profile, template ids, font profile, feature flags). It is **not** a hash of the export, so two runs can share a fingerprint and still produce different pixels. Do not read matching fingerprints as matching output.

A measured example on Origin 2022, same machine, same day, same `fresh_extract` source bundle and identical Fig12 fingerprint: a batch against a freshly launched Origin (`origin_launch_mode=batch_started`) and two batches against a reused warm Origin (`origin_launch_mode=preexisting_visible`) disagreed on Fig12 while Fig3/Fig14/Fig15/Fig16 stayed bit-identical.

| Fig12 metric | fresh Origin | reused Origin | delta | gate |
| --- | --- | --- | --- | --- |
| `edge_f1` | 0.821641555 | 0.811466457 | -0.010175097 | min 0.810 |
| `edge_score` | 0.746058099 | 0.750113543 | +0.004055444 | min 0.745 |
| `color_score` | 0.975087643 | 0.970851343 | -0.004236300 | min 0.920 |
| `ssim_score` | 0.801233053 | 0.803695619 | +0.002462566 | min 0.777 |

The two reused-Origin batches reproduced each other exactly, so the difference tracked Origin process state rather than run-to-run noise. The consequence was the part that mattered: Fig12 `edge_f1` fell to 0.0015 above its floor, 0.77% of the gate budget, purely from how Origin was started. That divergence is fixed below and `edge_f1` headroom is back to 6.13% in both launch modes, but the general lesson stands: a fingerprint match is not an output match, and a gate this tight can be flipped by an input nothing records.

Record `origin_launch_mode` with any Fig12 claim, and use `scripts/compare_five_figure_batches.py --baseline <root> --candidate <root>` to diff two batches. It reports per-metric drift, `pass_flip`, `near_threshold_regression`, and `identity_claims_equality_but_metrics_differ` for the case above. Comparing batches is not optional for a promotion claim: the per-run audit answers "did this pass?", not "is this the same figure as last time?".

The pixels that moved were three 1 px vertical black lines (x=489 y 54-268, x=285 y 323-541) present in some exports and absent in others. Nothing else differed: the readback recorded identical plot counts, types, bindings, graph objects and `zlevels` in both runs, so no structural gate can see this difference at all.

`layer.cmap.showLines` is never read back either, even though this document calls `showLines(3)` a hard failure and `showLines(0)` the canonical type-34 overlay state. `scripts/probe_fig12_contour_line_state.py` establishes why, by opening the two saved projects that differ only by those three lines and reading every candidate colormap property on each contour layer. On Origin 2022 `showLines`, `enableLines`, `lines`, `lineVisible`, `showLine`, `numLevels` and `showLabels` do not resolve at all, while `numColors`, `lineColor1`, `lineColor2`, `lineWidth1..3`, `lineStyle1` and `cmap.type` resolve and are **identical** in both states. No property distinguishes them.

Two consequences. First, contour-line visibility is not recoverable from property readback on this Origin version, so the `showLines` contract cannot be gated structurally and pixel comparison is the only detector -- which is what `compare_five_figure_batches.py` is for. Second, do not "verify" it by reading through `plot.get_int`: an unresolvable LabTalk property leaves the destination variable at its previous value, so an unguarded read returns the last number read and looks like evidence. The probe brackets every read with a sentinel and reports control expressions separately for exactly this reason.

`_apply_contour_line_style` commits its colormap edits with `updateScale()`, while the later `showLines(0)` in the path-overlay route does not. Adding a matching `updateScale()` was tried as a fix and **made the problem worse**: it re-commits the colormap from its scale settings, which restores the `showLines(1)` that `_apply_contour_line_style` had just set, so the lines came back. That change was reverted.

What the intermittency actually looks like, measured on Origin 2022 with the current code, by counting black pixels in the post-reopen export (6512 = lines off, 6945 = lines on):

| context | runs | lines off | lines on |
| --- | --- | --- | --- |
| fig12 alone, repeated in one Origin process | 20 | 19 | 1 |
| fig3 then fig12, repeated | 4 | 4 | 0 |
| full five-figure batches | 3 | 2 | 1 |

The flip happens **inside a single Origin process with identical inputs** -- the second of twenty otherwise identical standalone runs came out with the lines on. It is therefore not a function of launch mode, process age, or what ran before it; earlier batches that appeared to group by launch mode were coincidence at this rate. `showLines(0)` simply fails to persist to the saved project roughly one run in fourteen across all contexts observed here.

Two things follow, and the second is the important one.

The lines-off state is the canonical route: this document requires `showLines(0)` precisely so the editable source-vectorized boundary is not doubled. So the intermittent failure produces a **doubled boundary that the contract forbids**.

And the visual gate prefers that violation. Against the same source crop:

| metric | lines off (canonical) | lines on (doubled) | gate |
| --- | --- | --- | --- |
| `edge_f1` | 0.811466 (0.77% headroom) | 0.821642 (6.13%) | min 0.810 |
| `edge_score` | 0.750114 (2.01%) | 0.746058 (0.41%) | min 0.745 |
| `ssim_score` | 0.803696 | 0.801233 | min 0.777 |
| `color_score` | 0.970851 | 0.975088 | min 0.920 |

Both states pass, and each sits within roughly 2% of a different floor, so neither is comfortable. But `edge_f1` rewards the doubled boundary by +0.0102 -- a second boundary matches more source edge pixels -- which means the metric that is supposed to police boundary fidelity scores the contract violation higher than the compliant render. The promoted p18 baseline is a lines-on run, so the retained Fig12 evidence records the doubled-boundary state. Re-promoting Fig12 against a compliant render would leave `edge_f1` at 0.77% of budget, so that gate needs re-derivation from the canonical route rather than inheritance from a violating one.

### The round trip, and what was changed

Two defects in `_apply_contour_line_style` explain the mechanism.

It styled `lineColor1..3` and `lineWidth1..3` while every panel declares **four** z-levels, so the fourth contour line kept Origin's default styling. That is exactly what the stray segments are: 433 pure-black pixels forming two full-height vertical lines, black rather than the configured `(86, 107, 68)` because that slot was never written.

More importantly, the overlay route enabled the lines and then disabled them: `_apply_contour_line_style` ended with `showLines(1)` and `updateScale()`, and the caller then issued a bare `showLines(0)` with no commit of its own. The exported page therefore depended on whether that trailing command took effect. Adding `updateScale()` after it does **not** help and makes it worse -- that re-commits the colormap from its scale settings and restores the `showLines(1)` just set.

The function now takes the final visibility as an argument, styles all four slots, and sets colour, width, visibility and labels in one committed block. The overlay route asks for lines-off directly, so the enable-then-disable round trip no longer exists and cannot be half-applied.

Evidence for the change: 40 standalone live runs plus a full five-figure batch all produced byte-identical canonical exports, against a measured baseline failure rate of 2 in 27 (7.4%). Zero failures in 40 runs has p ~ 0.046 under that baseline, which is suggestive rather than conclusive on its own; the structural argument -- the command that produced the failing state is no longer issued -- carries the rest. Fig3, Fig14, Fig15 and Fig16 exports are unchanged byte for byte. Detection remains available through `scripts/compare_five_figure_batches.py`, and a Fig12 promotion claim should still state which state it captured.

## Export supersampling

`extract_aa2195_fresh_source_bundle.py` rasterises the source crops with PyMuPDF at scale 2.0-3.0, so a source crop carries a soft anti-aliased edge. Origin exports at the benchmark canvas 1:1, which does not. Measured on Fig3: the source has 256 distinct grey levels and 8.22% intermediate-grey pixels, the 1:1 export has 158 levels and 5.04%. That gap, not missing geometry, accounts for essentially all of Fig3's ink deficit -- the export is *darker* than the source in the very-dark band and short only in the mid-grey halo.

The optional `export_supersample` candidate parameter (integer, 1-4, default 1) renders the page at N times the canvas and resamples down with Lanczos, reproducing that edge physics. It changes only how the page is rasterised; the Worksheet bindings, plots and OPJU are untouched. `export_supersample=1` is the promoted path and is byte-identical to a build without the parameter. Any factor above 1 is recorded in the builder route and changes `render_identity.fingerprint`, so a supersampled export cannot be mistaken for a 1:1 one. `_effective_builder_route` in `scripts/origin_candidate_worker.py` is an allowlist: a route key missing from it is dropped silently, so a new rendering parameter must be registered there or it will not reach the identity.

Measured same-run on administrator Origin 2022:

| figure | metric | gate | N=1 | N=2 | N=3 |
| --- | --- | --- | --- | --- | --- |
| Fig3 | `foreground_f1` | min 0.520 | 0.535192 | 0.585823 | 0.591160 |
| Fig3 | `edge_f1` | min 0.550 | 0.569649 | 0.605866 | 0.612261 |
| Fig3 | `ssim_score` | min 0.650 | 0.732804 | 0.747381 | 0.746974 |
| Fig3 | `nonwhite_delta` | max 0.030 | 0.026751 | 0.006893 | 0.007398 |
| Fig3 | `color_score` | min 0.900 | 0.929951 | 0.911270 | 0.941897 |
| Fig14 | `edge_f1` | min 0.440 | 0.453847 | **0.424573 fails** | 0.466741 |
| Fig14 | `foreground_f1` | min 0.430 | 0.448658 | 0.465190 | 0.454363 |
| Fig14 | `registration_abs_dy_px` | max 6.0 | 5.500000 | 6.000000 | 6.000000 |
| Fig14 | `nonwhite_delta` | max 0.012 | 0.009684 | 0.001304 | 0.004062 |

Fig3 improves on every gate at N=3 and its `near_threshold_metrics` empties from `['edge_f1', 'foreground_f1']` to `[]`. Fig14 does not: N=2 fails `edge_f1` outright, and although N=3 passes, it drives `registration_abs_dy_px` to exactly its 6.0 px limit, i.e. zero headroom. Supersampling is therefore a per-figure decision backed by a same-run measurement, not a global default, and none of these variants is promoted. Promotion still requires the full live gate set plus the recorded identity.

## Fresh-extract release execution

When the source PDF is supplied and old data is disallowed, the accepted AA2195 route is a same-run `fresh_extract` batch. Use a new or empty output root, resolve Python 3.10 with `scripts/resolve_python310.ps1`, run `scripts/assert_admin_preflight.py` elevated, and attach to exactly one visible administrator Origin 2022 process. The batch must create a new `source_bundle/source_bundle.json`, materialize per-figure candidates from that same manifest, run Fig3/Fig12/Fig14/Fig15/Fig16 live workers, and finish with `live_validation_status.json` plus `five_figure_batch_audit.json`.

A successful rerun must report `same_run_fresh_source_verified=true`, `source_data_policy=fresh_extract`, stable visible Origin PID across all five figures, and `overall_release_pass=true` for each figure. Keep dry-run outputs separate from live outputs; dry-runs can validate candidate shape, template records, and source references, but cannot satisfy save/reopen/readback/export or visual release gates.

## Official-template evidence

Record candidate project/template hashes, reopen results, Worksheet rows, plot types, direct bindings, and selection reason. Official assets are not bundled and remain subject to OriginLab terms.

The shareable package also excludes paper-source rasters. Its candidate JSON files use an authorized-local-source placeholder; `aa2195-release-evidence.json` is a maintainer-attested index of reference-run hashes and scalar metrics, not a substitute for the retained live evidence artifacts. `validate_public_evidence_index.py` checks index consistency only and always reports `live_origin_verified=false` and `pass_eligible=false` for index-only validation.
