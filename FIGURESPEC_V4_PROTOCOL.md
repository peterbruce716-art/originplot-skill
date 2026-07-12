# OriginPlot FigureSpec v4 Legacy Protocol

> Legacy input only. This document is retained for migration and historical
> schema interpretation; it is not a supported p14 execution route. Current
> execution uses the v5 schemas and `scripts/origin_candidate_worker.py`.

v4 separates authoring facts, compiled coordinates, executable operations, and run evidence.

## Schemas

- `originplot.figurespec.v4`: source facts, user intent, benchmark crops, raw measurements, and contracts.
- `originplot.compiled_ir.v4`: deterministic transforms from source coordinates to Origin coordinates.
- `originplot.operation_plan.v4`: ordered executable operations with explicit `adapter_route`.
- `originplot.run_manifest.v4`: preflight, build, round-trip, structure, serialization, visual, patch, and rollback statuses.

## Required Runtime Gates

1. Capability preflight is fail-closed before Origin starts.
2. `FigureSpec`, `Compiled IR`, and `Operation Plan` are immutable separate artifacts.
3. Build and inspect must be separable workers; dry-run may validate contracts without Origin.
4. Pre-save export, post-reopen export, and source benchmark comparisons are distinct evidence.
5. Correction plans must be bounded executable patches with rollback-on-no-improvement.

## Status Fields

`preflight_status`, `build_status`, `round_trip_status`, `structure_status`,
`serialization_status`, `visual_status`, and `overall_status` must be present in every v4 run manifest.

## Error Codes

Use the stable v4 error-code names recorded by the legacy artifacts, including
`E110_CAPABILITY_MISSING`, `E210_OPERATION_UNSUPPORTED`,
`E410_SERIALIZATION_DRIFT`, `E420_VISUAL_MISMATCH`, and
`E510_NO_IMPROVEMENT`. Do not invoke the retained v4 runtime scripts as the
current p14 execution path; migrate the artifacts to the v5 contracts first.
