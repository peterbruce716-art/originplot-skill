# OriginPlot FigureSpec v5.4 Evidence-Linked Live Benchmark Protocol

Version: `originplot.figurespec.v5.4`

v5.4 binds every benchmark decision to the current live run evidence chain:

```text
FigureSpec
-> compiled IR
-> operation plan
-> live OPJU
-> pre-save Origin export
-> clean-session reopen
-> inspection
-> post-reopen Origin export
-> materialized benchmark_actual
-> visual evidence engine
-> semantic benchmark
-> deviation ledger
-> self-contained evidence package
```

## Hard Gates

- OPJU, exports, inspection, QA, comparison board, and manifest must belong to the same `run_id`.
- Cross-run reuse is allowed only when the artifact record contains `inherited_from_run`, `inheritance_reason`, and `eligible_for_pass=false`.
- A seed OPJU fallback can create file continuity only. It caps `overall_status` at `incomplete` and is always a blocking benchmark deviation.
- Production semantic benchmarks must not accept handwritten `actual`; actual values must be materialized from `inspection.json`, `qa_report.json`, `run_artifacts.json`, and the FigureSpec.
- Evidence packages must be self-contained and use relative package paths only.
- Visual comparison must preserve aspect ratio. Non-uniform resize is a geometry failure, not a normalization step.
- `visual_thresholds` and `critical_style` from the recipe participate in pass/fail decisions.

## Required Evidence Package

Each benchmark run directory or zip must contain:

```text
source_crop.png
result.opju
pre_save.png
post_reopen.png
figurespec.json
compiled_ir.json
operation_plan.json
run_artifacts.json
inspection.json
qa_report.json
benchmark_actual.json
semantic_benchmark_report.json
deviation_ledger.json
run_manifest.json
registered_export.png
alpha_overlay.png
absolute_diff.png
edge_overlay.png
comparison_board.png
```

JSON evidence must not contain absolute paths, unresolved parent traversal, or external run references unless the artifact is explicitly marked as inherited and ineligible for pass.

## Active Tools

- `scripts/benchmark_materializer.py`
- `scripts/visual_evidence_engine.py`
- `scripts/semantic_figure_benchmark.py`
- `scripts/validate_benchmark_evidence_package.py`
- `scripts/build_shareable_package.py`
- `scripts/validate_shareable_package_v5.py`
- `scripts/run_all_tests.py`
