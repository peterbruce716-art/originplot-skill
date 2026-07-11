# OriginPlot v5.8.9-p14 Implementation Report

## 1. Execution summary

p14 separates public capability from benchmark evidence, keeps the specialized Fig12/Fig15/Fig16 Origin 2022 builders, and adds maintainable contracts for dependencies, CI, builder registration, CLI modes, public demonstration, packaging, and official-template-first routing. It does not claim universal image-to-OPJU conversion or completed visual closure where the same-run evidence does not support that conclusion.

The paper-like route is fail-closed before construction. Fig12, Fig15, and Fig16 candidates must reference a validated `originplot.template_search_record.v1`. The record proves that all four user-authorized official Origin entrances and both local template sources were checked, and that the required Graph Gallery projects were opened as editable projects in administrator Origin before they were selected as references.

## 2. Changed files

The p14 release changes are grouped below. Generated evidence, OriginLab projects, source crops, and OPJUs are intentionally outside the open-source archive.

- Public contract: `README.md`, `SKILL.md`, `LICENSE`, `p14_gap_analysis.md`, and this report.
- Progressive references: `references/current-contract.md`, `references/origin-runtime.md`, `references/visual-qa.md`, `references/aa2195-benchmark.md`, `references/troubleshooting.md`, `references/legacy-and-migration.md`, and `references/changelog.md`.
- Reproducibility: `requirements-core.txt`, `requirements-origin.txt`, `requirements-dev.txt`, `scripts/audit_dependencies.py`, and `.github/workflows/offline-ci.yml`.
- Builder infrastructure: `builders/base.py`, `builders/registry.py`, `builders/generic/__init__.py`, and `builders/generic/line_builder.py`.
- CLI and template routing: `scripts/origin_candidate_worker.py`, `scripts/inspect_official_templates.py`, `examples/candidates/fig12.json`, `examples/candidates/fig15.json`, `examples/candidates/fig16.json`, and `examples/template_search/aa2195_official_template_search.json`.
- Public demo: `examples/public_demo/README.md`, `examples/public_demo/generate_source.py`, `examples/public_demo/figure_spec.json`, and `examples/public_demo/candidate.json`.
- Packaging and regression: `scripts/build_shareable_package.py`, `scripts/validate_shareable_package_v5.py`, `scripts/run_all_tests.py`, and `tests/test_v589_p14_maintainability.py`.

## 3. README and SKILL refactor

`SKILL.md` was reduced from 758 lines and 82,021 bytes to a bounded active contract under 250 lines and 30 KB. Runtime details, benchmark rules, troubleshooting, visual QA, and migration history moved into one-level `references/` files. README now exposes honest benchmark states, installation, dependency groups, CLI semantics, template inspection, tests, builder extension, packaging, licensing, and limitations.

Both documents require template discovery before construction and preserve the four official entrances. The open-source package also contains a sanitized template-search record with those URLs and the inspected-project metadata required by the route gate.

## 4. Dependency grouping

- `requirements-core.txt`: portable runtime and validation dependencies.
- `requirements-origin.txt`: licensed Origin automation support for Windows/Python 3.10.
- `requirements-dev.txt`: tests and developer validation.
- `OriginExt`: supplied by Origin and deliberately not represented as an ordinary cross-platform package.

`scripts/audit_dependencies.py` compares external imports with the declarations and fails when a required package is absent from the grouped requirements.

## 5. What CI can and cannot verify

Windows/Python 3.10 offline CI can compile Python, run pytest and the packaged runner, audit dependencies, generate the public synthetic demo, execute its generic dry-run, build the shareable ZIP, and validate package contents.

CI cannot prove licensed Origin attachment, administrator session continuity, downloaded project compatibility, OPJU save/reopen behavior, direct live Worksheet binding readback, Origin-rendered exports, or visual similarity. Those claims require an administrator-started visible Origin 2022 instance and same-run live evidence.

## 6. Builder registry design

`builders/base.py` defines immutable builder metadata plus plan and live call contracts. `builders/registry.py` provides unique registration, duplicate rejection, stable unknown-ID failure, listing, and legacy figure resolution. Built-ins register Fig12, Fig15, Fig16, and the deliberately dry-run-only `generic_line` example. Registry resolution does not bypass the paper-like template-search gate.

## 7. CLI compatibility

The worker preserves `--figure fig12|fig15|fig16`, adds `--builder` and optional `--figure-spec`, and makes `--dry-run` and `--live` mutually exclusive. No mode flag retains the documented legacy dry-run default. `--require-live-success` exits nonzero unless live Origin verification and pass eligibility are both true.

Dry-run reports `planned_not_executed`; it cannot set structure, visual, live, or pass-eligible fields true. Missing paper-like template evidence fails with `E130_TEMPLATE_SEARCH_REQUIRED` before construction or Origin import.

## 8. Public demo usage

```powershell
python examples/public_demo/generate_source.py --output-dir "$env:TEMP\originplot-public-demo"
python scripts/origin_candidate_worker.py --builder generic_line `
  --figure-spec examples/public_demo/figure_spec.json `
  --candidate examples/public_demo/candidate.json `
  --output-dir "$env:TEMP\originplot-public-demo\plan" --dry-run
```

The demo is synthetic, redistributable, and planning-only. It is not a live Origin or visual-fidelity claim.

## 9. Test commands and actual results

Baseline before the route-gate correction:

- `python scripts/run_all_tests.py`: 180 tests passed, zero skipped.
- Independent ZIP validation: 146 entries, `status=ok`, zero failures.

Correction verification results:

- `python -m compileall -q .`: exit 0.
- `python -m pytest -q`: 187 passed plus 3 subtests, exit 0.
- `python scripts/run_all_tests.py`: 187 passed, zero skipped, exit 0.
- `python scripts/audit_dependencies.py`: `status=ok`, no missing declarations.
- `quick_validate.py .`: `Skill is valid!`.
- Public generator and generic-line dry-run: exit 0; status `planned_not_executed`.
- Fig12, Fig15, and Fig16 dry-runs: exit 0; each reports four official sources, both local searches, administrator editable-open evidence, the required GIDs, and the template-search record SHA256.
- Pre-release package build: 147 entries; validation is rerun on the final archive after this report is updated.

## 10. Live Origin run status

The original p14 same-run administrator workflow completed build, save, detach, editable reopen, readback, and Origin export for all three benchmarks. Each retained direct Worksheet-to-Plot bindings and remained within the 5,000-row budget.

| Figure | Direct plots | Worksheet rows | MAE | SSIM | Layout | Edge | Color | Honest status |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Fig12 | 3 | 4,968 | 0.04437 | 0.76412 | 0.98904 | 0.69987 | 0.97374 | Structure pass; visual baseline not promoted |
| Fig15 | 10 | 255 | 0.03334 | 0.84780 | 0.98878 | 0.74736 | 0.99380 | Frozen regression pass and pass-eligible |
| Fig16 | 11 | 1,380 | 0.04910 | 0.77753 | 0.98772 | 0.65732 | 0.97019 | Numeric gates pass; policy remains provisional |

The official-template inspection was also run in administrator Python against the visible administrator Origin 2022 SR1 instance. GID499, GID459, GID1609, GID27, GID399, and GID1652 opened as editable projects; their hashes, Worksheet rows, Plot types, and direct bindings were recorded. The open-source JSON contains only sanitized metadata, not licensed projects or machine paths.

## 11. Remaining limitations

- Fig12 still differs in some contour-boundary shapes and is not labeled visually complete.
- Fig16 remains provisional by benchmark policy despite passing the current scalar thresholds.
- Generic new figures still need a figure-specific live builder and evidence contract.
- Offline CI cannot make licensed Origin claims.
- The unpacked development tree has no Git metadata, so repository history cannot be reconstructed from this directory.

## 12. Recommended next version

The next version should focus on a new same-run administrator Origin calibration for Fig12 contour-boundary geometry and Fig16 semantic/visual promotion, while keeping the now-enforced template-search provenance fixed. Do not widen generic plot support until those benchmark closure claims are resolved.

## 13. git diff --stat

`git status --short` and repository `git diff --stat` return `fatal: not a git repository` because the supplied development tree has no `.git` directory. The release process therefore used `git diff --no-index --stat` between the verified p13 release directory and the corrected p14 pre-release directory as an honest file-level substitute:

```text
97 files changed, 2041 insertions(+), 858 deletions(-)
```

The no-index command returned 1 because differences were present, which is the documented `git diff` behavior rather than a validation failure.

## 14. Local commit status

No local commit was created because the supplied source tree is not a Git worktree. No push was attempted. The intended commit message remains `refactor: release originplot skill v5.8.9-p14` for use only after the source is placed in a real repository and its unrelated changes are reviewed.
