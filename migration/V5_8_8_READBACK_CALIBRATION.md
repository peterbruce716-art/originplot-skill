# OriginPlot v5.8.7-p2 to v5.8.8

## Scope

This patch closes Origin 2022 readback and calibration gaps. It does not retune Fig12, Fig15, or Fig16 visual parameters and does not overwrite run132 evidence.

## Changes

- Inspection now treats `GLayer.plot_list()` as authoritative and cross-checks LabTalk `layer -c` through the `count` variable.
- Plot and GraphObject readback include object-level details and disagreement reporting.
- Calibration creates independent plot, GraphObject, text, coordinate, and contour-palette probes, saves an OPJU, exits Origin, and uses a new inspection worker for post-reopen evidence.
- Pre-save-only evidence cannot pass any calibration gate.
- AA2195 candidate builders are packaged under `builders/aa2195`; the candidate worker no longer requires a workspace-relative script or undocumented environment variable.
- `pytest.ini` uses importlib collection so plain pytest works alongside the packaged unittest runner.

## Validation

Run from the installed skill directory:

```powershell
python scripts\run_all_tests.py
python -m pytest --collect-only -q
```

Live Origin 2022 probe, from an administrator terminal:

```powershell
python scripts\origin_calibration_probe.py --live --output outputs\originplot_v588_calibration_probe.json
```

The live probe owns hidden Origin sessions and releases them with `op.exit()` in `finally` paths.

## Verified Results

- Packaged runner: 32 tests, 0 failures, 0 skips.
- Plain pytest collection: 32 tests collected successfully.
- Origin 2022 live calibration: all five probe families verified and `pass_eligible=true`.
- Post-reopen plot counts: one line 1, two lines 2, matrix contour 1, column 1.
- Named GraphObjects: rectangle, line, text, and circle all found after reopen.
- Three-region palette IoU: orange 0.950, green 0.948, blue 0.965; no dominant purple or default red; palette stable after reopen.
- Packaged Fig15 candidate worker: created and reopened a real OPJU, exported PNG, and emitted all five required candidate artifacts without a workspace-relative builder.
