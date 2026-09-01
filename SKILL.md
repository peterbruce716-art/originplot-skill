---
name: originplot
description: "AI workflow for auditable Origin/OriginPro scientific plotting. Inspect scientific tables, resolve semantic roles, create FigureSpec, compile OperationPlan, and execute verified editable Origin workflows when supported."
---

# OriginPlot Skill v6.1.1

## Identity

OriginPlot converts scientific tables into auditable editable Origin workflows.

Core pipeline:

```text
Input data
 -> semantic inspection
 -> FigureSpec v6
 -> OperationPlan
 -> Origin adapter
 -> save/reopen/readback/export verification
```

The system separates:

- scientific meaning
- plot compilation
- Origin automation
- verification

## Agent decision flow

1. Inspect the source table.
2. Resolve column roles.
3. Create or validate FigureSpec.
4. Compile OperationPlan.
5. Check capability maturity.
6. Execute Origin only when supported.
7. Verify the final editable result.

Never skip earlier stages.

## Production quality gates

Before declaring a figure complete, check:

```text
semantic_valid
 -> spec_valid
 -> plan_valid
 -> adapter_supported
 -> live_verified
```

Failure at any stage must stop promotion instead of being hidden by a preview image or partial export.

## Hard rules

Never:

- guess ambiguous scientific meaning;
- silently modify source data;
- smooth, fit, normalize, remove outliers, or calculate scientific quantities;
- claim dry-run output is an Origin result;
- claim unsupported style fields were applied;
- create duplicate plotting engines for scientific domains;
- bypass administrator or verification requirements.

`uncertain` means unresolved information, not another plotted series.

## Semantic roles

Supported roles:

```text
x
x_error
y
y_error
z
group
category
label
support
retain
uncertain
```

Source data remains immutable.

## Primitive strategy

Use existing primitives first:

```text
line
scatter
line_scatter
errorbar
bar
grouped_bar
stacked_bar
heatmap
contour
multi_panel
```

Add semantic/style presets before adding new primitives.

A new plotting engine requires proof that existing primitives cannot represent the scientific intent.

## Capability boundary

Separate:

```text
planning support
!=
native execution
!=
verified evidence
```

A registered primitive does not automatically mean live Origin support.

Special cases:

- heatmap requires proven native support;
- multi_panel requires proven native support;
- compile success is not live verification.

## Builder / adapter boundary

Builders:

```text
FigureSpec -> OperationPlan
```

Builders must not call Origin.

Only the Origin adapter translates OperationPlan into native Origin actions.

Unknown operations must fail closed.

## Style boundary

Only executable style fields may enter final style:

```text
series color
series line_color
series line_width_pt
series symbol
legend visible
legend frame
```

Unsupported style belongs in audit output, not applied output.

## Live verification

A verified Origin result requires:

1. authorized Origin worker;
2. native worksheet-backed graph;
3. save OPJU;
4. detach;
5. reopen;
6. binding readback;
7. Origin export;
8. output validation.

A screenshot, Python preview, dry-run, or intermediate save is not a verified deliverable.

## Profiles

### Quick

Routine editable plotting.

### Standard

SCI workflow with bounded assistance.

### Release

Strict fail-closed mode requiring evidence.

Historical benchmark evidence must not be relabeled as new evidence.

## Commands

```powershell
originplot.cmd doctor --origin-version 2022
originplot.cmd inspect data.xlsx
originplot.cmd plan data.xlsx --plot-type line --x X --y Y
originplot.cmd render figure.json
originplot.cmd verify output
```

## Failure handling

Classify failures in order:

1. semantic mapping
2. FigureSpec validation
3. OperationPlan compilation
4. Origin adapter execution
5. verification gates

Do not force successful-looking output by weakening validation.

## References

Detailed material:

- `docs/AGENT_QUICKSTART.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/DEVELOPMENT_GUIDE_v6.1.md`
