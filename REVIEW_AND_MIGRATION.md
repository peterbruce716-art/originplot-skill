# Review and migration notes

## Main diagnosis

The original package is strong as a policy document but weak as an executable reproduction system. It has no FigureSpec executor, no compiled build plan, no clean-session structural inspector, and no independent verification that the OPJU contains the expected plot bindings and named editable objects. Existing QA is mainly file existence, reopen status, and resized pixel error.

## Highest-impact changes

1. Replace global MCP-first routing with capability-driven routing per Origin version and operation.
2. Treat official complete projects as construction evidence, then extract a minimal canonical seed instead of cloning the whole project into production.
3. Upgrade FigureSpec to v2 with explicit Origin object type, attachment mode, coordinate units, numeric coordinates, stable object names, z-order, and structural contracts.
4. Compile the spec into a deterministic operation plan. Rescale once, freeze axes, then add annotations; never rescale afterward.
5. Reopen the saved OPJU in a clean session and read back workbook, graph, layer, plot, axis, object, attachment, and data-binding structure.
6. Replace simple resized MAE with full-frame geometry, content-normalized geometry, tolerant edge overlap, and color checks.
7. Add a rendering calibration project/profile for every Origin version, adapter, DPI/scaling, font set, and export backend.

## Integration boundary

The added scripts validate and compile contracts but do not implement a live Origin inspector because that must be verified against the installed Origin version and adapter. Implement the inspector inside the proven Origin execution environment and emit the JSON shape expected by `validate_opju_inspection.py`.
