# OriginPlot v5.8.9-p14 Gap Analysis

## Audit baseline

- Audit date: 2026-07-12.
- Source reviewed: the unpacked `03_tools/originplot_v589_p13_work` tree.
- Git status, branch, and log could not be collected because this tree has no `.git` directory.
- Baseline: `python scripts/run_all_tests.py` passed 165 tests with zero skips.
- Baseline `SKILL.md`: 758 lines and 82,021 bytes.

## Confirmed gaps

| Area | p13 state | p14 action |
|---|---|---|
| Public scope | README implies all three AA2195 figures are reproduced | Publish evidence-bounded benchmark states and explain that new figures require a builder |
| Skill instructions | Active rules, old patches, and run history share one 82 KB file | Keep the operational decision path in `SKILL.md`; move details and history to `references/` |
| Dependencies | No reproducible dependency groups | Add core, Origin-runtime, and developer requirement files plus an import audit |
| CI | No GitHub Actions workflow | Add Windows/Python 3.10 offline CI; explicitly exclude live Origin claims |
| CLI | Implicit dry-run and one `--live` flag | Add mutually exclusive `--dry-run`/`--live`, `--require-live-success`, and explicit result fields |
| Builders | Worker hard-codes three figure choices | Add a duplicate-safe registry while preserving `--figure fig12|fig15|fig16` |
| Public example | Existing examples are benchmark-specific | Add a synthetic, redistributable generic-line dry-run example |
| V4 wording | V4 scripts exist in the source tree but are excluded from the shareable p13 package | Keep them as legacy/migration inputs; do not present them as the current runtime |
| Companion skill | Routing language can look automatic | Document `scientific-figure-reproduction` as optional and separately installed |
| Visual completion | Fig12 and Fig16 remain evidence-gated; Fig15 has a frozen regression route | Preserve provisional states and require same-run save/reopen evidence for promotion |
| Template route enforcement | Documentation required official/local search, but the worker accepted paper-like candidates without its evidence | Require a validated, sanitized template-search record before Fig12/Fig15/Fig16 dry-run or live construction; package the four official entrances and inspected-project metadata |

## Rule migration map

- Current execution, provenance, outputs, and fail-closed rules: `references/current-contract.md`.
- Origin 2022 attachment, units, save/reopen, and inspection: `references/origin-runtime.md`.
- Visual scoring and promotion: `references/visual-qa.md`.
- Fig12/Fig15/Fig16 active benchmark contracts: `references/aa2195-benchmark.md`.
- Runtime failures and recovery: `references/troubleshooting.md`.
- Version history and named-run records: `references/changelog.md`.
- V2/V3/V4 and superseded route clauses: `references/legacy-and-migration.md`.

## Non-regression constraints

- Preserve the 5,000-row global direct-Worksheet budget.
- Preserve Origin session release: attached sessions detach; owned hidden sessions exit.
- Preserve direct Worksheet-to-Plot readback after OPJU reopen.
- Do not promote dry-run, inherited, copied, or pre-save-only evidence.
- Do not remove Fig12, Fig15, or Fig16 legacy CLI entry points.
- Do not claim a live or visual pass without a licensed same-run Origin execution.
- Fail with `E130_TEMPLATE_SEARCH_REQUIRED` before construction when a paper-like candidate lacks complete official/local template-search evidence.
