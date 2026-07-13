# Figure Contract and Style Profiles

Read this file before designing a new builder or materially restyling an existing
one. For recorded AA2195 benchmarks, `source_fidelity` is mandatory unless the
user explicitly requests a journal-restyled derivative.

## Publication contract gate

Create `originplot.publication_contract.v1` before construction. Start from
`examples/publication_contract.example.json` and run:

```powershell
python scripts/validate_publication_contract.py path\to\publication_contract.json --json-out path\to\publication_contract.validation.json
```

The contract must declare:

- one-sentence `core_conclusion` and a supported `figure_archetype`;
- `target_journal`, `style_profile`, `final_size_mm`, and current author-guide provenance when a journal-specific profile is used;
- a panel map in which every panel answers a distinct question;
- an `evidence_hierarchy` with one hero panel and explicit validation/control panels;
- source data mapped to every panel, including whether geometry is measured, computed, reconstructed, or image-derived;
- editable Origin object families and canonical source groups;
- statistics/uncertainty applicability for every quantitative or mixed panel;
- color-vision, grayscale, and non-color encoding checks;
- OPJU plus vector exports, and raster exports when raster panels are present;
- reviewer risks and separate `source_fidelity` and `publication_style` acceptance tracks.

Do not proceed to a new builder when validation fails. A valid contract plans the
work; it does not prove that a builder exists or that Origin execution passed.

## Evidence logic

Every panel must support a distinct part of the conclusion. Use one hero panel
for the primary evidence, quieter validation panels for corroboration, and
control panels only when they materially constrain interpretation. Remove a
panel if hiding it would not weaken the argument.

Keep quantitative claims traceable to Worksheet data. Label image-derived
geometry as digitized or reconstructed. For representative images, retain the
link to quantification and record scale calibration and global image processing.

## Style selection

- `source_fidelity`: reproduce the declared reference typography, palette,
  geometry, axes, line patterns, and annotation placement. Use this for
  Fig3/Fig12/Fig14/Fig15/Fig16 visual benchmarks.
- `jmpt`, `acta_materialia`, `ijp`, and `msea`: use the packaged conservative
  materials-journal house tokens, then verify the current target journal guide.
- `jmpt_acta`: compatibility alias for the earlier combined house profile.
- `nature`: use the packaged conservative Nature-style tokens, then verify the
  current Nature research figure guide.
- `custom`: supply all tokens listed in
  `assets/journal_style_profiles.json#custom.required_tokens`.

These profiles are authoring defaults, not claims about immutable journal rules.
Record the URL and check date used for final submission requirements. Treat
profiles as composable tokens, following the SciencePlots pattern. Translate
tokens to verified Origin properties; do not copy Matplotlib runtime settings.

Legends must remain editable and derive samples from actual plotted series with
Origin plot references. Do not create a legend-only Worksheet, duplicate swatch
dataset, or legend-only plot layer.

## Canonical source groups

Declare `originplot.source_geometry_groups.v1` for every data-bearing or
geometry-bearing family:

1. Give the group a stable `group_id` and one `canonical_source.source_id`.
2. Encode disjoint segments in one X/Y pair with NaN separators when Origin can
   render the required family from one plot.
3. Mark exactly one plot consumer as `view: canonical`.
4. Keep every derived plot consumer in the same reopened Workbook/Worksheet and
   record its deterministic `derivation`.
5. Use `same_columns_as_canonical: true` when the Origin plot families permit
   exact X/Y/Z reuse.
6. For a derived GraphObject, record its object name and transformation; verify
   object type and geometry after reopen.
7. Fail structure acceptance when a consumer is missing, cross-bound, or has an
   undeclared derivation.

## Publication QA

- Inspect at final physical size, not only at export zoom.
- Check editable fonts, line widths, markers, units, uncertainty definitions,
  panel labels, grayscale legibility, and color-vision accessibility.
- Use redundant line, marker, hatch, or label encodings when color carries
  scientific meaning.
- Prefer vector PDF/SVG/EPS for line art and high-resolution TIFF/PNG for raster
  panels, subject to the current target-journal guide.
- Open exported files and verify nonblank content, selectable text where
  required, embedded/available fonts, unclipped labels, and correct dimensions.
- Keep source-fidelity and publication-style acceptance independent. Never
  silently replace a benchmark route with a journal-restyled derivative.

## Design sources

This contract adapts conclusion-first figure planning and on-demand references
from `nature-skills`, Times/full-box material-figure defaults from `sci-figure`,
reusable publication checks from K-Dense scientific visualization, composable
style tokens from SciencePlots, and progressive disclosure from Anthropic
skills. The davila7 collection reinforces explicit purpose, workflow, and
validation but contributes no Origin-specific runtime claims. Origin save,
release, reopen, readback, and export remain authoritative.
