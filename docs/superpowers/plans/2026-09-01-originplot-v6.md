# OriginPlot v6 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a compact v6 core for semantic table understanding, ten general plot primitives, deterministic OperationPlans and administrator-only verified Origin execution, with AA2195 isolated as regression benchmarks.

**Architecture:** Source tables are inspected into DataUnderstanding, confirmed as FigureSpec v6, compiled through a registry into Origin-independent OperationPlans, then executed by the existing elevated Origin lifecycle through a dedicated adapter. The runtime preserves administrator and release invariants while core code removes AA2195 and `generic_line` special cases.

**Tech Stack:** Python 3.10, stdlib dataclasses/json/csv/hashlib, openpyxl for XLSX, optional pandas/xlrd for XLS, originpro/OriginExt for live Windows execution, pytest.

**Spec:** `docs/superpowers/specs/2026-09-01-originplot-v6-design.md`

## Global Constraints

- Live Origin workers remain administrator-only.
- Release retains the continuous administrator envelope and cannot be weakened.
- Core modules must not import AA2195 benchmark modules.
- Builders never import `originpro`.
- Source tables are read-only; scientific values are never silently derived or altered.
- Public v6 primitives are exactly: line, scatter, line_scatter, errorbar, bar, grouped_bar, stacked_bar, heatmap, contour, multi_panel.
- Python 3.10 remains the validated baseline.

---

### Task 1: FigureSpec v6 and semantic inspection

**Files:**
- Create: `originplot/spec/models.py`
- Create: `originplot/spec/io.py`
- Create: `originplot/semantic/inspect.py`
- Create: `originplot/semantic/recommend.py`
- Test: `tests/test_v6_semantic_and_spec.py`

**Interfaces:**
- Produces `inspect_table(path, sheet=None) -> dict`, `recommend_plots(understanding) -> list[str]`, `load_figure_spec(path) -> FigureSpec`, `normalize_figure_spec(payload, base_dir) -> FigureSpec`.

- [ ] Write tests for CSV/XLSX role inference, unresolved columns, source hashing and FigureSpec validation.
- [ ] Run focused tests and confirm failures.
- [ ] Implement read-only table inspection and v6 dataclasses/validation.
- [ ] Run focused tests and confirm pass.
- [ ] Commit.

### Task 2: Primitive Builder Registry and OperationPlan

**Files:**
- Create: `originplot/builders/base.py`
- Create: `originplot/builders/registry.py`
- Create: `originplot/builders/xy.py`
- Create: `originplot/builders/bar.py`
- Create: `originplot/builders/matrix.py`
- Create: `originplot/builders/composite.py`
- Create: `originplot/operation_plan.py`
- Test: `tests/test_v6_builders.py`

**Interfaces:**
- Produces `compile_figure(spec) -> OperationPlan`, `resolve_builder(plot_type) -> FigureBuilder`, `list_builders() -> tuple[str, ...]`.

- [ ] Write registry tests covering all ten primitives and duplicate rejection.
- [ ] Write compile tests proving builders return declarative operations without Origin imports.
- [ ] Implement four compiler families and multi-panel composition.
- [ ] Run builder tests.
- [ ] Commit.

### Task 3: Runtime capabilities, doctor and administrator invariants

**Files:**
- Create: `originplot/runtime/capabilities.py`
- Create: `originplot/runtime/doctor.py`
- Modify: `originplot/runtime/origin_session.py`
- Test: `tests/test_v6_runtime.py`

**Interfaces:**
- Produces `resolve_origin_capabilities(version) -> dict`, `doctor() -> dict` while retaining `is_administrator()` and `attached_origin()` behavior.

- [ ] Write tests asserting Origin worker admin requirements remain true and capability status is version-gated.
- [ ] Implement capability-file loading and doctor diagnostics without launching Origin.
- [ ] Keep attach identity checks and detach semantics unchanged.
- [ ] Run runtime tests.
- [ ] Commit.

### Task 4: Origin adapter and verified artifact lifecycle

**Files:**
- Create: `originplot/adapters/originpro.py`
- Create: `originplot/verification/artifacts.py`
- Create: `originplot/verification/readback.py`
- Modify: `scripts/origin_profile_worker.py`
- Modify: `originplot/runtime/protocol.py`
- Test: `tests/test_v6_origin_adapter_protocol.py`

**Interfaces:**
- Adapter consumes `OperationPlan` and validated data payload and emits canonical `figure.opju/png/pdf/tif` plus readback.

- [ ] Write fake-Origin protocol tests for line/scatter/errorbar/bar/matrix operation dispatch.
- [ ] Refactor worker to dispatch plans rather than special-case `generic_line`.
- [ ] Preserve administrator preflight, save/detach/reopen/binding/export gates.
- [ ] Produce canonical artifact names.
- [ ] Run protocol tests.
- [ ] Commit.

### Task 5: Unified CLI and controller

**Files:**
- Create: `originplot/cli/main.py`
- Create: `originplot/cli/__init__.py`
- Create: `originplot.cmd`
- Rewrite: `scripts/originplot.py`
- Rewrite: `originplot/controller.py`
- Test: `tests/test_v6_cli_controller.py`

**Interfaces:**
- Public commands: `doctor`, `inspect`, `plan`, `render`, `draw`, `verify`.

- [ ] Write CLI/controller tests for inspect/plan/dry-run and builder-neutral dispatch.
- [ ] Remove `generic_line` controller conditionals.
- [ ] Add `draw` orchestration that stops on unresolved semantic roles unless mapping is explicit.
- [ ] Keep profile and elevated worker routing intact.
- [ ] Run CLI/controller tests.
- [ ] Commit.

### Task 6: AA2195 benchmark isolation and aggressive cleanup

**Files:**
- Move: `builders/aa2195/**` -> `benchmarks/aa2195/builders/**`
- Move AA2195 benchmark metadata/examples/evidence/tests under `benchmarks/aa2195/` where practical.
- Delete obsolete top-level V5 protocol/review/migration reports from product root.
- Remove legacy product-core AA2195 registrations.
- Add: `benchmarks/aa2195/README.md`
- Test: `tests/test_v6_package_boundaries.py`

**Interfaces:**
- Core imports must not contain `builders.aa2195` or `benchmarks.aa2195`.

- [ ] Write boundary test that scans `originplot/` for benchmark imports.
- [ ] Move benchmark code without changing its scientific parameters/evidence.
- [ ] Point benchmark-only entry points at the new paths.
- [ ] Delete obsolete root reports/protocol copies.
- [ ] Run boundary and retained benchmark offline tests.
- [ ] Commit.

### Task 7: Version, docs, packaging and CI

**Files:**
- Rewrite: `SKILL.md`
- Rewrite: `README.md`
- Modify: `version.json`
- Modify: `.github/workflows/offline-ci.yml`
- Modify: `requirements-core.txt`
- Add/update v6 examples.

**Interfaces:**
- Public package identity becomes `6.0.0`; benchmark evidence keeps its historical identity inside benchmark metadata rather than product identity.

- [ ] Update concise user docs around `originplot.cmd doctor` and `originplot.cmd draw <file>`.
- [ ] Document ten primitives, semantic safeguards, outputs and administrator invariant.
- [ ] Update offline CI to run v6 focused tests plus package validation.
- [ ] Run compileall, pytest, dependency audit and package validation.
- [ ] Commit.

### Task 8: Final verification

- [ ] Run `python -m compileall .`.
- [ ] Run `python -m pytest -q`.
- [ ] Run `python scripts/run_all_tests.py` or its v6 replacement.
- [ ] Run `python scripts/audit_dependencies.py`.
- [ ] Validate the shareable package.
- [ ] Compare `main...originplot-v6` and inspect for accidental admin-policy weakening or benchmark imports in core.
- [ ] Only after all checks pass, prepare integration/release options.
