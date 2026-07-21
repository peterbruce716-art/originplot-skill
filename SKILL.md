---
name: originplot
description: "Plan, build, inspect, debug, or reproduce editable Origin/OriginPro OPJU figures with native Worksheet-bound plots, save/reopen verification, Origin exports, and profile-scaled evidence. Use for Excel/CSV scientific plots, publication figure reconstruction, Origin 2022 automation, official template matching, editable OPJU delivery, and AA2195 Fig3/Fig12/Fig14/Fig15/Fig16 release benchmarks."
---

# OriginPlot Skill v5.9.0

OriginPlot is a Verified Origin Runtime for an editable Origin project, organized into three profiles. Default to `standard`. Keep the `5.9.0` package identity while retaining the validated `5.8.9-p18` functional contract and evidence identity.

## Capability Boundary

- Build Origin workbooks, native plots, layers, axes, legends, and editable annotations.
- Preserve real Plot-to-Worksheet bindings and validate them after reopening the OPJU.
- Support registered builders and explicit FigureSpecs; do not claim universal image-to-OPJU reproduction.
- Do not use a reference image, raster background, or screenshot as the editable result.
- Do not treat a Python, R, or Matplotlib redraw as a live Origin deliverable.
- Route an open-code redraw to the optional `scientific-figure-reproduction` companion; do not imply it is bundled.
- Do not read unrelated local documents or private data.

## Identify Inputs

Before execution, identify the requested figure class, input data or authorized reference, builder or FigureSpec, output directory, requested profile, and whether live Origin execution is authorized. For data files, record the exact sheet and X/Y/error columns. For image matching, record source provenance and the intended fidelity claim.

Use Python 3.10 with `originpro` for Origin 2022. Run controller-only work without administrator rights. Require an administrator process only for the worker that imports `originpro` or `OriginExt`, attaches to Origin, builds, saves, reopens, reads back, or exports.

## Select A Profile

- `quick`: routine supported plots and style iteration; the built-in generic worker currently covers one line plot; no formal visual claim.
- `standard`: default for SCI figures and reference-guided reconstruction; bounded template discovery and basic visual QA.
- `release`: AA2195 benchmarks, regression, package acceptance, or any claim of full live validation.

Never weaken `release` with lighter overrides. A user request to reproduce again, re-digitize, or avoid old data requires the release `fresh_extract` route and a new or empty output root.

## Permanent Hard Rules

For every live profile:

1. Use native Origin plots or verified editable Origin objects.
2. Bind every data plot to a Worksheet.
3. Save the OPJU, release the session, reopen the OPJU, and inspect the reopened project.
4. Verify expected pages, layers, plots, Worksheets, and bindings.
5. Export the final image from reopened Origin.
6. Fail on blank export, Demo watermark, reopen failure, missing plot, or lost binding.
7. Keep dry-run, live structure, visual, and release states distinct.
8. Release attached sessions with `op.detach()` in `finally`; release worker-owned hidden diagnostics with `op.exit()`.
9. Do not use historical artifacts as same-run live evidence.

Read [references/origin-runtime.md](references/origin-runtime.md) before live work.

For editable viewing, apply `win -z0` after build and reopen, record `editable_view_evidence`, and state that fitting the window does not change page geometry. Use bounded `--phase-timeout-seconds` controls where supported.

## Release Invariants

Keep administrator privilege for the entire live lifecycle in Release; every helper process that touches Origin must remain elevated. Do not run `origin_attach_smoke.py` as the default formal preflight. After each attach, fail with `E123_ORIGIN_SESSION_IDENTITY_DRIFT` if the administrator-started visible Origin PID changes or a new embedding process appears. Missing authorization fails with `E121_ATTACH_POLICY_VIOLATION`.

Strict template discovery checks these official entrances plus local catalogs:

- `https://www.originlab.com/www/products/GraphGallery.aspx?s=0&sort=Newest`
- `https://docs.originlab.com/zh/`
- `https://www.originlab.com/videos/index.aspx?CID=11`
- `https://docs.originlab.com/quick-help/graphing/zh/`

For column layers, declare `side_by_side`, `cumulative_stack`, or `nested_overlap` per layer. Nested columns share the zero baseline; cumulative stacks use successive baselines. For source-visible proportions, declare `morphology_ratio_contracts` with `reference_item` and `expected_ratios`, then audit the post-reopen final export. Missing declarations, missing measurements, and out-of-tolerance ratios fail the release visual-structure gate.

## Quick Workflow

Read [references/profiles/quick.md](references/profiles/quick.md) and the runtime rules. Use `template_policy=skip`, `evidence_level=basic`, `reopen_check=basic`, and `visual_qa=off` unless the user requests a stronger profile.

Run:

```powershell
python scripts/originplot.py --figure-spec figure_spec.json --builder generic_line --profile quick --live --output-dir outputs\quick
```

Do not run official template discovery, full lineage, morphology contracts, AA2195 gates, five-figure audit, or release eligibility.

## Standard Workflow

Read [references/profiles/standard.md](references/profiles/standard.md), [references/template-discovery.md](references/template-discovery.md), [references/visual-qa.md](references/visual-qa.md), and runtime rules.

Use `template_policy=auto`, `evidence_level=visual`, `reopen_check=basic`, `visual_qa=basic`, at most three template candidates, and at most one rebuild by default. Template retrieval failure becomes a warning and native reconstruction fallback, not a blocker.

Run:

```powershell
python scripts/originplot.py --figure-spec figure_spec.json --builder generic_line --profile standard --live --output-dir outputs\standard
```

## Release Workflow

Read [references/profiles/release.md](references/profiles/release.md), [references/evidence-contract.md](references/evidence-contract.md), runtime, template, visual, and troubleshooting references. Read [references/aa2195-benchmark.md](references/aa2195-benchmark.md) only for AA2195 work.

Use `template_policy=strict`, `evidence_level=full`, `reopen_check=strict`, and `visual_qa=benchmark`. Keep the complete administrator privilege envelope, source lineage, hashes, pre-save and post-reopen exports, full readback, evidence directory, and fail-closed release gates.

Run a single strict route:

```powershell
python scripts/originplot.py --profile release --figure fig15 --candidate candidate.json --live --require-live-success --output-dir outputs\release
```

Run the AA2195 five-figure batch only through `scripts/run_five_figure_live_batch.ps1`; it maps to `release` automatically.

For AA2195 reruns that ask to reproduce again, re-digitize, or avoid old data, use `-SourceDataPolicy fresh_extract`, pass the authorized `-SourcePdf`, and write to a new or empty `-OutputRoot`. Resolve Python with `scripts/resolve_python310.ps1`, run `scripts/assert_admin_preflight.py` under the same elevated envelope, and keep exactly one visible administrator-started Origin instance. Candidate dry-runs are useful for source/template contract checks before live work, but they remain `planned_not_executed` and are never OPJU or release evidence.

## Outputs And Status

- `basic`: `candidate.opju`, `candidate_export.png`, `candidate_summary.json`.
- `visual`: basic outputs plus readback, visual metrics, and manifest.
- `full`: visual outputs plus pre-save export, evidence directory, hashes, provenance, route/source identities, template evidence, and release status.

Use `planned_not_executed`, `completed`, `live_structure_pass`, `live_visual_pass`, `incomplete`, or `failed` according to the profile contract. Quick completion never sets `pass_eligible=true`. A disabled gate is `not_required`, never `pass`.

## Failure Handling

- Stop before Origin attach on invalid schema, unauthorized source, or strict release preflight failure.
- Preserve stable error codes and report which gate failed.
- In Quick/Standard, warn and fall back after bounded template search failure.
- In Release, fail closed when strict template, lineage, hash, structure, visual, or evidence requirements are missing.
- On Demo watermark, invalidate the run and restart the full release lifecycle only after fixing the license/environment.
- Read [references/troubleshooting.md](references/troubleshooting.md) for attach, lock, serialization, and export failures.

## Claims

Report exactly what ran. Dry-run is planning only. Quick is editable completion, not release validation. Standard visual pass is not release eligibility. AA2195 evidence applies only to its named routes and recorded identities. Never claim raw-data recovery, cross-machine pixel identity, or automatic high-fidelity reproduction of arbitrary figures.
