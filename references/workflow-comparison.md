# Workflow Comparison

| Concern | Before | Quick | Standard | Release |
| --- | --- | --- | --- | --- |
| Default | Release-like | Explicit | Yes | Explicit |
| Template search | Strict for paper-like routes | Skip | Bounded auto | Strict |
| Controller admin | Often required | No | No | Existing strict envelope |
| Reopen/binding/export | Required | Required | Required | Required |
| Visual QA | Benchmark-oriented | Off | Basic | Benchmark |
| Evidence | Full | Basic | Visual | Full |
| AA2195 rules | Loaded in common path | No | Only explicit AA2195 route | Yes |
| Release eligibility | Evaluated | No | No | Yes |

The split reduces routine preflight and evidence work without changing the immutable editable-project closure or the AA2195 release gates.
