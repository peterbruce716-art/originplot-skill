# Origin Runtime

## Preflight

Formal live execution requires Windows, Origin 2022 with a valid license, Python 3.10 with `originpro`, administrator Python, and a visible administrator-started Origin instance. Administrator privilege is continuous from live preflight through template inspection, build, save, detach, reopen, readback, export, and cleanup. Never combine an elevated Origin instance with a non-elevated helper. Verify that the target OPJU is not open and that no stale lock blocks saving.

## Session lifecycle

Formal AA2195 builds attach to the authorized visible instance. Build and reopen are separate phases. Session cleanup belongs in `finally` or the session context manager:

- attached session: `op.detach()`;
- worker-owned diagnostic hidden session: `op.exit()`.

Hidden sessions are diagnostic-only unless an explicit future contract promotes them. A constructor hang or modal prompt is a failed bounded worker route, not evidence.

## Save/reopen closure

1. Start from a blank project.
2. Build native editable pages and direct Worksheet bindings.
3. Export pre-save evidence and save OPJU.
4. Release the Origin session.
5. Attach in a new phase and open the same OPJU as editable, never read-only.
6. Inspect page/layer/plot/object/data bindings and actual Worksheet shapes.
7. Run `win -z0` to fit the editable page view; this does not change page geometry.
8. Save the fitted edit view and export post-reopen evidence.
9. Release the session.

## Origin 2022 units

- `page.width/page.height are dots`; calculate `page.width = width_inches * page.resx` and the equivalent height.
- Layer page-percent boxes use the verified Origin unit mode.
- Origin text `fsize is points`; do not apply page-dot scaling to text.
- Record `editable_view_evidence` before save and after reopen.
- Unit drift fails with `E540_PAGE_UNIT_SCALE_MISMATCH` or `E541_LAYER_UNIT_SCALE_MISMATCH`.

## Readback

Use `list(GLayer.plot_list())` as the primary enumeration route and compare it with LabTalk `layer -c`. Deep Origin 2022 binding readback may use `layer.plotn.pid`, `%A=xof(Ydataset)`, and the plot range exposed by `Plot.lt_range()`. Always restore the string register after a LabTalk probe.

Each plot record includes type, visibility, data workbook, worksheet, X/Y columns, and Z for XYZ contour. Required object names are read after reopen. Axis visibility and titles are read from native axis properties such as `layer.axis.showAxes`.
