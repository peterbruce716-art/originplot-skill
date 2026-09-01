# OriginPlot v6 Design

## Goal

Turn OriginPlot from an AA2195-centered reproduction framework into a compact, general scientific plotting skill while preserving its strongest invariant: administrator-controlled native Origin execution with save, detach, reopen, binding readback, Origin export, and verification.

## Non-negotiable runtime invariant

Administrator behavior does not change in v6. Quick and Standard controllers may remain non-administrator, but every worker that touches Origin remains elevated. Release retains the continuous administrator envelope and strict fail-closed lifecycle. The existing attach identity checks, `op.detach()` behavior, same-run evidence rules, and release evidence semantics remain authoritative.

## Product boundary

OriginPlot v6 accepts CSV, TSV/TXT, XLS and XLSX scientific tables, understands column roles, recommends supported plot primitives, freezes the user's scientific intent into FigureSpec v6, compiles that spec to a deterministic OperationPlan, executes the plan in Origin, then verifies the reopened editable project.

It does not silently fit, smooth, normalize, delete outliers, infer error bars, identify peaks/phases, calculate scientific quantities, or invent missing measurements.

## Architecture

```text
source table
  -> semantic inspection
  -> DataUnderstanding
  -> confirmed FigureSpec v6
  -> Builder Registry
  -> OperationPlan
  -> elevated Origin adapter/runtime
  -> save -> detach -> reopen -> readback -> Origin export
  -> verification/report
```

### Core packages

- `originplot/semantic/`: table inspection, column-role inference, plot recommendations.
- `originplot/spec/`: FigureSpec v6 validation and normalized data mapping.
- `originplot/builders/`: primitive compilers. Builders never import `originpro`.
- `originplot/adapters/`: OperationPlan-to-Origin execution.
- `originplot/runtime/`: administrator/elevation policy, Origin session identity, doctor and version capability resolution.
- `originplot/verification/`: reopened structure, binding and artifact checks.
- `originplot/cli/`: user-facing `doctor`, `inspect`, `plan`, `render`, `draw`, `verify` commands.
- `originplot/presets/`: small semantic/style presets; presets contain no Origin API code.

## FigureSpec v6

FigureSpec is the only formal input for ordinary v6 rendering. It contains:

- `schema`: `originplot.figurespec.v6`
- `source`: file, sheet, hash
- `data`: explicit series/matrix mappings
- `figure`: plot type, axes and semantic labels
- `style`: theme, per-series and legend preferences
- `layout`: page and panel geometry
- `verification`: profile and required gates

Once confirmed, builders do not infer or change source-column roles.

## Semantic model

Every source column is classified exactly once as one of:

`x`, `y`, `x_error`, `y_error`, `z`, `group`, `category`, `label`, `support`, `retain`, `uncertain`.

Ambiguous columns remain `uncertain`; they are not promoted to visible data automatically. Recommendations are based on structural evidence and small allow-listed presets, not aesthetic guessing.

## Primitive builders

v6.0 supports ten public primitives implemented through four compiler families:

- XY family: `line`, `scatter`, `line_scatter`, `errorbar`
- categorical family: `bar`, `grouped_bar`, `stacked_bar`
- matrix family: `heatmap`, `contour`
- composition: `multi_panel`

`multi_panel` resolves and compiles child primitives rather than reimplementing plotting logic.

## OperationPlan

Builders compile FigureSpec into `originplot.operation_plan.v1`. Operations are declarative and Origin-independent, including workbook/sheet creation, column writes, graph/layer creation, native plot binding, axes, legends, page geometry and export intent. The Origin adapter is the only layer allowed to translate these operations into `originpro`/LabTalk calls.

## Runtime and capabilities

`originplot doctor` reports Python, platform, administrator state, Origin discovery, `originpro`/`OriginExt`, and a capability profile. Compatibility data for Origin 2022/2024/2026 is retained and elevated into runtime dispatch. Origin 2022 remains the validated baseline; newer versions may be reported as compatible or experimental rather than falsely verified.

Administrator rules are not relaxed by capability probing.

## Profiles

- `quick`: native editable completion, reopen and binding checks; no formal visual claim.
- `standard`: default SCI workflow; bounded template/style assistance and visual artifact checks.
- `release`: strict evidence, hashes, lineage and benchmark gates; cannot be weakened.

All live profiles retain save/reopen/binding/export gates. A disabled gate is `not_required`, never `pass`.

## Outputs

Quick/Standard use a compact canonical set:

- `figure.opju`
- `figure.png`
- `figure.pdf`
- `figure.tif`
- `figure_spec.json`
- `verification.json`

Release may add `evidence/`, hashes, readback, provenance, metrics and manifest artifacts.

## Reference figures

A reference image can only contribute confirmed `StyleSpec`/layout suggestions. It cannot supply scientific values, labels, fits, phase assignments, logos, watermarks or raster content for the editable project. Explicit user style choices override confirmed reference suggestions, which override presets, which override defaults.

## AA2195

AA2195 Fig3/Fig12/Fig14/Fig15/Fig16 remains valuable regression evidence but is removed from the ordinary product core and moved under `benchmarks/aa2195/`. Core modules must not import benchmark modules. Benchmarks may import the core runtime and verification packages.

## Aggressive cleanup

v6 removes or retires version-specific top-level protocol documents, duplicate legacy controllers, old migration-only execution paths and product-core AA2195 special cases. Stable error semantics and release evidence needed by the benchmark are retained under the benchmark subtree.

## Success criteria

1. Ordinary plotting has no AA2195 dependency.
2. Controller/CLI contains no `generic_line` special case.
3. All ten primitives resolve through one registry and compile offline.
4. Semantic inspection supports CSV/TSV/TXT/XLS/XLSX without modifying sources.
5. Live Origin operations remain administrator-only exactly as before.
6. Save/detach/reopen/readback/export remains mandatory for live completion.
7. Offline CI tests FigureSpec, semantic inspection, builder compilation, registry, doctor/capabilities and package boundaries without launching Origin.
8. AA2195 is isolated as a benchmark/regression package.
