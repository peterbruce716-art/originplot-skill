# AA2195 Benchmark Contract

The packaged AA2195 builders are specialized implementations, not proof that arbitrary source images can be converted automatically.

## Fig3

- Four-layer source-calibrated stress-strain reconstruction with 44 direct Worksheet XY plots.
- PSC, UC, and TR retain one continuous editable X/Y source per curve. Their native Origin line styles are applied after plot insertion and must reopen as style codes 0 (solid), 2 (dotted), and 3 (dash-dot), respectively.
- The live gate retains strict MAE, layout, edge, color, and registration checks; the source-calibrated SSIM floor is 0.650.
- Every curve declares a canonical source group with `single_xy` continuity; line appearance is a plot property and does not fragment or duplicate the underlying data.
- Each of the four panels declares its own subplot-to-Worksheet contract and reopens against only that panel's curve Workbook. Its editable PSC/UC/TR legend rows use `\l(plot)` references to the actual colored curve plots, and every referenced plot must retain the row's native line style; no legend-only Workbook or Plot is permitted.

## Fig14

- One native XY page with nine direct Worksheet plots: three editable NaN-separated line plots, three independent marker overlays, and three editable error paths.
- The line/marker split is deliberate: Origin 2022 can overwrite grouped line styles when line-symbol plots are inserted. Reopened readback must report type-200 line and error plots, type-202 marker overlays with zero line width, nine direct Worksheet bindings, and the declared NaN dash runs.
- PSC/UC/TR markers, source-calibrated values, error extents, axes, legend, and Times New Roman typography survive save/reopen readback.
- The current same-run Origin 2022 route passes structure and visual gates; it is an editable reconstruction of the published raster, not raw experimental data recovery.
- Each PSC/UC/TR family is one canonical source group. The dense NaN-patterned line, anchor-marker view, and error path are deterministic views in the same reopened Worksheet.

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
- Calibrate stage-local S offsets and numeral glyph centering from the reopened export.
- Promotion requires all live visual gates plus the frozen source hash, effective builder route, geometry version, Origin version, and export profile. Metrics without that identity remain non-promoted.

## Official-template evidence

Record candidate project/template hashes, reopen results, Worksheet rows, plot types, direct bindings, and selection reason. Official assets are not bundled and remain subject to OriginLab terms.

The shareable package also excludes paper-source rasters. Its candidate JSON files use an authorized-local-source placeholder; `aa2195-release-evidence.json` is a sanitized index of reference-run hashes and scalar metrics, not a substitute for the retained live evidence artifacts.
