# Benchmark Improvements and Evidence Boundaries

Baseline: peterbruce716-art/originplot-skill, main commit 74c1aaab1b1a8fb4f1eff8e4a4b64a729fd71688.
Product version remains 6.1.3; AA2195 evidence contract remains 5.8.9-p18.
These changes retain the existing product and evidence-contract versions; they do not declare a new tagged release. The measurements below are maintainer-reported local Origin runs, not hosted CI or bundled scientific evidence.

## Function-Preserving Simplification

- Shorten SKILL.md into a routing entrypoint; keep operational details in the existing packaged Agent Quickstart. Preserve template-first research, scientific semantics, visible authorized attachment, lifecycle ownership, and evidence limitations.
- Share CLI planning argument declarations, FigureSpec argument assembly, and render/draw exit decisions. Retain command-specific execution flags, help ordering, write ordering, error payloads, and the distinct verify predicate.
- Require all three operational guides in the compact-package validator. Regression tests inspect transitive inline links and fragments in the actual built package; reference-style definitions fail explicitly instead of bypassing the check. This is a guide-format regression check, not a general Markdown parser.
- The simplification step left Origin workers, adapters, builders, capability profiles, source policies, scientific data, optional canvas/export modes, and acceptance thresholds unchanged. The separate benchmark fixes below are scoped explicitly. Runtime speed is not a claimed improvement.

## Changes

- Add an optional measured Origin 2022 export profile at `benchmarks/aa2195/examples/origin2022_quality_export.json`: Fig3/15/16 use 3x and Fig12/14 use 1x. Keep legacy defaults unchanged. An all-3x trial worsened Fig14 SSIM/MAE and reduced Fig12 edge F1, so it was not adopted.
- Correct Fig12 colorbar title/tick vertical text anchors by -9/-12 source pixels. Keep the colorbar rectangles, levels, matrices, fonts, horizontal positions, and scientific data unchanged. Include the text anchors in the existing colorbar render-identity inventory.
- Reject supersampled native rasters with incorrect width or excessive height mismatch before resizing. Width must equal requested width; height allows at most half a target pixel of integer rounding. Preserve the direct 1x path. Retain native dimensions in export evidence.

- Correct the live dependency to published originpro 1.1.15-compatible releases; declare extraction and image-analysis dependencies in requirements-benchmark.txt and relevant test dependencies in requirements-dev.txt.
- Preserve original hidden/minimized window observations when recovery succeeds; continuity cannot pass by replacing failed observations.
- Recompute source/data/crop hashes, source policy agreement, freshness flags, and evidence-artifact hashes during the batch audit. Bind published OPJU/PNG files to their audited counterparts.
- Bind candidate readback identity, normalized raw objects, and validation records to the hashed same-run inspection. Apply the existing evidence serializer so portable path normalization is preserved; changed readback contents cannot reuse stale passing validation flags.
- Mark shipped template metadata as historical instead of current asset inspection. Restore the paper-reproduction local-template, official-project, then native-construction workflow in SKILL.md.
- Add optional Fig3 full canvas (1245x950) with complete bottom axis titles and unchanged scientific data and physical panel geometry. Keep the historical 1245x900 default for compatibility comparisons only.
- Add a validated per-figure export supersampling map (integer 1-4). Reject unknown names, booleans, fractional factors, and hashtable member-shadowing inputs before I/O.

## Live Evidence Boundaries

Initial fresh-source five-figure batches ran locally on administrator Origin 2022 with Python 3.10.11. All five native OPJU projects passed save/reopen binding checks and the full-canvas Fig3 plus 3x-export batch passed strict window/source/structure/visual gates. At that stage, Fig12/14/15/16 exports were pixel-identical to the fresh baseline.

The later quality profile and Fig12 text correction were tested first with validated source reuse and then with fresh extraction. Both executions passed all five gates and produced identical RGB pixels to each other, with unchanged scientific data and thresholds. The final fresh run had 361 valid visibility samples. Local before/after SSIM was Fig12 0.801233/0.813380, Fig15 0.840919/0.841348, and Fig16 0.792995/0.822538; Fig3 and Fig14 were unchanged controls. Fig12 edge F1 improved from 0.821642 to 0.888785. Fig16 mean bar-boundary error improved from 0.476190 to 0.369048 px, while its maximum remained 1 px. These scalar summaries do not replace independently retained native evidence; paper files, exports, and local project artifacts are not included in this update.

A same-source, same-1245x950-canvas Fig3 control measured SSIM 0.736730 at 1x and 0.751831 at 3x, and edge F1 0.747656 and 0.755342. Color and layout scores decreased slightly while remaining above thresholds; supersampling is therefore optional, not a universal recommendation. The PNG is an Origin-rendered Lanczos-downsampled raster; OPJU data/plots remain native and editable.

The old and full Fig3 canvases must not be treated as the same baseline. The historical crop is incomplete. No acceptance thresholds were relaxed. Native editable reconstruction remains approximate rather than pixel-identical; Fig16 retains a bar-boundary maximum error of 1 px at its existing limit. The benchmark validates its AA2195 route, not every generic v6 plotting capability.

## Reproduce

From an elevated PowerShell Core session, with one visible authorized Origin 2022 instance:

```powershell
& "$HOME\.codex\skills\originplot-skill\scripts\run_five_figure_live_batch.ps1" `
  -OutputRoot <new-empty-output-directory> `
  -SourceDataPolicy fresh_extract -SourcePdf <authorized-AA2195-PDF> `
  -Fig3CanvasMode full -ExportSupersampleByFigure @{fig3=3;fig12=1;fig14=1;fig15=3;fig16=3}
```

When no Origin process is open, also pass `-LaunchOriginExe <local-Origin-install-directory-or-executable>`. The runner preserves a visible final Origin window. Full-repository tests: `py -3.10 scripts/run_all_tests.py`.
