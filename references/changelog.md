# Changelog

## v5.8.9-p18.2

- Enforced explicit "reproduce again / do not use old data" requests as `fresh_extract` runs from the original PDF in a new output root; fresh manifests now reject any parent, reuse, or validated-source lineage before Origin attach.
- Increased fresh Fig3 vector-path sampling to 181 points per curve without smoothing, retained endpoint and monotonic-X checks, and recorded the dense source route in the same-run bundle.
- Matched Fig15 source typography with Times New Roman, added bounded endpoint-preserving raster stair-step suppression, and enforced dotted guide style code 2 after save/reopen in both layers.
- Added `-LaunchOriginExe` to the elevated five-figure runner. It prepares fresh source data first, rejects all pre-existing visible or hidden Origin processes, launches one Origin instance, attaches immediately, and records `origin_launch_mode=batch_started`.
- Recorded the final run007 same-run administrator Origin 2022 batch. All five figures passed live, structure, visual, source-data, and release gates with one stable visible PID and zero audit findings. The evidence remains identified as contract/evidence version p18 and is not relabeled as a p18.2 contract run.

## v5.8.9-p18.1

- Added `version.json` as the canonical release/contract/evidence version source. This release revision remains on the p18 functional contract and does not relabel the retained p18 Origin evidence.
- Excluded `.venv`, `venv`, `site-packages`, local Python binaries, coverage output, type-checker/linter caches, and symlinked directories from shareable-package traversal; polluted archives now fail closed with stable contamination codes.
- Removed the deprecated explicit Pillow mask mode while preserving 8-bit `L` pixels and dilation behavior.
- Added machine validation for the sanitized AA2195 evidence index, including five-figure uniqueness, SHA-256 format, finite bounded metrics, Fig16's 21-segment boundary record, and explicit public-verification limits. Index-only validation never promotes live or pass-eligible status.
- Corrected the offline CI package filename from the stale p14 label to p18.1. No new Windows + Origin 2022 live E2E was claimed for this maintenance release.

## v5.8.9-p18

- Corrected Fig14 fresh-source marker extraction so the 250 degrees C data points are not averaged with same-x legend symbols.
- Replaced the same-x black-pixel union with marker-local connected-component selection for Fig14 error bars; marker occlusion now uses the largest visible one-sided extent instead of collapsing or merging error ranges.
- Added synthetic regressions for same-x series separation, legend exclusion, and one-sided marker occlusion.
- Added registration-normalized foreground F1 and edge F1 to visual evidence and made both blocking gates for Fig3, Fig12, Fig14, Fig15, and Fig16, together with per-figure foreground-density limits.
- Bumped the Fig14 geometry/data route identity to `aa2195_fig14_component_errorbars_native_scatter_dash_v4`. Marker overlays now use native scatter plots so Origin cannot render a zero-width connecting hairline over the dashed series. Prior p17 evidence remains historical and is not promoted as p18 evidence.
- Added `validated_crop_reextract`, a fail-closed lineage route that applies the corrected Fig14 extractor to a promoted source crop without reopening the PDF; it rejects parent-hash drift, failed prior quality evidence, any unrelated data change, or a missing corrected extraction method.
- Added a Fig16 color-component boundary audit over all 21 WH/DRV/DRX segments. Missing segments, maximum boundary error above 1 px, or mean boundary error above 0.5 px now block promotion.
- Removed the stale Fig16 DRX height reduction and stage-local S-slot left shifts that caused 2 px top-boundary and 1-3 px horizontal-boundary errors; bumped the route identity to `aa2195_fig16_segment_boundary_calibrated_v7`.
- Recorded the final same-run administrator Origin 2022 p18 batch: Fig3, Fig12, Fig14, Fig15, and Fig16 all passed with one stable visible Origin PID and zero audit findings. Fig14 native scatter markers reopened with shapes 1/2/3 and retained the three dashed source series; Fig16 detected all 21 bar segments with zero missing, 1 px maximum boundary error, and 0.476190 px mean boundary error.

## v5.8.9-p17

- Replaced the blanket same-run data-extraction rule with explicit `fresh_extract` and `validated_reuse` source-data policies.
- Added `build_validated_data_reuse_record.py`; it authorizes reuse only when the prior five-figure audit has no findings and every figure passed live Origin, structure, visual, provenance, and release gates.
- Reused curves, markers, error bars, fields, bar segments, and source crops remain hash-verified. Missing, failed, or drifted reuse evidence stops before Origin attach with `E128_SOURCE_DATA_REUSE_REJECTED`.
- Kept construction evidence strict: a reuse run creates new Worksheets and OPJUs and repeats save/detach/reopen/readback/export/visual QA. Prior OPJUs, exports, readbacks, and metric files remain forbidden as pass evidence.
- Extended the five-figure audit and offline behavior tests to require a passing source-data gate for either policy.

## v5.8.9-p16

- Added same-run AA2195 PDF crop and scientific-data extraction for Fig3, Fig12, Fig14, Fig15, and Fig16.
- Required `-SourcePdf`, `fresh_source_required=true`, and crop/data hash verification before Origin attach.
- Retained validated local layout, typography, editable-object, and calibration routes as references while preventing inherited scientific data, OPJUs, exports, and readbacks from entering a fresh batch.
- Added fresh-source digests to builder routes, readback, and render identity; Fig12 analytic fallback is forbidden for the five-figure fresh rebuild.
- Updated offline tests with explicit synthetic fresh-source fixtures; production builders remain fail-closed.
- Fixed relocated live candidates by resolving the official template-search record before copying; batch completion now also requires five zero worker exit codes.
- Fig14 now uses freshly digitized anchors with Origin-native dashed lines and fails closed when post-reopen line-style readback falls back to solid.
- Fig16 retains the 15% native column gap and uses an editable `#fefefe` layer background to match the PDF raster mean while preserving exact freshly extracted WH/DRV/DRX colors.

## 2026-07-14 Graph Gallery discovery and basic-data intake update

- Added bounded keyword or Gallery-URL discovery that resolves GID detail pages, records structured retry evidence, and extracts only official Graph Gallery ZIP links.
- Reused the existing archive validator and retriever for optional downloads, added official-detail `Referer` support, retained the 20-candidate hard limit, and avoided overwriting existing archives unless explicitly requested.
- Expanded skill triggering and intake guidance for template matching and Excel/CSV scatter, line, or line-symbol requests while keeping `generic_line` offline-only and making no new live-builder or Origin-evidence claim.

## v5.8.9-p15

- The five-figure live runner now accepts one visible `Origin64`, `Origin_64`, `Origin_32`, or `Origin` process while preserving the same-PID attach and batch audit policy.
- Added fail-closed post-reopen `plot_style_contracts` for the three Fig14 PID 202 marker overlays, including persisted Origin 2022 symbol-shape and symbol-size readback.
- Extended the five-figure batch audit so Fig14 marker-style drift fails the batch release gate.
- Hardened the live batch runner to require one Python 3.10 executable and an administrator preflight before Origin attachment, then reuse that executable for every worker and the final audit.
- Kept the source-tree V4 legacy-document assertion while allowing the packaged suite to run after the shareable-package policy intentionally excludes that legacy protocol file.
- Preserved the recorded p14 AA2195 evidence as historical reference evidence. The p15 version label does not relabel those runs or claim a new p15 five-figure live pass.

## 2026-07-14 Fig14 persisted-marker and batch-preflight update

- Made Fig14 symbol shape and size explicit Origin 2022 LabTalk properties and added post-reopen `plot_style_contracts` validation for the three PID 202 marker overlays.
- Made the five-figure batch audit fail closed with `PLOT_STYLE_FAILED` when Fig14 marker semantics are missing or drifted.
- Made the five-figure runner resolve and require Python 3.10, write `admin_preflight.json` before Origin attach, and use the same Python executable for all workers and the audit.
- Recorded a new administrator Origin 2022 Fig14 live canary with shapes 1/2/3 and size 10.5 verified after reopen. All visual gates passed (MAE 0.040352, SSIM 0.833945, layout 0.974196, edge 0.780529, color 0.987886). This single-figure canary proves the new closure but does not replace the earlier five-figure same-run batch; mixed metric movement is not described as uniform pixel improvement.

## 2026-07-13 morphology-proportion audit update

- Required every identifiable morphology that affects source fidelity to declare its measurable ratios, normalization reference, tolerance, audit stage, and optional visible ordering before construction.
- Added a generic fail-closed morphology-ratio validator; missing declarations, missing post-export measurements, order violations, and out-of-tolerance ratios now fail the visual-structure gate.
- Applied the rule beyond column charts to stacked shares, panel/object dimensions, gaps, regional occupancy, and other measurable shape relationships without changing frozen AA2195 evidence.

## 2026-07-13 mixed column-arrangement and native-cap update

- Required each column/bar layer to declare `side_by_side`, `cumulative_stack`, or noncumulative `nested_overlap` independently, including plot order and per-series width controls for nested overlays.
- Defined the geometry distinction between cumulative stacking and same-baseline nested overlap so touching bars in a raster reference are not automatically treated as stacked values.
- Extended the native Origin 2022 YErr contract to intentionally overlapped columns and required a recorded native cap-width control with final-size evidence that every cap is narrower than its visible column.
- Kept the update additive to the `5.8.9-p14` runtime and frozen AA2195 benchmark evidence; the new KYBD run is task-local evidence and does not promote unrelated builders.

## 2026-07-13 administrator-envelope and demo-restart update

- Added an explicit administrator preflight before the first action that can feed a live run; elevating only the final Origin worker is now forbidden.
- Extended the single privilege envelope through template retrieval/inspection, candidate materialization, Origin save/reopen/readback/export, evidence packaging, and cleanup.
- Made every demo-watermark result invalidate the complete run and emit a machine-readable restart directive requiring a new run ID, clean output root, and full restart from administrator preflight.
- Limited demo-watermark restart to one fully elevated retry. A repeated watermark is a license/environment failure, not a reason to loop or accept contaminated evidence.

## 2026-07-13 template-retrieval resilience update

- Prohibited treating a single search-tool, parser, redirect, or download failure as evidence that OriginLab is unavailable.
- Required at least three bounded attempts after failures unless an earlier retry succeeds, at least two retrieval methods before declaring exhaustion, alternate close Gallery candidates when available, and recorded local-catalog and installed-template fallback.
- Added `scripts/retrieve_official_template.py` to reject HTML error pages, validate ZIP signatures and integrity, prevent unsafe extraction paths, record SHA256 and attempt evidence, and support multiple official URLs.
- Added `E131_TEMPLATE_RETRIEVAL_EXHAUSTED` for transparent failure only after the complete retry matrix is exhausted. This maintenance update does not change the frozen AA2195 builder evidence or inherit a new live pass.

## 2026-07-13 publication-contract extension

- Added a machine-validatable `originplot.publication_contract.v1` that gates conclusion-first panel design, evidence hierarchy, source traceability, final physical size, statistics and uncertainty, accessibility, and export requirements before a new builder or material restyle.
- Added explicit journal-style tokens for JMPT, Acta Materialia, IJP, MSEA, Nature, source fidelity, and custom profiles. These are house defaults and require current author-guide verification; they are not represented as journal mandates.
- Added materials/EBSD figure QA rules that keep GOS, KAM, LAGB/HAGB, IPF, and recrystallization claims distinct and require multi-evidence support for CDRX/DDRX interpretations.
- Kept this extension additive to the `5.8.9-p14` Origin runtime and frozen AA2195 builders. It does not inherit live evidence or change their pass status.

## 5.8.9-p14 subplot Worksheet closure

- Added `originplot.subplot_worksheet_bindings.v1` and `subplot_worksheet_contracts` for Fig3/Fig12/Fig14/Fig15/Fig16.
- The post-reopen structure gate now proves every declared subplot/layer contains editable plots bound to its corresponding Workbook alias, Worksheet, and X/Y(/Z) columns.
- The five-figure batch audit fails closed on missing or failed per-subplot Worksheet evidence.
- Replaced Fig3's legend-only Worksheet plots and Fig16's legend micro-layer plots with editable `\l(plot)` references to their actual curves/columns; added a plot-derived legend readback gate.
- Recalibrated Fig16's plot-derived legend after user visual review and Origin reopen pixel readback: its top border stays inside the page, WH/DRV share one 2 px border, and DRV/DRX retain the source's 3 px white gap.
- Corrected Fig3's PSC/UC/TR plot and legend semantics: all curve Worksheets now keep continuous X/Y data, native Origin line-style commands preserve solid/dotted/dash-dot patterns, and reopen validation checks every plot referenced by each legend row.
- Corrected Origin 2022 line-style inspection to use the persisted LabTalk `get dataset -d` value; generic `Plot.get_int("line.style")` reports zero even for saved dotted and dash-dot plots and is no longer accepted for the reopen gate.

## v5.8.9-p14

Scope honesty, skill refactor, dependency reproducibility, offline CI, and extensible builder registry. Active instructions were separated from benchmark details and historical records. CLI and manifest states now distinguish planning, command success, live structure, live visual verification, and pass eligibility.

The canonical Fig12 route was promoted after administrator Origin 2022 save/reopen validation. It retains native XYZ Worksheets, adds editable type-34 source-vectorized regions and editable page-coordinate axis titles, and passes all declared visual gates (MAE 0.035472, SSIM 0.801507, layout 0.992431, edge 0.745290, color 0.977127). A packaging and contract-hardening update removes all source rasters from shareable archives, sanitizes packaged source paths, adds type-34 and geometry checks, isolates transient SVG imports, aligns Fig12 defaults, and reports near-threshold metric margins. The five named routes have pass evidence only within their recorded benchmark scopes and reference environment.

The 2026-07-13 maintenance update maps the upstream FigureSpec hierarchy into the local V5 intake contract without claiming universal execution. Fig14 now separates each editable line, marker overlay, and error path so Origin 2022 cannot silently replace the UC/TR dash semantics on reopen. The revised route has nine direct Worksheet plots and passed a five-figure same-run Origin 2022 batch (MAE 0.039869, SSIM 0.837364, layout 0.974196, edge 0.786489, color 0.981307); the slight MAE/SSIM tradeoff is retained explicitly rather than described as uniform metric improvement. The batch runner also resolves its default skill root after PowerShell parameter binding, preventing an empty `$PSCommandPath` default-expression failure.

The canonical-source maintenance extension adds `originplot.source_geometry_groups.v1` and makes its post-reopen validation a structure gate. Fig3 keeps every curve in one continuous X/Y view and stores its dash semantics as a native plot property; Fig15 preserves multi-segment geometry in single NaN-separated X/Y views; Fig14 binds line, marker, and error views to one logical series group in the same Worksheet; Fig12 links XYZ sampling and type-34 local regions to one classified field; Fig16 links stacked families and each fill/border swatch to one canonical row or bbox source. This extension has offline regression evidence until a new same-run administrator Origin batch is recorded; it does not inherit or replace the prior live evidence.

## v5.8.9-p13 and earlier

p13 hardened release acceptance and Fig12 targeted optimization. Earlier p1-p12 work established Origin 2022 unit calibration, Fig15 object persistence and frozen regression evidence, Fig16 native geometry/stack semantics, deep plot readback, portable release validation, and same-run evidence materialization.

Named workspace runs such as Run015, Run047, Run052, Run062, and Run095 are historical diagnostics. They may identify comparators in a project report, but they are not active Skill instructions and cannot substitute for current same-run evidence.
