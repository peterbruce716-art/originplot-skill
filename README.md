# OriginPlot Skill v5.8.9-p13

OriginPlot builds editable Origin/OriginPro projects and verifies the saved,
reopened OPJU rather than accepting a look-alike raster export. The packaged
AA2195 examples reproduce Fig12, Fig15, and Fig16 with native
Worksheet-to-Plot bindings and a global limit of 5,000 source rows per figure.

## Requirements

- Windows with a licensed Origin 2022 installation
- Python 3.10 with `originpro`
- An administrator-started, visible Origin instance for authorized attachment

No local Python interpreter, Origin executable, source image, OPJU, or generated
output is bundled in the release archive.

## Portable paths

Candidate JSON files may use absolute paths, but relative `source_crop` paths
are recommended. They are resolved in this order: candidate JSON directory,
optional `project_root`, current directory, skill directory, then its parent.
This makes a candidate folder relocatable as a unit.

Place source crops beside the examples as follows:

```text
examples/candidates/
  fig12.json
  fig15.json
  fig16.json
  source/
    fig12_source_canonical.png
    fig15_source.png
    fig16_source.png
```

Run a live rebuild from the skill root:

```powershell
python scripts/origin_candidate_worker.py --figure fig12 `
  --candidate examples/candidates/fig12.json `
  --output-dir outputs/fig12 --live
```

The worker always releases its Origin session in `finally`: attached sessions
use `op.detach()`, while worker-owned hidden sessions use `op.exit()`.

## Verification

```powershell
python scripts/run_all_tests.py
python scripts/build_shareable_package.py --skill-dir . --zip-out originplot-skill.zip
python scripts/validate_shareable_package_v5.py --path originplot-skill.zip
```

Fig16 uses the verified Origin Graph Gallery GID399 stacked-column route with
GID1652 layout conventions. Official templates are reference material; they
must be downloaded and validated locally under their applicable OriginLab terms.

## License

Code and documentation in this repository are available under the MIT License.
Origin, OriginPro, Graph Gallery assets, and user-provided source figures remain
the property of their respective owners and are not included.
