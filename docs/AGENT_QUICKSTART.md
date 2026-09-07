# OriginPlot Agent Quickstart

Operational details supplement [SKILL.md](../SKILL.md). The optional full-repository benchmark adds stricter requirements in `benchmarks/aa2195/docs/benchmark.md`.

## Data and Planning

- Roles: `x`, `x_error`, `y`, `y_error`, `z`, `group`, `category`, `label`, `support`, `retain`, `uncertain`. Resolve ambiguity before execution.
- Wide-XY planning keeps all recognized Y columns unless `--y` selects one. Confirm per-series error mappings in FigureSpec; never share the first error column across curves. Invalid column mappings fail before writing a plan.
- Check the [Capability Matrix](CAPABILITY_MATRIX.md); registration alone does not prove a live route.
- Executable styles: series `color`, `line_color`, `line_width_pt`, `symbol`; legend `visible`, `frame`. Precedence: preset, confirmed reference suggestions, explicit user choices. Rejected fields stay in the style audit, never reported as applied.

## Templates for Paper Reproduction

1. Inspect the local template catalog and installed Origin templates.
2. If insufficient, inspect relevant downloadable projects from the official OriginLab Graph Gallery. Safely extract, open in compatible visible Origin, and check graphs, worksheets, plot types, bindings, and complete project structure. Record hashes and selection/rejection reasons.
3. Consult official Chinese graphing documentation and quick-help for the chosen route. Use native API construction only after documenting why available templates do not meet the figure requirements.

AA2195 sanitized template records are historical metadata. Recorded booleans, hashes, and reconstruction routes do not establish current asset or editable-open inspection.

## Live Session and Visibility

Use Python 3.10 and an administrator-authorized Origin worker with the user's compatible Origin installation. Attach to the visible authorized application; release with `op.detach()` in `finally`. Before saving/exporting, check the target OPJU is not open; investigate locks and residual processes before retrying.

Never create graphs with `hidden=True` or call `op.set_show(False)`. A hidden/redirected helper console is allowed; Origin's window, worksheets, graph, and progress stay visible. Raster screenshots cannot replace native worksheet-backed graphs.

- Require one visible, non-`-Embedding` Origin process with a stable PID. Stop only confirmed `Origin*.exe -Embedding` residue without a main window; record PIDs and protect every window-bearing process. Remaining embedding or unexplained hidden processes block attachment.

The five-figure runner additionally enforces these presentation/evidence steps:

- With no Origin open, `-LaunchOriginExe <local-Origin-install-directory-or-executable>` resolves the application executable, launched with `WindowStyle Normal`. Otherwise attach to the one authorized visible process.
- Restore/foreground the selected window before attach and each worker; record handle and presentation result. Record focus separately because users may switch applications.
- Sample visibility/minimized state every 500 ms during workers, with pre-worker, post-worker, and post-display evidence. Preserve original hidden/minimized observations even after recovery; restoration cannot erase continuity failures.
- Set `visible_window_evidence_required=true`; audit with `--require-visible-window-evidence`. Missing/hidden/minimized samples fail. Historical audits lacking samples cannot pass retroactively.
- Show each completed graph for 3 seconds by default (`-FigureDisplaySeconds 1..60`), print progress/elapsed time, and leave the final Origin window open for review.

## Verification and Failure Handling

Native delivery: authorized worker, worksheet-backed graphs, OPJU save, detach, reopen, binding readback, Origin export, output validation. All applicable gates must pass; an image or zero exit code is insufficient.

Standalone `verify` checks artifact hashes, image decoding/nonblankness, PDF parsing/nonempty page streams, and recorded live gates. It neither launches Origin, reopens OPJU, nor authenticates evidence. Success means files match recorded evidence. Missing historical hashes require a new live run, not manufactured hashes.

Retain benchmark source provenance, data/crop hashes, same-run manifests, PNG, OPJU, readback, and window observations. Published OPJU/PNG must match audited copies. Recompute hashes; recorded pass flags alone are insufficient. Report fresh extraction, validated reuse, and crop re-extraction distinctly.

Follow SKILL.md's failure order. Never relax scientific/visual thresholds, suppress failures, or promote unsupported operations. Offline tests cannot prove licensed Origin execution.

## Dependencies and Development

- Core table inspection/planning: `requirements-core.txt`.
- Live Origin: add `requirements-origin.txt` on Windows.
- Full AA2195 extraction/live evaluation: `requirements-benchmark.txt` (includes core/Origin requirements).
- Full-repository offline tests: `requirements-dev.txt`, then `py -3.10 scripts/run_all_tests.py`.

The compact runtime omits the full-repository benchmark/development requirements and scripts. Use its included core/Origin requirements for ordinary plotting. For implementation boundaries and test expectations, read the [Development Guide](DEVELOPMENT_GUIDE_v6.1.md).
