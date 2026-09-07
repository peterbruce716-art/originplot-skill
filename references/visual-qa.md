# Visual QA

Visual acceptance follows structure gates. A blank or structurally invalid export is rejected before MAE, SSIM, registration, layout, color, or ROI scoring.

The correction loop is bounded:

```text
validate -> apply -> clean rebuild -> save/reopen -> evaluate -> promote or roll back
```

Each candidate has a unique effective-parameter fingerprint. Identical consecutive export, metric, and readback signatures stop with `E510_NO_IMPROVEMENT`.

Promotion requires same-run evidence and benchmark-specific thresholds. Record the source crop identity, canvas size, effective builder route, render fingerprint, visual metrics, semantic inventory, and blocking deviations. `demo_cyan_ratio` and unexpected large fill components are hard QA checks where applicable.

For Fig3, Fig12, Fig14, Fig15, and Fig16, global MAE/SSIM are necessary but insufficient because white page area can dominate them. The target gate also requires registration-normalized `foreground_f1`, `edge_f1`, and a figure-specific `nonwhite_delta`. Registration for overlap scoring uses only the already-reported content-bbox translation; the independent registration gate still blocks excessive displacement. Missing overlap metrics fail closed.

The target gate records signed `gate_margins` in metric units and `gate_headroom_fractions` as a fraction of each gate's own budget (`1 - threshold` for a `min` gate, the threshold itself for a `max` gate). A passing metric appears in `near_threshold_metrics` when its margin is below 0.001 **or** its headroom is below 10% of that budget. The relative test exists because one absolute margin cannot describe gates whose units differ by orders of magnitude: `mae_0_1` and `ssim_score` live on 0..1, `registration_abs_dx_px` allows up to 16 px, and `fig16_bar_boundary_missing_segments` is a zero-tolerance count. Under the margin-only rule Fig12 `edge_score` sat 0.41% of its budget from failing and was still reported as safe. Disclose every near-threshold metric and rerun live validation for a different Origin build, export profile, or machine. Do not lower thresholds to manufacture margin.

Fig12 and Fig14 have same-run promoted source-calibrated baselines. Fig15 and Fig16 are frozen-regression routes, and Fig3 retains its promoted approximate-reconstruction gate. Passing scalar metrics alone is insufficient: the same-run render identity must match the declared source hash, effective route, geometry version, Origin version, and export profile. A promoted source-calibrated route is still not a claim of raw-data recovery or pixel identity. For Fig14, same-x legend symbols and neighboring series must be excluded during marker/error-bar digitization; a marker that hides one side of an error bar is measured from its center to the largest visible local extent.

Never describe a figure as closer than a baseline unless the current same-run metrics improve the declared comparator. A visual-looking Python image is not Origin evidence. A copied OPJU or prior export remains `inherited_diagnostic`.
