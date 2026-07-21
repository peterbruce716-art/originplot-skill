# Workflow Migration

Legacy `origin_candidate_worker.py` commands remain supported and retain strict p18 behavior. New work should call `scripts/originplot.py`.

| Old route | New route |
| --- | --- |
| Generic dry-run | `originplot.py --profile standard --dry-run` |
| Routine editable plot | `originplot.py --profile quick --live` |
| SCI reconstruction | `originplot.py --profile standard --live` |
| AA2195 strict run | `originplot.py --profile release --live` |
| Five-figure batch | unchanged script; internally mapped to `release` |

The new controller owns profile resolution, template policy, evidence selection, task serialization, and status normalization. The administrator worker owns only Origin operations. The legacy strict worker remains the Release adapter; historical evidence and migration tools are not modified.
