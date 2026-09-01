---
name: originplot
description: "Inspect CSV/TXT/XLS/XLSX scientific data, confirm column roles, plan one of ten general publication plot primitives, and build verified editable Origin/OriginPro projects through an administrator-only native Origin lifecycle. Use for line, scatter, line+scatter, error-bar, bar, grouped/stacked bar, heatmap planning, contour, multi-panel planning, reference-guided style planning, OPJU delivery, and AA2195 regression benchmarking."
---

# OriginPlot Skill v6.0

OriginPlot turns a read-only scientific table into an auditable FigureSpec, a deterministic OperationPlan, and—when authorized and live-mature—native editable Origin objects. The ordinary v6 core is general-purpose; AA2195 lives only under `benchmarks/aa2195/` as retained regression evidence.

## Hard runtime invariant

**Administrator policy is unchanged from v5.**

- Quick/Standard planning and controller work may run without administrator rights.
- Every process that imports `originpro`/`OriginExt`, attaches to Origin, builds, saves, reopens, reads back, or exports remains administrator-only.
- Release retains its continuous administrator envelope and cannot be weakened.
- Keep the existing visible-Origin identity checks, fail on a new Embedding process, and always detach attached sessions in `finally`.

Never work around these rules by changing DCOM, registry, firewall, user groups, Origin installation, or process identity.

## Beginner path

For a new table, prefer:

```powershell
originplot.cmd doctor --origin-version 2022
originplot.cmd inspect data.xlsx
originplot.cmd draw data.xlsx --x Strain --y Stress --plot-type line_scatter
```

If column meanings are sufficiently clear, `draw` can use the high-confidence semantic roles. If unresolved numeric columns remain, do not guess: ask only for the needed mapping and rerun with explicit `--x`, `--y`, `--x-error`, `--y-error`, `--category`, or `--z`.

Advanced commands:

```powershell
originplot.cmd plan data.xlsx --plot-type errorbar --x Time --y Signal --y-error SD --output figure.json
originplot.cmd render figure.json --output-dir output
originplot.cmd verify output
```

## Semantic boundary

Classify every source column as exactly one of:

`x`, `y`, `x_error`, `y_error`, `z`, `group`, `category`, `label`, `support`, `retain`, `uncertain`.

`uncertain` is a question, not another automatic curve. The source file is immutable. Do not silently:

- fit or smooth;
- normalize;
- delete outliers;
- create error bars from unstated assumptions;
- identify peaks, phases, transitions, or materials;
- calculate scientific quantities;
- invent or fill measurements;
- pivot, split, aggregate, or reshape long-form groups.

An explicit user mapping resolves semantic uncertainty for the selected plot; unrelated unknown columns are retained, not rendered.

### Categorical tables

Automatic categorical planning is limited to transformations that do not change the source-table meaning:

- `category + one Y` may compile to `bar`;
- `category + multiple Y columns` is wide form and may compile to `grouped_bar`, with one series per Y column;
- `category + group + one Y` is long form. Do not infer a pivot, group split, aggregation, or stacked layout. Automatic `bar`/`grouped_bar`/`stacked_bar` planning must fail closed and require a manually confirmed FigureSpec with explicit series mappings or an explicitly transformed source.

## FigureSpec v6 is the ordinary-workflow contract

The formal schema is `originplot.figurespec.v6`. It contains:

- `source`: file, sheet and SHA-256;
- `data`: explicit series or matrix mappings;
- `figure`: primitive and axes;
- `style`: theme, series and legend choices;
- `layout`: page/panel geometry;
- `verification`: profile and required gates.

If the source hash changes, the prior confirmed spec is stale. Builders must never reinterpret source-column roles after FigureSpec is frozen.

## Ten v6 primitives

The public planning/compile registry contains exactly:

- `line`
- `scatter`
- `line_scatter`
- `errorbar`
- `bar`
- `grouped_bar`
- `stacked_bar`
- `heatmap`
- `contour`
- `multi_panel`

They are implemented through four compact compiler families: XY, categorical bars, matrix/XYZ, and composition. `multi_panel` composes child builders rather than duplicating plot logic.

Domain workflows such as stress-strain, XRD, Rietveld, electrochemistry, or spectroscopy should be semantic/style presets that compile to these primitives. Do not create a new Origin API subsystem for each scientific field.

### Capability maturity is separate from compile support

Never equate a registered builder with promoted live Origin evidence. `doctor` exposes:

- `compile_primitives`: FigureSpec/OperationPlan support;
- `live_candidate_primitives`: primitives that may enter the live worker but still require same-run verification;
- `live_evidence_primitives`: primitives with explicitly promoted v6 evidence;
- `primitive_maturity`: per-primitive compile/live status and reason.

At v6.0, repository-wide `live_evidence_primitives` remains empty until new licensed-Origin evidence is deliberately promoted. A successful individual live run proves that run only.

`heatmap` and `multi_panel` are compile-only in v6.0 and must fail **before launching the elevated Origin worker** when live execution is requested. `heatmap` uses `E524_HEATMAP_LIVE_UNVERIFIED`; `multi_panel` uses `E527_LIVE_PRIMITIVE_BLOCKED`. Do not silently grid/bin XYZ data, synthesize a matrix, or pretend panel composition was executed. Promotion requires the missing native adapter behavior plus fresh same-run licensed-Origin evidence.

## Builder and adapter boundary

Builders only perform:

```text
FigureSpec -> OperationPlan
```

They do not import or call Origin. `originplot.operation_plan.v1` is declarative and can be tested offline.

Only `originplot/adapters/originpro.py` translates an OperationPlan into native Worksheet-backed Origin objects. This keeps data semantics, plotting logic, and application automation independently testable.

## Live completion gates

A successful live Quick/Standard run requires the native lifecycle:

1. elevated worker authorization;
2. attach to the authorized visible Origin process;
3. native Worksheet and graph construction;
4. direct Plot-to-Worksheet binding;
5. save `figure.opju`;
6. detach;
7. reattach and reopen `figure.opju`;
8. read back editable plots and bindings;
9. export from the reopened Origin project;
10. reject blank export or Demo watermark.

A Python/Matplotlib redraw, screenshot, raster background, dry run, or capability declaration is never a completed Origin deliverable.

Canonical ordinary outputs are:

```text
figure.opju
figure.png
figure.pdf
figure.tif
figure_spec.json
verification.json
```

`operation_plan.json` may also be retained for audit/debugging.

## Profiles

### Quick

Use for routine supported plots and style iteration. It still requires native save/reopen/binding/export when live, but makes no formal benchmark visual claim.

### Standard

Default for SCI plotting. It may perform bounded template discovery/style assistance, but template failure must not silently change data semantics. Same live structure gates remain mandatory.

### Release

Release is fail-closed and cannot be weakened. During the v6 migration, the historical AA2195 strict release/evidence identity remains under `benchmarks/aa2195/`; do not relabel old 5.8.9-p18 evidence as v6 evidence. A general v6 Release route must remain blocked until it earns new same-run live evidence.

## Origin versions and doctor

Python 3.10 remains the validated baseline. `doctor` is read-only and does not launch Origin.

Capability status is explicit:

- Origin 2022: validated environment baseline;
- Origin 2024: compatible-unverified until receiving-machine smoke/readback passes;
- Origin 2026: experimental;
- unknown versions: fail closed for live claims.

The authoritative v6 capability profiles live inside `originplot/runtime/profiles/` and are packaged with the installable runtime. Source checkout, installed wheel, and compact Skill package must therefore resolve the same v6 profiles. `ready_for_live_worker` means only that the environment can attempt an authorized worker. It does not promote a primitive to live evidence. Capability metadata never waives administrator or same-run verification requirements.

## Reference figures

A reference image may suggest panel structure, mark type, line/symbol use, page ratio, legend placement and allow-listed style values. It may not contribute scientific values, labels, fits, phase assignments, logos, watermarks, or bitmap content to the editable result.

Priority is:

```text
explicit user style > confirmed reference suggestion > preset > OriginPlot default
```

Reference-derived choices must ultimately become normal FigureSpec `style`/`layout` fields. Do not create a parallel image-reproduction execution engine.

## Packaging boundary

The installable `originplot` package owns all ordinary runtime assets required by the product path: administrator worker, PowerShell elevation launcher, template discovery/retrieval logic, and v6 capability profiles. Product code under `originplot/` must not import the repository-root `scripts` package.

The default shareable Skill package intentionally excludes root `scripts/`, benchmark content, generated/private scientific files, and v5-named contracts. Repository-root scripts may remain only as development/benchmark compatibility tooling; ordinary installed execution must not depend on them.

## AA2195 benchmark

`benchmarks/aa2195/` preserves Fig3/Fig12/Fig14/Fig15/Fig16 builders, configuration, candidates, historical protocols and evidence. Product core under `originplot/` must never import this benchmark package. Benchmark compatibility bridges may import the benchmark from legacy wrappers while migration support remains.

## Claims

Report exactly what ran:

- semantic inspection is not scientific analysis;
- dry run is planning only;
- compile support is not live evidence;
- editable completion is not release eligibility;
- compatibility is not verification;
- historical AA2195 evidence applies only to its recorded identities;
- never claim raw-data recovery, automatic arbitrary-image-to-OPJU reproduction, or cross-machine pixel identity.
