# Standard Profile

Use Standard by default for publication figures, reference-guided reconstruction, and normal SCI delivery.

## Defaults

- `template_policy=auto`
- `evidence_level=visual`
- `reopen_check=basic`
- `visual_qa=basic`
- `max_template_candidates=3`
- `max_rebuild_attempts=1`

Run every Quick live gate. Search local templates first, then make at most one bounded Gallery search when useful. Evaluate no more than the configured candidate count. Fall back to a native builder when no reusable candidate is found or retrieval fails.

When a reference exists, register it before comparison and report nonblank, alignment, MAE, SSIM, layout, edge/foreground, and Demo checks when available. Stop after the bounded rebuild count or when the score does not improve.

Return `live_structure_pass` or `live_visual_pass`. Keep `pass_eligible=false`; Standard evidence is not a release package.
