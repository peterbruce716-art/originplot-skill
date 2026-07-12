# Troubleshooting

- `E120_ENVIRONMENT_MISMATCH`: use administrator Python 3.10 on Windows and verify the Origin-side Python modules.
- `E121_ATTACH_POLICY_VIOLATION`: start a visible Origin instance as administrator before a formal run.
- Locked OPJU: close the project, check the exact `.lck`, and inspect residual hidden Origin processes before retrying. Never batch-delete files.
- Modal or demo watermark: resolve licensing or the dialog; do not treat the export as a pass.
- Zero plot readback: compare `plot_list()` with `layer -c`, activate the layer, and inspect the live binding chain.
- Blank export: reject before visual scoring; verify page/layer units, visibility, data ranges, and post-reopen export.
- Two identical correction iterations: stop with `E510_NO_IMPROVEMENT` and inspect the dominant mismatch rather than changing unrelated parameters.
- Fig16 excess dark-blue pixels: inspect group-frame width before changing bar colors.
- Fig16 H/S overlap: calibrate the affected stage locally; do not apply a global shift that damages other stages.
