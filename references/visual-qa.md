# Visual QA

Visual acceptance follows structure gates. A blank or structurally invalid export is rejected before MAE, SSIM, registration, layout, color, or ROI scoring.

The correction loop is bounded:

```text
validate -> apply -> clean rebuild -> save/reopen -> evaluate -> promote or roll back
```

Each candidate has a unique effective-parameter fingerprint. Identical consecutive export, metric, and readback signatures stop with `E510_NO_IMPROVEMENT`.

Promotion requires same-run evidence and benchmark-specific thresholds. Record the source crop identity, canvas size, effective builder route, render fingerprint, visual metrics, semantic inventory, and blocking deviations. `demo_cyan_ratio` and unexpected large fill components are hard QA checks where applicable.

The target gate records signed `gate_margins` in metric units. Passing metrics with margin below 0.001 appear in `near_threshold_metrics`; disclose them and rerun live validation for a different Origin build, export profile, or machine. Do not lower thresholds to manufacture margin.

Fig12 and Fig14 have same-run promoted source-calibrated baselines. Fig15 and Fig16 are frozen-regression routes, and Fig3 retains its promoted approximate-reconstruction gate. Passing scalar metrics alone is insufficient: the same-run render identity must match the declared source hash, effective route, geometry version, Origin version, and export profile. A promoted source-calibrated route is still not a claim of raw-data recovery or pixel identity.

Never describe a figure as closer than a baseline unless the current same-run metrics improve the declared comparator. A visual-looking Python image is not Origin evidence. A copied OPJU or prior export remains `inherited_diagnostic`.
