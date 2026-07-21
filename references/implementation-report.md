# Workflow Simplification Implementation Report

## 1. Modification Summary

Added profile-aware orchestration, bounded template policy, evidence levels, worker JSON protocol, centralized status semantics, a unified CLI, and an AA2195 benchmark configuration loader. Kept the retained p18 strict worker as the Release backend for the 5.9.0 package.

## 2. Architecture

`originplot.controller` performs non-Origin planning and dispatch. `originplot.core` owns profile and result models. `originplot.template` owns template policy. `originplot.runtime.protocol` defines the controller/worker boundary. `originplot.benchmarks.aa2195` owns specialized configuration.

## 3. Quick

Quick skips template discovery and release evidence while retaining save/detach/reopen/binding/export gates. Quick never becomes release eligible.

## 4. Standard

Standard is the new CLI default. It uses bounded auto template discovery, native fallback, basic visual QA, and visual-level evidence.

## 5. Release

Release rejects weakened overrides and delegates to the existing strict worker. The five-figure runner explicitly selects Release.

## 6. Privilege Boundary

Profile resolution, JSON parsing, template planning, metrics, manifests, and reports run in the controller. Only the Origin worker requires administrator rights in Quick/Standard. Existing Release privilege behavior is preserved.

## 7. Template Strategy

`skip`, `auto`, and `strict` are centralized. Auto bounds candidates and degrades retrieval failures to warnings. Strict fails closed.

## 8. Evidence Levels

`basic`, `visual`, and `full` determine artifact expectations. Disabled gates are `not_required`.

## 9. AA2195 Regression

Visual thresholds, template IDs, frozen routes, geometry versions, source hashes, Fig14 marker shapes, and the Fig16 segment count moved to benchmark configuration. Historical evidence files and identities were not modified.

## 10. Tests

Offline tests cover profile defaults and weakening prevention, template bounds/fallback, dry-run state, hard-gate normalization, CSV FigureSpec validation, a mocked generic-line save/reopen/binding/export cycle, Quick eligibility, and AA2195 configuration completeness. Live Origin E2E was not run during this refactor.

## 11. Known Limitations

Quick/Standard now include a focused native live builder for one Worksheet-backed line plot from CSV, TSV, or XLSX. Scatter, line-symbol, column, multi-layer, and schematic families remain unsupported by this worker and fail closed. The generic-line path has offline protocol tests but no new licensed-Origin E2E evidence from this refactor.

## 12. Next Step

Run a licensed Origin 2022 canary for generic-line, then add separately tested scatter, line-symbol, and column plugins without changing Release evidence semantics.
