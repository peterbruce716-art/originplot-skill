# OriginPlot v6

**AI-assisted, auditable, editable scientific plotting in Origin/OriginPro.**

OriginPlot v6 is a compact general-purpose plotting skill: give it a CSV/TXT/XLS/XLSX table, confirm the scientific column mapping, and it compiles a deterministic FigureSpec/OperationPlan before an administrator-only Origin worker creates and verifies the editable project.

The project deliberately separates **scientific meaning**, **plot compilation**, and **Origin automation**. It does not treat a Python preview as an Origin result and it does not silently invent analysis.

## What changed in v6

The old AA2195-centered product architecture has been replaced by a general core:

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
.\.venv\Scripts\python -m pip install -r requirements-core.txt -r requirements-dev.txt
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

The runtime still checks the authorized visible Origin process identity and rejects session drift/new Embedding processes. The v6 refactor changes architecture, not this safety/reliability policy.

## Ten plot primitives

v6.0 exposes exactly ten public primitives:

| Family | Primitives |
|---|---|
| XY | `line`, `scatter`, `line_scatter`, `errorbar` |
| Categorical | `bar`, `grouped_bar`, `stacked_bar` |
| Matrix/XYZ | `heatmap`, `contour` |
| Composition | `multi_panel` |

Internally these are four compiler families, not ten duplicated plotting engines. New scientific domains should normally add semantic/style presets that compile to these primitives.

### Compile support vs live evidence

The ten names above are the **v6 planning/compile surface**. They do not mean that all ten primitives have blanket live-Origin evidence.

`originplot.cmd doctor` reports the distinction explicitly through:

```text
compile_primitives
live_candidate_primitives
live_evidence_primitives
primitive_maturity
```

At v6.0, no general primitive is promoted as repository-wide v6 live evidence merely because offline CI passes. A successful live run still has to earn its own same-run save/reopen/binding/export verification.

`heatmap` is stricter: FigureSpec and OperationPlan compilation are supported, but live execution is deliberately blocked with `E524_HEATMAP_LIVE_UNVERIFIED` before the elevated Origin worker starts. Promotion requires a regular-grid/matrix adapter plus fresh licensed-Origin evidence. The other live candidates remain subject to the same-run verification gates and are not automatically promoted by capability metadata.

## Conservative data understanding

Every source column is assigned one role:

```text
x / y / x_error / y_error / z / group / category / label / support / retain / uncertain
```

A numeric column with unclear meaning remains `uncertain`. OriginPlot will not quietly turn it into another curve. Explicit user mappings resolve the selected scientific roles; unrelated columns are retained.

OriginPlot does **not** silently smooth, normalize, fit, remove outliers, calculate error bars, identify peaks/phases, or compute scientific results.

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
  "style": {"theme": "publication"},
  "layout": {"page": {"width_cm": 18, "height_cm": 12}},
  "verification": {"profile": "standard"}
}
```

The source SHA-256 is frozen with the plan. If the source changes, the confirmed specification is stale instead of silently being reused.

## Builder architecture

Builders never import Origin. Their entire job is:

```text
FigureSpec -> originplot.operation_plan.v1
```

The OperationPlan contains declarative actions for workbooks, graph/layers, native plot bindings, axes, legends, page geometry and export intent. Only [`originplot/adapters/originpro.py`](originplot/adapters/originpro.py) translates those operations into Origin calls.

This makes semantic understanding and plot compilation testable on machines without Origin.

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
9. nonblank export check;
10. Demo-watermark rejection.

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

`ready_for_live_worker` is an environment-readiness signal only. Primitive maturity and same-run evidence are separate. Capability metadata never overrides administrator requirements or the verification gates.

## Profiles

**Quick** is low-overhead editable plotting. **Standard** is the default SCI workflow with bounded template/style assistance. Both live profiles still require save/reopen/binding/export.

**Release** is fail-closed. The historical AA2195 strict evidence remains `5.8.9-p18` under the benchmark subtree and is not relabeled as v6 evidence. General v6 Release promotion requires new same-run evidence before it can become eligible.

## Reference figures

A reference image may suggest layout and style grammar, but it cannot inject its scientific values, labels, fits, phase assignments, logos, watermarks or bitmap into the editable project.

Style precedence is:

```text
explicit user choice > confirmed reference suggestion > preset > OriginPlot default
```

Reference choices must become normal FigureSpec `style`/`layout` fields; there is no parallel screenshot-reproduction engine.

## AA2195 benchmark

[`benchmarks/aa2195`](benchmarks/aa2195/) contains the retained specialized builders, candidate/configuration material and historical evidence/protocol documents. `originplot/` is forbidden from importing it; an offline package-boundary test enforces that separation.

## Offline tests

```powershell
python -m compileall originplot scripts tests
python -m pytest -q
python scripts/run_all_tests.py
python scripts/audit_dependencies.py
python scripts/build_shareable_package_v6.py --skill-dir . --zip-out "$env:TEMP\originplot-v6.zip"
python scripts/validate_shareable_package_v6.py --path "$env:TEMP\originplot-v6.zip"
```

These commands test planning/contracts/package boundaries. They do **not** prove live Origin execution. A live claim still requires the licensed administrator-Origin lifecycle on Windows.

## License and evidence

Repository-authored code and documentation are MIT licensed. Origin/OriginPro, Origin templates, paper figures and user-provided data retain their own licenses/rights.

Product version: **6.0.0**. Historical AA2195 benchmark evidence identity: **5.8.9-p18**.
