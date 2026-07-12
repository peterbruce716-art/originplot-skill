---
name: originplot
description: "Use for editable Origin/OriginPro OPJU construction, save/reopen inspection, native plot and Worksheet binding validation, Origin-rendered visual QA, and authorized Origin 2022 automation."
---

# OriginPlot Skill v5.8.9-p14

OriginPlot is a Verified Origin Runtime for producing and validating an editable Origin project. It includes specialized AA2195 Fig3/Fig12/Fig14/Fig15/Fig16 builders and an extensible registry; it does not automatically reproduce arbitrary figures. Each named AA2195 route has administrator Origin 2022 save/reopen evidence within its declared benchmark scope. This is not a claim of arbitrary-input completion, cross-machine pixel identity, or raw-data recovery. Fig12 keeps native XYZ Worksheet bindings, applies a constrained TR region-anchor remap, and adds editable source-vectorized type-34 regions plus editable page-coordinate axis titles. Origin 2022 supports these SVG path objects through plain `draw -paths objName SVGPath`; the tested `-s/-d` variants did not create objects.

## Use this skill when

- The required deliverable is an editable `.opju` with Origin workbooks, native plots, layers, axes, legends, or annotations.
- The task needs Origin 2022 automation, authorized attach, OPJU save/reopen inspection, or Origin-rendered evidence.
- The user asks to reproduce, inspect, debug, package, or regression-test an Origin figure.

## Do not use it when

- The deliverable is only Python, R, Matplotlib, or another open-code redraw.
- The user wants image editing without an editable Origin project.
- The environment cannot support Origin and the user requires a live E2E claim now.

`scientific-figure-reproduction` is an optional companion skill for open-code redraws. It is not bundled. If it is unavailable, explain the scope boundary instead of claiming an automatic handoff.

## Required inputs

Before execution, identify:

1. Figure class: native chart, semantic schematic, or unsupported.
2. Source/reference image and its provenance, when visual comparison is requested.
3. FigureSpec or an existing registered AA2195 figure ID.
4. Candidate parameters and output directory.
5. Required acceptance level: offline plan, live structure, or live visual pass.
6. Whether the user has authorized attach to an administrator-started visible Origin instance.

Do not read unrelated local documents or private data. Never embed the source image as the editable base graph.

## Task classification

- `offline_contract`: validate schemas, registry resolution, candidates, dependencies, tests, or packaging without Origin.
- `live_build`: construct, save, release, reopen, inspect, and export in Origin.
- `live_debug`: diagnose attach, modal, serialization, readback, or export failures.
- `benchmark`: run live build plus source comparison and benchmark-specific gates.
- `new_builder`: define a new builder and tests; do not imply universal plot support.

For AA2195 Fig3/Fig12/Fig14/Fig15/Fig16, read [references/aa2195-benchmark.md](references/aa2195-benchmark.md). For other tasks, do not load benchmark-specific rules unless they are relevant.

## Preflight

For offline work:

- Validate JSON and required files.
- Resolve the builder through `builders.registry`; reject unknown or duplicate IDs.
- Keep source, candidate, and output paths portable where possible.

For formal live work:

- Require Windows, Origin 2022 with a valid license, Python 3.10, and `originpro`.
- Require administrator Python and a visible administrator-started Origin process before the live workflow begins.
- Keep administrator privilege for the entire live lifecycle: preflight, template-project open/inspection, build, save, release, reopen, readback, export, and cleanup. Do not mix elevated and non-elevated Origin/Python phases.
- Confirm the destination OPJU is not open and no stale lock blocks it.
- Use bounded workers and expose runtime timeout controls such as `--phase-timeout-seconds` where supported.
- Do not run `origin_attach_smoke.py` as the default formal preflight. It is a destructive live-debug diagnostic because it calls `op.new(asksave=False)`; the normal formal route starts directly with `origin_candidate_worker.py --live`.
- After every `op.attach()`, verify that the same administrator-started visible Origin PID remains visible and that no new `-Embedding` process appeared. Fail with `E123_ORIGIN_SESSION_IDENTITY_DRIFT` before construction on any identity drift.

For every paper-like reproduction, template discovery is the first route decision, before builder selection or construction:

1. Search the official Graph Gallery index: `https://www.originlab.com/www/products/GraphGallery.aspx?s=0&sort=Newest`.
2. Check the Chinese product documentation: `https://docs.originlab.com/zh/`.
3. Check the official graphing videos: `https://www.originlab.com/videos/index.aspx?CID=11`.
4. Check the Chinese graphing Quick Help: `https://docs.originlab.com/quick-help/graphing/zh/`.
5. Search the local official-template catalog and installed Origin templates.
6. Prefer the workspace catalog `OriginLab官方相似模板_下载器与匹配清单` when present.
7. Record every candidate URL/file, hash, compatibility, open/reopen result, workbook rows, plot types, direct bindings, and selection/rejection reason.
8. Open and inspect the downloaded project in compatible Origin before calling it a reusable template. A screenshot, `.otp`, filename, or Gallery citation alone is not sufficient.
9. If no candidate is reusable, record the gap and use a native reconstruction route; never imply object transplantation.

If preflight fails, return a stable error and do not create evidence that looks live.
Missing or unauthorized attach uses `E121_ATTACH_POLICY_VIOLATION`; a non-administrator live process uses `E120_ENVIRONMENT_MISMATCH`.
Shareable candidates that still contain `AUTHORIZED_LOCAL_SOURCE_REQUIRED` fail before Origin attach with `E124_AUTHORIZED_SOURCE_REQUIRED`; replace it with an authorized readable local source path.

## FigureSpec and route gate

Every execution route must declare its builder, figure class, editable object family, source provenance, expected page/layer/plot/object inventory, direct Worksheet bindings, row budget, and acceptance mode.

The route gate fails before construction if the required official/local template search record is absent for a paper-like figure.

For final graphs:

- Use Origin-native plots or verified editable Origin objects.
- Bind every data-bearing or geometry-bearing Plot directly from a Worksheet. Treat geometry-only GraphObjects separately: require an editable native object type plus an explicit post-reopen type and geometry contract. Source-derived type-34 paths may use a unique transient SVG import, but the SVG is never retained or treated as evidence.
- After reopen, resolve workbook, worksheet, X, Y, and Z for XYZ plots from live Origin readback.
- Keep the global direct-plot Worksheet total at or below 5,000 rows per figure.
- Reject source-image pages, pixel traces, raster backgrounds, and copied preview pages.
- Treat official templates as references unless donor opening, object readback, and transplantation are evidenced.

Read [references/current-contract.md](references/current-contract.md) for result fields, provenance, fail-closed rules, and required outputs.

## Origin session lifecycle

Formal AA2195 execution uses two authorized attach phases:

```text
blank project -> build -> pre-save export -> save OPJU -> detach
new attach phase -> editable reopen -> inspect -> fit view -> save -> post-reopen export -> detach
```

Always release in `finally` or the session context manager. Attached sessions use `op.detach()`; a worker-owned diagnostic hidden session uses `op.exit()`. Never close the user's Origin application when detaching is sufficient.

Both phases and every helper process that touches Origin must remain elevated. A non-administrator helper cannot inherit or continue a formal live run; fail with `E120_ENVIRONMENT_MISMATCH` before importing `originpro` or `OriginExt`.

The build and reopen phases must use the same verified visible Origin PID. Check the pre-save export for demo cyan markings before saving the OPJU; fail immediately with `E122_ORIGIN_DEMO_EXPORT_BLOCKED` instead of continuing the batch.

Read [references/origin-runtime.md](references/origin-runtime.md) before changing Origin attachment, page/layer units, text size, readback, save, reopen, or export logic.

## Editable closure

A live candidate is not verified until the saved OPJU is released, reopened in a new phase, read back, exported again, and released. The reopened graph must retain expected pages, layers, direct plots, axes, objects, workbook shapes, and bindings.

Run `win -z0` for the delivered editable view and record `editable_view_evidence`; this does not change page geometry. Origin page dimensions are dot-based and text size is point-based. Do not mix these units.

If inspection reports zero plots where plots are expected, compare `plot_list()` with `layer -c` and fail closed until the discrepancy is resolved.

## Provenance and status

Only `live_same_run` evidence can pass. Seed OPJUs, copied files, prior exports, and cross-run reports are `inherited_diagnostic` and not pass-eligible.

Keep these fields independent:

- `command_success`
- `structure_pass`
- `visual_pass`
- `live_origin_verified`
- `pass_eligible`
- `overall_status`

Dry-run success means planning succeeded. It must report `planned_not_executed`, `live_origin_verified=false`, `structure_pass=false`, `visual_pass=false`, and `pass_eligible=false`.

## CLI behavior

- `--dry-run`: validate and materialize a plan; exit 0 on valid input.
- `--live`: attempt licensed Origin execution.
- `--require-live-success`: exit nonzero unless the live result is pass-eligible.
- `--dry-run` and `--live` are mutually exclusive.
- No mode flag retains the legacy dry-run default with a clear notice.
- Legacy `--figure fig12|fig15|fig16` remains supported.
- New routes use `--builder <id>` and optional `--figure-spec <path>`.

Argument errors exit 2. Worker/build errors exit nonzero. A valid but visually unpromoted live diagnostic may exit 0 only when `--require-live-success` is absent, while its manifest remains incomplete.

## Visual QA

Run structure and nonblank gates before scalar visual metrics. Compare source and post-reopen Origin export, record registration and ROI evidence, and use a bounded clean-rebuild loop. Identical consecutive signatures stop with `E510_NO_IMPROVEMENT`.

For the named AA2195 set, run `scripts/audit_five_figure_batch.py` on the completed batch directory after all five routes finish. The audit is a release gate: it requires exactly Fig3/Fig12/Fig14/Fig15/Fig16, one stable visible Origin PID, `live_same_run` provenance, matching skill versions, and `structure_pass`, `visual_pass`, and `overall_release_pass` for every figure. A scalar score from one figure or an inherited manifest cannot promote the five-figure set.

Use `scripts/run_five_figure_live_batch.ps1 -OutputRoot <path>` from an elevated PowerShell process to build the five named routes in one visible Origin session. The batch runner records per-figure output and PID stability, continues through visual non-promotion so the full gap is observable, and invokes the batch audit at the end.

Fig3's four-panel route keeps the top PSC/UC/TR legend editable: each temperature swatch is a native Worksheet-backed line segment, with NaN gaps encoding dotted and dash-dot modes so the pattern survives save/reopen. Fig3 labels and axes explicitly use Times New Roman and the temperature labels retain their source color and bold weight; these typography and legend details are part of the live visual check rather than raster decoration.

Report `gate_margins` and `near_threshold_metrics`. A promoted metric within 0.001 of its threshold remains a pass in the verified environment but must be disclosed as near-threshold; do not generalize it to another Origin build, export profile, or machine without a new live run.

Never claim improvement without same-run metrics against the declared comparator. Read [references/visual-qa.md](references/visual-qa.md) before tuning visual parameters or changing promotion thresholds.

## Outputs

A live promoted candidate requires:

- editable OPJU;
- pre-save and post-reopen Origin exports;
- post-reopen object and binding readback;
- visual metrics and deviation records;
- candidate manifest with consistent run identity and hashes;
- self-contained standard evidence directory.

Shareable skill packages exclude source images, OPJUs, and rendered exports. Packaged AA2195 candidates contain an authorized-local-source placeholder, and `references/aa2195-release-evidence.json` provides only a sanitized hash-and-metric index.

Offline reports must say `live_origin_e2e = not_run_environment_unavailable` or another accurate not-run reason, never passed.

## Troubleshooting

Use [references/troubleshooting.md](references/troubleshooting.md) for attach failures, locked OPJUs, blank exports, plot readback disagreement, modal prompts, and no-improvement stops. Do not change multiple unrelated mechanisms after repeated failures.

## Legacy and maintenance

V2/V3/V4 artifacts are legacy inputs and require explicit migration to current V5 contracts. Read [references/legacy-and-migration.md](references/legacy-and-migration.md); do not present legacy runtime scripts as the p14 execution path.

Version history and named-run records live in [references/changelog.md](references/changelog.md). Do not append project run diaries to this file.

When updating the skill:

1. Run the baseline first.
2. Make the smallest coherent change.
3. Add behavior tests for code and narrow wording tests only for false public claims.
4. Run compile, pytest, packaged tests, dependency audit, public demo dry-run, package build, and package validation.
5. Run live Origin only in an authorized environment and report it separately.

## External wording

Say that the repository provides a verified Origin framework plus specialized AA2195 builders. State that the five named routes passed their declared gates in the recorded Origin 2022 reference runs, while Fig12 has a near-threshold edge score and Fig15/Fig16 remain frozen-regression routes. Do not call the routes universally complete, claim cross-machine pixel identity, say that dry-run reproduced a figure, or imply that a new figure is automatically supported.
