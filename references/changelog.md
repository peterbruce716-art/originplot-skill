# Changelog

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
