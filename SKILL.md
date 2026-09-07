---
name: originplot
description: "AI workflow for auditable Origin/OriginPro scientific plotting. Inspect scientific tables, resolve semantic roles, create FigureSpec, compile OperationPlan, and execute verified editable Origin workflows when supported."
---

# OriginPlot Skill v6.1.3

Convert scientific tables into auditable, editable Origin graphs. Keep scientific meaning, specification, execution, and evidence separate.

## Workflow

1. Inspect authorized source data and resolve column semantics; do not guess ambiguous meaning.
2. Create and validate FigureSpec v6, then compile and validate OperationPlan.
3. Check capability maturity before execution. Planning support is not native support or verified evidence.
4. Use an authorized, visible Origin session; verify native save/reopen, worksheet bindings, and exports.

Completion: `semantic_valid -> spec_valid -> plan_valid -> adapter_supported -> verified_result`. Diagnose failures in that order. Preview, dry-run, and screenshots alone do not prove editability.

## Essential Rules

- Source data is immutable. Do not smooth, normalize, fit, remove outliers, or derive quantities without instruction. Unresolved semantics stay `uncertain`.
- Builders compile plans; only adapters call Origin. Unknown operations fail closed. Prefer existing primitives/presets over new engines.
- Apply only executable styles and report unsupported fields. Follow the quickstart's per-series mapping and style rules before planning.
- Keep Origin visible and non-minimized. Detach attached sessions in `finally`; do not close the user's application. Never weaken validation or hide failed evidence.
- Paper reproduction is template-first: local templates, then relevant official projects when needed, then justified native reconstruction. Inspect editable structure before adopting downloaded projects.
- Historical metadata and standalone `verify` are not fresh native verification. Read the evidence limits before making completion claims.

## Read as Needed

| Task | Required reference |
|---|---|
| First use, planning, reproduction, live execution, or evidence review | [Agent Quickstart](docs/AGENT_QUICKSTART.md) |
| Selecting a plot type | [Capability Matrix](docs/CAPABILITY_MATRIX.md); `heatmap` and `multi_panel` stay blocked until native support is proven |
| Extending builders/adapters | [Development Guide](docs/DEVELOPMENT_GUIDE_v6.1.md) |
| AA2195 five-figure benchmark | Full repository only: `benchmarks/aa2195/docs/benchmark.md` |

The compact runtime includes the three linked guides, not benchmark scripts/builders. Load benchmark materials only for that task.

## Commands

Use Python 3.10. From the installed skill directory:

```powershell
originplot.cmd doctor --origin-version 2022
originplot.cmd inspect data.xlsx
originplot.cmd plan data.xlsx --plot-type line --x X --y Y
originplot.cmd render figure.json --dry-run
originplot.cmd render figure.json
originplot.cmd draw data.xlsx --plot-type line --x X --y Y
originplot.cmd verify output
```

`quick` is for routine editable plotting, `standard` for bounded scientific assistance, and `release` for strict evidence-required work. A profile never grants unsupported capability.

## Five-Figure Benchmark

Use `requirements-benchmark.txt` and `scripts/run_five_figure_live_batch.ps1` from the full repository. Read the quickstart and benchmark contract before running.

- Use a new output directory and explicitly select `fresh_extract`, `validated_reuse`, or `validated_crop_reextract`; describe reuse honestly.
- For complete Fig3 axis titles, request `-Fig3CanvasMode full` with `fresh_extract`. The compatibility-default `legacy` crop omits bottom titles.
- `-ExportSupersampleByFigure @{fig3=3}` is optional and per-figure. Valid factors are integers 1-4; compare against the same canvas and retain metric tradeoffs.
- Require the strict source/structure/visual/window audit and native deliverables. AA2195 success does not certify generic v6 capabilities.
