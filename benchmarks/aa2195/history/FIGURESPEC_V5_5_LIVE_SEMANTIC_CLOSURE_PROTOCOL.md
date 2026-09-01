# OriginPlot Skill v5.5 - Live Semantic Closure Protocol

Version: `originplot.live_semantic_closure.v5.5`

The v5.5 closure rule is simple: a benchmark can pass only when its OPJU, exports, inspection, actual, semantic report, visual evidence, ledger, and manifest are all produced by the same current run.

## Provenance States

- `live_same_run`: eligible for pass if every gate succeeds.
- `inherited_diagnostic`: useful for review only; always pass-ineligible.

## Live Same-run Required Fields

Each artifact record should include `run_id`, `artifact_id`, `producer`, `created_at`, `path`, `sha256`, `origin_pid`, `python_pid`, `provenance`, and `eligible_for_pass`.

## Closure Gates

1. No seed fallback and no inherited artifacts.
2. OPJU exists and has SHA256 recorded.
3. Pre-save and post-reopen Origin exports exist and have SHA256 recorded.
4. A clean inspect worker reopened the OPJU and wrote inspection evidence.
5. Benchmark actual was materialized from inspection/QA/run artifacts.
6. Visual evidence includes page metrics and all recipe ROIs.
7. Evidence package validator passes.
8. Operation maturity is verified for all compiled operations.
9. Semantic benchmark has zero blocking failures.

## Diagnostic Runs

Any old OPJU/export/report reuse must be marked as `inherited_diagnostic`, `eligible_for_pass=false`, and `overall_status=incomplete`.
