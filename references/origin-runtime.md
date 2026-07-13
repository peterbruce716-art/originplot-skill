# Origin Runtime

## Preflight

Formal live execution requires Windows, Origin 2022 with a valid license, Python 3.10 with `originpro`, administrator Python, and a visible administrator-started Origin instance. The batch runner recognizes the supported process names `Origin64`, `Origin_64`, `Origin_32`, and `Origin`; require exactly one visible instance and preserve its PID regardless of installed bitness. Administrator privilege is one continuous envelope from the first action that can feed a live run through template retrieval/inspection, contract and candidate materialization, build, save, detach, reopen, readback, export, evidence packaging, and cleanup. Run `python scripts/assert_admin_preflight.py --json-out <run-root>/admin_preflight.json` before those actions. Never start unelevated and elevate only a later helper. Verify that the target OPJU is not open and that no stale lock blocks saving.

Do not run `origin_attach_smoke.py` as the default formal preflight. The smoke script is an explicit live-debug diagnostic that clears the active project. The default formal path is the candidate worker itself. Snapshot the visible Origin PID before `op.attach()`, verify the same PID and visible window immediately after attach, reject any new `-Embedding` process with `E123_ORIGIN_SESSION_IDENTITY_DRIFT`, and require the same PID for the reopen phase.

Keep the application, source worksheets, progress worksheet, and graph page visible throughout formal construction. Do not minimize Origin or hide/re-hide the graph page. Gray placeholders may appear transiently while Origin creates or populates layers; accept them only as intermediate UI state. Before pre-save export, activate the completed graph and require a nonblank export with no gray placeholder obstruction. Repeat the same check after reopen.

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

Run the demo-watermark gate on template-inspection exports, immediately after step 3's pre-save export and before saving the OPJU, and again after reopen. `E122_ORIGIN_DEMO_EXPORT_BLOCKED` stops the run at once. Mark the entire run invalid, release the attached session in `finally`, and preserve only a failure manifest and diagnostic watermark evidence. Do not reuse the OPJU, exports, readback, run ID, or output root.

Restart from the initial administrator preflight with a new run ID, a clean output root, administrator Python, and a visible administrator-started Origin instance. Rerun template inspection and reconstruction; do not resume from save/reopen/QA. Allow one complete elevated restart for this condition. If the elevated restart also reports `E122_ORIGIN_DEMO_EXPORT_BLOCKED`, stop with a license/environment failure because administrator privilege alone cannot repair an invalid or demo license.

## Origin 2022 units

- `page.width/page.height are dots`; calculate `page.width = width_inches * page.resx` and the equivalent height.
- Layer page-percent boxes use the verified Origin unit mode.
- Origin text `fsize is points`; do not apply page-dot scaling to text.
- Record `editable_view_evidence` before save and after reopen.
- Unit drift fails with `E540_PAGE_UNIT_SCALE_MISMATCH` or `E541_LAYER_UNIT_SCALE_MISMATCH`.

## Readback

Use `list(GLayer.plot_list())` as the primary enumeration route and compare it with LabTalk `layer -c`. Deep Origin 2022 binding readback may use `layer.plotn.pid`, `%A=xof(Ydataset)`, and the plot range exposed by `Plot.lt_range()`. For PID 202 marker plots, use persisted LabTalk `get dataset -k` and `get dataset -z` values for symbol shape and size; generic OriginPro plot properties alone are not sufficient. Always restore the string register after a LabTalk probe.

Each plot record includes type, visibility, data workbook, worksheet, X/Y columns, and Z for XYZ contour. Required object names are read after reopen. Axis visibility and titles are read from native axis properties such as `layer.axis.showAxes`.

The five-figure PowerShell runner must resolve Python 3.10 before any worker starts, run `assert_admin_preflight.py` into the clean output root, and use that exact executable for all five workers and `audit_five_figure_batch.py`.
