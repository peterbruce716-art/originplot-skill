# Visual QA

Visual acceptance follows structure gates. A blank or structurally invalid export is rejected before MAE, SSIM, registration, layout, color, or ROI scoring.

The correction loop is bounded:

```text
validate -> apply -> clean rebuild -> save/reopen -> evaluate -> promote or roll back
```

Each candidate has a unique effective-parameter fingerprint. Identical consecutive export, metric, and readback signatures stop with `E510_NO_IMPROVEMENT`.

Promotion requires same-run evidence and benchmark-specific thresholds. Record the source crop identity, canvas size, effective builder route, render fingerprint, visual metrics, semantic inventory, and blocking deviations. `demo_cyan_ratio` and unexpected large fill components are hard QA checks where applicable.

Never describe a figure as closer than a baseline unless the current same-run metrics improve the declared comparator. A visual-looking Python image is not Origin evidence. A copied OPJU or prior export remains `inherited_diagnostic`.
