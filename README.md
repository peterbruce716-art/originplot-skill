# OriginPlot Skill v5.9.0

## Profile-aware workflow

New commands use three profiles. `standard` is the default; `quick` reduces routine overhead; `release` preserves the retained p18 strict validation path.

```powershell
# Routine editable plot
python scripts/originplot.py --figure-spec figure_spec.json --builder generic_line `
  --profile quick --source-policy supplied --live --output-dir outputs\quick

# SCI reconstruction (default profile)
python scripts/originplot.py --figure-spec figure_spec.json --builder generic_line `
  --profile standard --source-policy supplied --live --output-dir outputs\standard

# Strict benchmark or release validation
python scripts/originplot.py --figure fig15 --candidate candidate.json `
  --profile release --live --require-live-success --output-dir outputs\release
```

The controller handles profile resolution, bounded template policy, task JSON, status, and reporting without administrator rights in Quick/Standard. The Origin worker owns attach, native construction, save, detach, reopen, binding readback, and Origin export. See [workflow migration](references/workflow-migration.md) and [the implementation report](references/implementation-report.md).

OriginPlot is a verification framework for editable Origin/OriginPro projects. It includes AA2195-specific builders for Fig3, Fig12, Fig14, Fig15, and Fig16. It is not a universal system that converts any input image into a high-fidelity OPJU automatically.

The core acceptance loop is native editable construction, save, release, reopen, live readback, second Origin export, and evidence-gated visual comparison. A look-alike raster alone is never sufficient.

`5.9.0` is the downloadable release revision. The active functional contract and AA2195 evidence identity remain `5.8.9-p18`; `version.json` is the machine-readable source for this distinction. The 5.9.0 package carries the retained same-run fresh-PDF administrator Origin 2022 evidence without relabeling that p18 evidence as a new contract.

## Capability boundary

OriginPlot handles Origin workbooks, native plots, graph layers, editable annotations, OPJU persistence, readback, and Origin-rendered evidence. A new figure normally needs a FigureSpec, source or reconstructed data, a registered builder, benchmark gates, and a licensed Origin validation run.

Python/R/Matplotlib redraws are outside this repository. `scientific-figure-reproduction` is an optional, separately installed companion skill; OriginPlot does not bundle it or silently transfer work to it.

## Benchmark status

| Benchmark | Structure and protocol | Visual state | Public conclusion |
|---|---|---|---|
| Fig3 | Four native layers with 44 direct Worksheet line plots and source-calibrated anchors | Same-run Origin evidence; approximate reconstruction gate promoted at SSIM 0.650 with stricter MAE/layout/color gates | Validated editable reconstruction route; not a claim of exact digitization |
| Fig12 | Three native XYZ Worksheet plots plus editable type-34 source-vectorized regions and editable axis-title overlays | Canonical same-run Origin 2022 save/reopen evidence passes MAE, SSIM, layout, edge, and color gates | Validated editable reconstruction route; not raw-data recovery or pixel identity |
| Fig14 | One native layer with six direct Worksheet plots, line-symbol series, and editable error paths | Same-run Origin evidence passes structure and visual gates | Validated editable reconstruction route |
| Fig15 | Specialized two-layer builder and frozen regression contract are retained | A known regression route exists; new runs still require same-run Origin evidence | Validated regression capability, not a universal reproduction claim |
| Fig16 | Native GID399-style stacked-column structure and readback route exist | Frozen regression identity plus same-run visual gates | Validated regression capability, not a universal reproduction claim |
| Generic single-line figure | Native Worksheet-backed line builder with save/reopen/binding/export gates | Worker route has offline protocol tests; each delivery still requires a licensed live Origin run | Editable line capability, not an automatic fidelity guarantee |

Details are in [the AA2195 benchmark contract](references/aa2195-benchmark.md).

## Requirements

Offline development and tests:

- Windows, Linux, or macOS;
- Python 3.10;
- packages in `requirements-core.txt` and `requirements-dev.txt`.

Live Origin execution additionally requires:

- Windows and a licensed Origin 2022 installation;
- Python 3.10 with `originpro` available;
- Origin-provided `OriginExt` where the active adapter requires it;
- an administrator-started visible Origin instance for the formal attach route.

Quick/Standard planning remains non-administrator; their dedicated Origin worker is elevated for attach, build, save, reopen, readback, and export. Release retains the continuous elevated envelope from preflight through evidence cleanup. Offline tests and CI do not launch Origin and therefore do not require administrator privilege.

`OriginExt` is supplied by the Origin environment and is not represented as a normal cross-platform PyPI dependency.

## Install dependencies

Offline development:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-core.txt -r requirements-dev.txt
```

Live Origin support:

```powershell
.\.venv\Scripts\python -m pip install -r requirements-origin.txt
```

Confirm that the selected interpreter can import the Origin modules before a live run. Do not replace Origin's licensed runtime with mocked modules for E2E claims.

## Install as a Codex skill

```powershell
git clone https://github.com/peterbruce716-art/originplot-skill.git
Copy-Item .\originplot-skill "$env:USERPROFILE\.codex\skills\originplot-skill" -Recurse
```

The directory name matches the repository package and the Skill front matter name is `originplot`. To update, replace the installed directory only after validating the new package; preserve any user-owned candidates outside the skill directory.

Minimal Codex request:

```text
Use originplot to validate an editable Origin reconstruction from this FigureSpec. Keep dry-run and live evidence separate.
```

## Candidate CLI

Legacy-compatible AA2195 dry-run:

```powershell
python scripts/origin_candidate_worker.py --figure fig12 `
  --candidate examples/candidates/fig12.json `
  --output-dir outputs/fig12-plan --dry-run
```

Formal live run:

```powershell
python scripts/origin_candidate_worker.py --figure fig15 `
  --candidate path\to\fig15-candidate-with-source.json `
  --output-dir outputs/fig15-live --live --require-live-success
```

Five-figure live run with a fresh PDF extraction:

```powershell
.\scripts\run_five_figure_live_batch.ps1 `
  -OutputRoot outputs\aa2195-fresh `
  -SourceDataPolicy fresh_extract `
  -SourcePdf path\to\paper.pdf `
  -LaunchOriginExe path\to\Origin64.exe
```

If the request says to reproduce again or not use old data, this fresh route is mandatory: use the original PDF and a new or empty output root, and do not substitute either validated reuse mode. `-LaunchOriginExe` is the preferred elevated workflow when an empty Origin window may auto-hide: the runner completes same-run PDF extraction first, rejects every pre-existing visible or hidden Origin process, starts one Origin instance, and attaches immediately. The generated source manifest must be same-run, declare `fresh_extraction=true`, and contain no parent or reuse lineage.

Reuse scientific data from a prior promoted batch whose reproduction already passed:

```powershell
.\scripts\run_five_figure_live_batch.ps1 `
  -OutputRoot outputs\aa2195-reuse `
  -SourceDataPolicy validated_reuse `
  -ReuseBatchRoot outputs\prior-promoted-batch
```

The reuse route is limited to hash-verified curves, markers, error bars, fields, bar segments, and source crops. It validates the prior batch before Origin attach, then builds new Worksheets and OPJUs and repeats save/reopen/readback/export/visual QA. It never promotes copied OPJUs, exports, readbacks, or old metrics.

To apply the corrected Fig14 extraction without reopening the PDF, use the same command with `-SourceDataPolicy validated_crop_reextract`. This lineage route re-extracts Fig14 from its promoted source crop and fails if any other figure data hash changes.

Registry-based public demo:

```powershell
python examples/public_demo/generate_source.py --output-dir "$env:TEMP\originplot-public-demo"
python scripts/origin_candidate_worker.py --builder generic_line `
  --figure-spec examples/public_demo/figure_spec.json `
  --candidate examples/public_demo/candidate.json `
  --output-dir "$env:TEMP\originplot-public-demo\plan" --dry-run
```

With no mode flag, the worker retains the legacy default of dry-run and prints a notice. `--dry-run` and `--live` are mutually exclusive. `--require-live-success` returns nonzero unless a live run reaches pass eligibility.

Paper-like candidates must set `template_search_record`. The packaged Fig12/Fig15/Fig16 examples use `examples/template_search/aa2195_official_template_search.json`, a sanitized metadata record that remains inside the open-source ZIP. It records all four required official entrances:

- `https://www.originlab.com/www/products/GraphGallery.aspx?s=0&sort=Newest`
- `https://docs.originlab.com/zh/`
- `https://www.originlab.com/videos/index.aspx?CID=11`
- `https://docs.originlab.com/quick-help/graphing/zh/`

Before construction, search those entrances plus the local official catalog and installed Origin templates. Inspect every downloaded Graph Gallery project in the visible administrator Origin instance:

```powershell
python scripts/inspect_official_templates.py `
  --manifest path\to\originlab_official_template_manifest.json `
  --project-root path\to\workspace `
  --output outputs\official-template-inspection.json
```

The report records project and archive hashes, compatible open status, workbook rows, graph layers, Plot types, and direct data bindings. Sanitize that evidence into the candidate's template-search record without copying machine paths or licensed assets. A successful download alone is not template acceptance. Missing or incomplete records fail with `E130_TEMPLATE_SEARCH_REQUIRED` before Origin import or construction.

The packaged AA2195 candidate files are parameter examples and intentionally do not redistribute paper source images. During packaging, every AA2195 `source_crop` is replaced by `AUTHORIZED_LOCAL_SOURCE_REQUIRED`; supply an authorized local path before a live benchmark run. The validator rejects candidate-source rasters in a shareable archive.
If the placeholder reaches a live worker, execution stops before Origin attach with `E124_AUTHORIZED_SOURCE_REQUIRED` and no live evidence is produced.

For Fig12 parameter screening before a live run:

```powershell
python scripts/rank_fig12_matrix_candidates.py `
  --source-crop path\to\authorized-fig12-crop.png `
  --nx 40 --ny 41 --boundary-tolerance-px 2 `
  --json-out outputs\fig12-offline-ranking.json
```

The ranker reports palette accuracy, exact boundary F1, and tolerant boundary F1. Its output only shortlists candidates; it is not live Origin evidence and does not authorize changing the promoted defaults.

To diagnose how a historical Origin export responded to one shortlisted matrix, use:

```powershell
python scripts/calibrate_fig12_origin_response.py `
  --candidate path\to\fig12-candidate.json `
  --source-crop path\to\authorized-fig12-crop.png `
  --origin-export path\to\historical-origin-export.png `
  --json-out outputs\fig12-origin-response.json
```

This calibration is inherited diagnostic evidence only. Promotion still requires a same-run administrator-Origin build, save, reopen, exact contour-level and XYZ readback, and pre/post visual pass.

## Verification levels

Candidate manifests separate `command_success`, `structure_pass`, `visual_pass`, `live_origin_verified`, `pass_eligible`, and `overall_status`. Dry-run can validate a plan and exit zero, but it reports `planned_not_executed`; it never reports visual or live success.

Offline CI validates contracts, schemas, tests, packaging, and non-Origin logic. Live Origin E2E requires a licensed Windows self-hosted runner or a local authorized Origin environment.

## Tests

```powershell
python -m compileall .
python -m pytest -q
python scripts/run_all_tests.py
python scripts/audit_dependencies.py
python scripts/validate_public_evidence_index.py references/aa2195-release-evidence.json
python scripts/build_shareable_package.py --skill-dir . --zip-out "$env:TEMP\originplot-skill-v5.9.0.zip"
python scripts/validate_shareable_package_v5.py --path "$env:TEMP\originplot-skill-v5.9.0.zip"
```

None of these offline commands proves live Origin E2E.

## Add a builder

Implement the interface in `builders/base.py`, register a unique ID through `builders/registry.py`, validate the FigureSpec/candidate relationship, and add behavior tests. Registry entries must not silently replace existing IDs. The focused generic-line worker supports one Worksheet-backed line plot in Quick/Standard; it has offline protocol tests but no licensed-Origin E2E evidence and makes no release claim.

The legacy `--figure fig12|fig15|fig16` options remain supported and resolve through the same registry.

## Packaging and assets

The shareable archive includes code, docs, schemas, requirements, CI configuration, and rebuildable synthetic demo sources. It excludes generated outputs, caches, virtual environments, `site-packages`, local interpreters, OPJUs, raster evidence, spreadsheets, private data, and commercial templates. Its public AA2195 evidence JSON is a maintainer-attested hash-and-metric index, not an independently reproducible pixel-evidence bundle; index validation cannot set live or pass-eligible status.

Code and repository-authored documentation are MIT licensed. Origin, OriginPro, Graph Gallery projects, paper figures, and user-provided assets retain their respective rights and are not redistributed here.

## Known limitations

- Live automation is tied to Origin 2022 behavior and a licensed Windows environment.
- Fig3 and Fig12 are source-calibrated reconstructions; their claims do not imply exact recovery of unprovided raw data. Fig16 claims apply only to its frozen regression identity and same-run evidence.
- Fig12 contour data remains backed by native XYZ Worksheet plots. Plain `draw -paths objName SVGPath` creates editable type-34 overlay objects; each overlay now uses a unique cleaned temporary directory and must pass post-reopen type-34 plus X/Y/DX/DY geometry checks. The canonical Origin 2022 run passed every strict visual gate (MAE 0.035472, SSIM 0.801507, layout 0.992431, edge 0.745290, color 0.977127), but edge is explicitly reported as near-threshold and is not a cross-machine portability claim.
- Fig15's frozen regression evidence does not generalize to arbitrary dual-panel schematics.
- A generic registry reduces hard-coding; it does not remove the need for figure-specific engineering and validation.
- The source tree retains legacy V4 migration tools, but p18 execution and shareable packaging use V5 contracts.
