# Changelog

## 6.1.3 - 2026-09-07

### Fixed
- `version.json` declared `6.0.0` while `pyproject.toml`, `CHANGELOG.md` and `SKILL.md` declared `6.1.2`. `scripts/versioning.py` exposes that field as `release_version`, so the release gate in `scripts/validate_release_candidate.py` was failing with `skill_version_mismatch` on the shipped tree.
- `scripts/check_version_consistency.py` compared only pyproject, changelog and SKILL, so it passed on that inconsistent tree. It now also reads `version.json`. The retained AA2195 benchmark evidence identity stays independent and is not compared.
- `scripts/run_all_tests.py` globbed only `tests/test_v6_*.py` and silently skipped the `capability`, `contract`, `contracts`, `fail_closed` and `package_boundary` suites: 7 of 16 modules. It now discovers every test module, and references `load_versions`, which the release gate requires.
- Batch comparison, export supersampling, Origin attach cleanup, and evidence run identity now fail closed on missing or malformed inputs instead of accepting ambiguous state or masking the primary error.
- `requirements-dev.txt` now declares the NumPy/scikit-image benchmark test stack, so clean GitHub runners collect the AA2195 regression tests instead of relying on packages preinstalled on a developer workstation.
- `scripts/audit_five_figure_batch.py` read `live_validation_status.json` but never consumed its `status`, per-run `exit_code` or `pid_stable`. A batch the runner itself marked `failed`, with a worker that exited 1 against an unstable Origin, audited as `pass` with zero findings and exit code 0 -- and `run_five_figure_live_batch.ps1` exits with that status. It now fails closed on all three, and reports `SKILL_VERSION_MISSING` for manifests that stamp no version (five unstamped manifests previously "agreed" with each other).
- `benchmarks/aa2195/builders/fig12_builder.py` styled `lineColor1..3` and `lineWidth1..3` while every Fig12 panel declares four z-levels, so the fourth contour line kept Origin's default black instead of the configured `(86, 107, 68)`. All declared slots are now styled.
- `benchmarks/aa2195/builders/fig12_builder.py` enabled the native contour lines and then disabled them: `_apply_contour_line_style` ended with `showLines(1)` plus `updateScale()`, and the path-overlay caller issued a bare `showLines(0)` with no commit. Whether that trailing command took effect decided the exported page, and it failed in 2 of 27 measured live runs, doubling the boundary the type-34 overlay already draws -- which the canonical route explicitly forbids. The function now takes the final visibility as an argument and sets colour, width, visibility and labels in one committed block, so the overlay route asks for lines-off directly and the round trip no longer exists. 40 standalone live runs plus a full five-figure batch produced byte-identical canonical exports (p ~ 0.046 under the measured baseline rate; the structural argument carries the rest), and Fig3/Fig14/Fig15/Fig16 are unchanged byte for byte. An earlier attempt to fix this by adding `updateScale()` after `showLines(0)` made it worse and was reverted.

- `scripts/validate_shareable_package_v6.py` hardcoded `"6.0.0"` as the expected package version. That literal is what masked the version drift above: it agreed with the stale `version.json` while `pyproject.toml` said 6.1.2, so CI certified a package whose own metadata disagreed with itself. It now compares `version.json` against the `pyproject.toml` that ships inside the same archive, and rejects an empty version. The AA2195 evidence identity stays pinned to `5.8.9-p18`.
- `scripts/validate_release_candidate.py` invoked `scripts/run_all_tests.py` with `--expected-min-tests` and `--json-out`, which the runner never accepted, so no result JSON was written and the `run_all_tests` gate always read 0 tests. The runner now implements both flags and emits an `originplot.run_all_tests.v1` record.

### Changed
- The five-figure runner now permits an explicitly requested visible Origin 2022 launch with `validated_reuse` or `validated_crop_reextract`, so an already validated source bundle can be benchmarked without requiring a second PDF extraction. Source-data and live-license gates remain unchanged.
- Enforced visible Origin operation across the AA2195 benchmark builders and smoke diagnostic: graph-page creation uses an explicit visible helper, new diagnostic sessions are reported as visible, and the legacy `--new-hidden` flag is compatibility-only and never selects a hidden mode.
- `near_threshold_metrics` is no longer decided by a single absolute 0.001 margin. That constant was applied to gates whose units differ by orders of magnitude, so Fig12 `edge_score` sat 0.41% of its budget from failing and was still reported as safe. The gate now also records `gate_headroom_fractions` and flags any passing metric with under 10% of its own budget remaining. Pass/fail behaviour is unchanged; only reporting improved.
- Retired the `validate_shareable_package_v5` release gate in favour of `validate_shareable_package_v6`. The v5 validator requires eight paths that the v6 restructure moved into `benchmarks/aa2195` or deleted, so it could not pass on a v6 tree. The archive it produced also feeds `absolute_path_scan` and `cache_temp_artifact_scan`, which now scan the v6 package.

### Added
- `scripts/compare_five_figure_batches.py` diffs two five-figure batch roots and reports per-metric drift, `pass_flip`, `near_threshold_regression` and `identity_claims_equality_but_metrics_differ`.
- `scripts/probe_fig12_contour_line_state.py` records the Origin colormap readback boundary by reading every candidate line property on two saved Fig12 projects that differ only by three contour lines. Every read is sentinel-guarded, and control expressions are reported separately so an unreadable property cannot masquerade as a measurement.
- `tests/test_v6_fig12_contour_style.py` pins the Fig12 contour fix offline, with no Origin required: it asserts the emitted LabTalk styles every declared z-level, that a hidden request never emits `showLines(1)`, that visibility is set before the commit in the same block, and that the path-overlay call site asks for hidden lines. Each assertion was mutation-checked -- reverting to three styled slots, to the enable-then-disable round trip, or to an unconditional visible request each fails exactly the corresponding test.
- Optional `export_supersample` candidate parameter (integer 1-4, default 1) renders a page at N times the benchmark canvas and resamples down with Lanczos, matching the anti-aliasing the PyMuPDF source crops already carry. It changes only rasterisation, not the Worksheet bindings, plots or OPJU. `export_supersample=1` is byte-identical to the previous export path; any higher factor is recorded in the builder route and changes `render_identity.fingerprint`. Measured results per figure are in `benchmarks/aa2195/docs/benchmark.md`; nothing is promoted on it, and it is deliberately not a global default because Fig14 regresses where Fig3 improves.
- Registered `export_supersample` in the `_effective_builder_route` allowlist in `scripts/origin_candidate_worker.py`. That function drops any route key not on the list, so before registration a supersampled export carried the same fingerprint as a 1:1 export. A test now pins both directions.
- Documented cross-batch reproducibility in `benchmarks/aa2195/docs/benchmark.md`: `render_identity.fingerprint` hashes declared inputs, not the export; a measured Fig12 case where a fresh versus reused Origin process moved `edge_f1` by -0.0102 to 0.0015 above its floor under an identical fingerprint; and the fact that `layer.cmap.showLines` is asserted by contract but never read back.

### Known gaps
- The Fig12 visual gate rewards a contract violation. The canonical route hides the native contour lines so the type-34 overlay boundary is not doubled, but a doubled boundary scores `edge_f1` 0.0102 *higher* because a second boundary matches more source edge pixels. The promoted p18 baseline is a doubled-boundary run, so the retained Fig12 evidence records the violating state, and a compliant render sits at 0.77% of the `edge_f1` budget. That gate should be re-derived from the canonical route rather than inherited. The builder defect that produced the violation is fixed above; this is about the threshold and the retained evidence, which are a maintainer decision.
- `layer.cmap.showLines` cannot be read back on Origin 2022. `scripts/probe_fig12_contour_line_state.py` shows `showLines`, `enableLines`, `lines`, `lineVisible`, `showLine`, `numLevels` and `showLabels` do not resolve, while every property that does resolve (`numColors`, `lineColor1..2`, `lineWidth1..3`, `lineStyle1`, `cmap.type`) is identical whether or not the lines are drawn. The `showLines(3)`-is-a-hard-failure contract therefore cannot be gated structurally; pixel comparison is the only detector. Note that an unresolvable LabTalk property leaves the destination variable at its previous value, so an unguarded read returns the last number read and looks like evidence -- the probe brackets every read with a sentinel.
- `scripts/validate_release_candidate.py` is v5-era tooling that no CI workflow runs, and it is now 7 of 10 gates green: `compileall`, `run_all_tests`, `random_directory_portability`, `validate_shareable_package_v6`, `absolute_path_scan`, `cache_temp_artifact_scan` and `report_version_consistency` all pass against this tree. Its `EXPECTED_MIN_TESTS = 117` is satisfied by the 126 tests here, so no threshold change was needed. The three remaining gates want a v5-era evidence layout that the current worker does not produce: `benchmark_evidence_packages` rejects the absolute local paths a raw batch necessarily contains and expects a sanitized package, `live_readback_validation` wants a `fig15_inspection_missing` artifact, and `final_release_bundle_validation` needs a bundle argument. `scripts/materialize_live_evidence.py` is the intended sanitizer but has no CLI and expects a different file set (`result.opju`, `inspection.json`, `qa_report.json`) than the worker emits. Bridging or retiring that path is a release-policy decision and has been left alone.
- The Fig3 and Fig14 pixel-fidelity gap is diagnosed but unfixed: the source crop is rasterised by PyMuPDF at scale 3.0 (256 grey levels, 8.22% intermediate pixels) while Origin exports 1:1 (158 levels, 5.04%), which accounts for essentially all of Fig3's 25.6% ink deficit. Supersampled export would change the pixels of all five figures and invalidate the frozen Fig15/Fig16 identities, so it was not applied.

### Validation
- See the GitHub Actions run attached to the 6.1.3 release commit for the authoritative test and packaging results.
- Five same-run administrator Origin 2022 `fresh_extract` five-figure live batches across both `batch_started` and `preexisting_visible` launch modes passed before release hardening; the offline regression suite pins their structural contracts.

## 6.1.2

### Changed
- Reduced SKILL guidance duplication to improve AI context efficiency.
- Kept scientific safety rules, capability boundaries, and verification requirements explicit.
- Improved agent workflow readability for faster decision routing.

### Validation
- Existing CI validation remains authoritative:
  - ruff check
  - ruff format
  - pytest
  - package validation

## 6.1.1

### Added
- Production quality gate documentation from semantic validation through live verification.
- Clearer AI agent stop conditions to prevent promotion of partial or preview-only results.
- Stronger separation between planning support, native execution, and verified evidence.
- Package metadata synchronization with the v6.1.1 stable version.

### Changed
- Updated Skill guidance to emphasize fail-closed scientific plotting workflows.
- Improved completion criteria for editable Origin deliverables.
- Removed release-version ambiguity between documentation and Python package metadata.

### Validation
- ruff check
- ruff format --check
- pytest
- package import validation
- shareable package validation

## 6.1.0rc1

### Added
- Release candidate tracking for the v6.1 architecture hardening work.
- Explicit release validation workflow documentation.
- Stronger CI and package boundary validation.
- Clearer documentation for FigureSpec, OperationPlan, primitive maturity, and fail-closed execution boundaries.

## 6.0.0

- Initial v6 architecture release.
