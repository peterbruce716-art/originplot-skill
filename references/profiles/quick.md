# Quick Profile

Use Quick for routine native charts and rapid style iterations when the user needs an editable OPJU but no formal source-fidelity claim.

## Defaults

- `template_policy=skip`
- `evidence_level=basic`
- `reopen_check=basic`
- `visual_qa=off`
- `max_template_candidates=0`
- `max_rebuild_attempts=0`

## Required Live Gates

Save the OPJU, detach, reopen it, find the expected graph/layer/plot and Worksheet, resolve every data plot binding, export a nonblank image from reopened Origin, and reject Demo markings. Treat every other release-only gate as `not_required`.

Return `completed` only after all required live gates pass. Keep `pass_eligible=false` because Quick is not a release assessment.
