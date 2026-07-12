# Public synthetic line demo

This example is generated entirely from repository-authored formulas and contains no paper image, private data, or commercial Origin template. It demonstrates registry resolution, FigureSpec validation, candidate planning, and honest dry-run status.

```powershell
python examples/public_demo/generate_source.py --output-dir "$env:TEMP\originplot-public-demo"
python scripts/origin_candidate_worker.py --builder generic_line `
  --figure-spec examples/public_demo/figure_spec.json `
  --candidate examples/public_demo/candidate.json `
  --output-dir "$env:TEMP\originplot-public-demo\plan" --dry-run
```

The generated CSV and PNG are disposable demo outputs and are not packaged. The current `generic_line` entry has no promoted live Origin implementation, so a `--live` request fails closed with `E440_PLOT_FAMILY_NOT_IMPLEMENTED`.
