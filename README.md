# OriginPlot v6

**AI-assisted, auditable, editable scientific plotting in Origin/OriginPro.**

OriginPlot v6 is a compact general-purpose plotting skill: give it a CSV/TXT/XLS/XLSX table, confirm the scientific column mapping, and it compiles a deterministic FigureSpec/OperationPlan before an administrator-only Origin worker creates and verifies the editable project.

The project deliberately separates **scientific meaning**, **plot compilation**, and **Origin automation**. It does not treat a Python preview as an Origin result, silently reshape scientific data, or claim a style was applied when the live adapter cannot execute it.

## Architecture

```text
scientific table
  -> semantic inspection
  -> confirmed FigureSpec v6
  -> primitive Builder Registry
  -> OperationPlan
  -> elevated Origin adapter
  -> save -> detach -> reopen -> binding readback -> Origin exports
```

AA2195 Fig3/Fig12/Fig14/Fig15/Fig16 is retained under [`benchmarks/aa2195`](benchmarks/aa2195/) as regression evidence instead of being part of ordinary plotting logic.

## Quick start

Windows + Python 3.10:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python -m pip install .
.\.venv\Scripts\python -m pip install -r requirements-origin.txt
```

Then:

```powershell
originplot.cmd doctor --origin-version 2022
originplot.cmd inspect experiment.xlsx
originplot.cmd draw experiment.xlsx --plot-type line_scatter --x Strain --y Stress
```

For an error-bar plot:

```powershell
originplot.cmd draw experiment.xlsx `
  --plot-type errorbar `
  --x Time --y Signal --y-error SD
```

To separate planning from live Origin execution:

```powershell
originplot.cmd plan experiment.xlsx --plot-type line --x Time --y Signal --output figure.json
originplot.cmd render figure.json --dry-run --output-dir plan-check
originplot.cmd render figure.json --output-dir final
originplot.cmd verify final
```

## Administrator policy

**v6 does not relax the administrator design.**

Quick/Standard controllers may be non-admin, but the dedicated worker that imports `originpro`/`OriginExt`, attaches, builds, saves, reopens, reads back or exports is still elevated. Release remains stricter and requires its continuous administrator envelope.

The runtime still checks the authorized visible Origin process identity and rejects session drift/new Embedding processes. The v6 refactor changes architecture, not this reliability policy.

## Ten plot primitives

v6.0 exposes exactly ten public planning/compile primitives:

| Family | Primitives |
|---|---|
| XY | `line`, `scatter`, `line_scatter`, `errorbar` |
| Categorical | `bar`, `grouped_bar`, `stacked_bar` |
| Matrix/XYZ | `heatmap`, `contour` |
| Composition | `multi_panel` |

Internally these are four compiler families, not ten duplicated plotting engines. New scientific domains should normally add semantic/style presets that compile to these primitives.

### Compile support is not live evidence

`originplot.cmd doctor` reports:

```text
compile_primitives
live_candidate_primitives
live_evidence_primitives
primitive_maturity
```

At v6.0, no general primitive is promoted as repository-wide live evidence merely because offline CI passes. A successful live run must earn its own same-run save/reopen/binding/export verification.

`heatmap` and `multi_panel` are currently compile-only. Live execution is blocked **before the elevated Origin worker starts**: `heatmap` uses `E524_HEATMAP_LIVE_UNVERIFIED`; `multi_panel` uses `E527_LIVE_PRIMITIVE_BLOCKED`. Promotion requires the missing native adapter behavior plus fresh licensed-Origin evidence.

## Conservative data understanding

Every source column is assigned one role:

```text
x / y / x_error / y_error / z / group / category / label / support / retain / uncertain
```

A numeric column with unclear meaning remains `uncertain`. OriginPlot will not quietly turn it into another curve.

Categorical auto-planning is intentionally conservative:

- `category + one Y` may become `bar`;
- `category + multiple Y columns` is treated as wide-form data and may become `grouped_bar`, with one explicit series per Y column;
- `category + group + one Y` is long-form data and is **not** silently pivoted, split, grouped, aggregated or stacked.

A hand-written FigureSpec does not bypass execution reality. XY builders currently execute `x`, `y`, `x_error`, and `y_error`; per-point `label` mappings are rejected. Bar builders execute `category`, `y`, and optional `y_error`; `group`/`label` mappings are rejected until the live adapter actually implements them.

OriginPlot does **not** silently smooth, normalize, fit, remove outliers, calculate error bars, identify peaks/phases, pivot long-form groups, or compute scientific results.

## FigureSpec v6

Ordinary plotting has one formal contract: `originplot.figurespec.v6`.

```json
{
  "schema": "originplot.figurespec.v6",
  "source": {
    "file": "stress.csv",
    "hash": "..."
  },
  "data": {
    "series": [
      {"id": "sample", "x": "Strain", "y": "Stress", "y_error": "Stress SD"}
    ]
  },
  "figure": {
    "id": "stress_strain",
    "type": "errorbar",
    "x_axis": {"title": "Strain", "unit": "%"},
    "y_axis": {"title": "Stress", "unit": "MPa"}
  },
  "style": {
    "series": {"sample": {"color": "red", "line_width_pt": 1.5}},
    "legend": {"visible": true, "frame": false}
  },
  "layout": {"page": {"width_cm": 18, "height_cm": 12}},
  "verification": {"profile": "standard"}
}
```

The source SHA-256 is frozen with the plan. If the source changes, the confirmed specification is stale instead of silently being reused.

## Executable style surface

v6.0 intentionally accepts only style fields for which the ordinary Origin adapter has a deterministic execution path:

```text
series.<id>.color
series.<id>.line_color
series.<id>.line_width_pt
series.<id>.symbol
legend.visible
legend.frame
```

Unsupported aliases are not silently retained. `theme`, `legend.position`, symbol size, transparency, matrix colormap/levels/colorbar options and other unimplemented fields go to `style_audit.rejected` and must not be reported as applied.

Style precedence is:

```text
explicit user choice > confirmed reference suggestion > preset > OriginPlot default
```

Precedence applies only among executable fields. Unsupported higher-priority values are still rejected.

## Builder and OperationPlan boundary

Builders never import Origin. Their entire job is:

```text
FigureSpec -> originplot.operation_plan.v1
```

The OperationPlan contains declarative actions for workbooks, graph/layers, native plot bindings, axes, legends, page geometry and export intent. Only [`originplot/adapters/originpro.py`](originplot/adapters/originpro.py) translates those operations into Origin calls.

Unknown OperationPlan actions fail with `E520_OPERATION_PLAN_INVALID` before live Origin execution. The adapter never silently skips a misspelled or unimplemented action.

## Verified live lifecycle

A completed live run requires:

1. elevated Origin worker;
2. authorized Origin attach;
3. native Worksheet-backed plotting;
4. OPJU save;
5. detach;
6. reopen;
7. editable plot + Worksheet binding readback;
8. final Origin export;
9. nonblank PNG/PDF/TIF checks;
10. Demo-watermark rejection.

`live_origin_verified` is true only if **all required live gates pass**. Merely entering Origin, building a graph, or saving an intermediate OPJU is not enough.

Canonical ordinary outputs:

```text
figure.opju
figure.png
figure.pdf
figure.tif
figure_spec.json
verification.json
```

`operation_plan.json` is also retained for audit/debugging.

## Origin versions

`originplot.cmd doctor` is read-only; it does not launch Origin.

Current status model:

- **Origin 2022** — validated environment baseline;
- **Origin 2024** — compatible-unverified until same-machine smoke/readback passes;
- **Origin 2026** — experimental;
- unknown versions — no automatic live claim.

The v6 capability profiles are package-owned runtime data under `originplot/runtime/profiles/`, so the same profiles are used from a source checkout, an installed wheel, and the compact Skill package. `ready_for_live_worker` is an environment-readiness signal only; it does not promote live evidence.

## Profiles

**Quick** is low-overhead editable plotting. **Standard** is the default SCI workflow with bounded template/style assistance. Both live profiles still require save/reopen/binding/export.

**Release** is fail-closed. Historical AA2195 strict evidence remains `5.8.9-p18` under the benchmark subtree and is not relabeled as v6 evidence. General v6 Release promotion requires new same-run evidence.

## Reference figures

A reference image may suggest panel structure, mark type, line/symbol use, page ratio, legend placement and other visual grammar, but a suggestion is not an executable contract. Only the allow-listed fields above can enter v6.0 `style`; unsupported suggestions such as exact legend placement remain in `style_audit.rejected` until a deterministic Origin mapping exists.

A reference image cannot inject scientific values, labels, fits, phase assignments, logos, watermarks or bitmap content into the editable project. There is no parallel screenshot-reproduction engine.

## Packaging boundary

The installable `originplot` package owns the ordinary runtime worker, elevation launcher, template discovery/retrieval code and v6 capability profiles. There is one canonical ordinary worker: `originplot.runtime.worker`.

The default shareable Skill ZIP intentionally excludes root `scripts/`, AA2195 benchmark material, generated/private scientific files and v5 contracts. Root scripts may remain as development/benchmark tooling, but ordinary installed execution must not depend on them.

## AA2195 benchmark

[`benchmarks/aa2195`](benchmarks/aa2195/) contains the retained specialized builders, configuration, candidates and historical evidence/protocol documents. `originplot/` is forbidden from importing it; offline package-boundary tests enforce that separation.

## Offline tests

```powershell
python -m compileall originplot scripts tests benchmarks
python -m pytest -q
python scripts/run_all_tests.py
python scripts/audit_dependencies.py
python -m pip install . --no-deps --target "$env:TEMP\originplot-installed"
python scripts/build_shareable_package_v6.py --skill-dir . --zip-out "$env:TEMP\originplot-v6.zip"
python scripts/validate_shareable_package_v6.py --path "$env:TEMP\originplot-v6.zip"
```

CI also runs an installed-package isolation smoke test from outside the repository tree. These commands test planning, contracts, package boundaries and fail-closed behavior. They do **not** prove licensed Origin execution.

## License and evidence

Repository-authored code and documentation are MIT licensed. Origin/OriginPro, Origin templates, paper figures and user-provided data retain their own licenses/rights.

Product version: **6.0.0**. Historical AA2195 benchmark evidence identity: **5.8.9-p18**.
