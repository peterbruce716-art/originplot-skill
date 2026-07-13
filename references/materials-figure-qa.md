# Materials and EBSD Figure QA

Read this file only for materials-science, microstructure, or EBSD figures.

## Semantic separation

- Treat IPF as crystallographic orientation evidence, not a recrystallization
  classifier by itself.
- Treat KAM as a local orientation-gradient proxy. Lower KAM is consistent with
  lower local lattice curvature and stored dislocation density, but does not by
  itself prove recrystallization.
- Treat GOS as a grain-scale internal-misorientation metric. Describe a threshold
  such as GOS below 2 degrees as `recrystallized-like` or a low-internal-
  misorientation state unless independent evidence supports a stronger claim.
- Report LAGB and HAGB using the stated misorientation thresholds. Do not infer
  boundary migration from HAGB fraction alone.
- Keep recrystallized fraction definitions tied to the exact classifier,
  cleanup, grain reconstruction, and threshold settings.

## Mechanism claims

Discuss CDRX or DDRX only by combining relevant evidence: grain-size evolution,
subgrain rotation, boundary character change, HAGB development, boundary
migration, and new-grain morphology. Phrase associations as correlations or
consistency unless the experiment establishes causality.

## Panel and source checks

- Use the same field of view for panels that invite pixel- or region-level
  comparison, or mark mismatched fields explicitly.
- Keep scale bars calibrated, visible, and consistent with the mapped data.
- Preserve orientation/color keys and numeric color-bar limits after Origin
  reopen; do not rely on a screenshot as the legend source.
- Record step size, cleanup, grain reconstruction, minimum grain size, boundary
  thresholds, KAM kernel/neighborhood, and excluded wild spikes when they affect
  interpretation.
- Bind map-derived statistics to the corresponding source table and region ID.
- Report sample count separately from pixel, point, or grain count.
- Use uncertainty across independent specimens when making population claims;
  do not treat thousands of pixels or grains from one field as independent
  biological/material replicates.

## Final claim audit

For each claim, record the supporting panel, metric definition, sample basis,
and plausible alternative interpretation. Downgrade wording when the figure
shows spatial association without temporal or intervention evidence.
