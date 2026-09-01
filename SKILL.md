---
name: originplot
description: "AI workflow for auditable Origin/OriginPro scientific plotting. Inspect scientific tables, resolve semantic roles, create FigureSpec, compile OperationPlan, and execute verified editable Origin workflows when supported."
---

# OriginPlot Skill v6.1.2

## Purpose

Convert scientific tables into auditable editable Origin workflows.

Pipeline:

```text
Input data
 -> semantic inspection
 -> FigureSpec v6
 -> OperationPlan
 -> Origin adapter
 -> verification
```

Keep these layers separate:

- scientific meaning
- plotting specification
- execution
- evidence

## Agent workflow

Always follow:

1. Inspect source data.
2. Resolve column semantics.
3. Create/validate FigureSpec.
4. Compile OperationPlan.
5. Check capability maturity.
6. Execute only supported Origin actions.
7. Verify the final artifact.

Do not skip validation stages.

## Completion gates

A figure is complete only when applicable checks pass:

```text
semantic_valid
 -> spec_valid
 -> plan_valid
 -> adapter_supported
 -> verified_result
```

Preview output, dry-run output, or screenshots are not proof of an editable Origin result.

## Scientific safety rules

Never:

- guess ambiguous scientific meaning;
- modify source data silently;
- smooth, normalize, fit, remove outliers, or derive quantities without instruction;
- claim unsupported Origin features executed;
- weaken validation to obtain successful-looking output.

`uncertain` means unresolved information.

## Semantic roles

Supported roles:

```text
x x_error y y_error z group category label support retain uncertain
```

Source data is immutable.

## Primitive policy

Prefer existing primitives:

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

Extend with semantic/style presets before creating new plotting engines.

A new primitive requires evidence that existing primitives cannot express the scientific intent.

## Capability boundary

Keep separate:

```text
planning support
!=
native execution
!=
verified evidence
```

Registered capability does not imply live Origin support.

`heatmap` and `multi_panel` require proven native support before promotion.

## Builder and adapter rules

Builders create plans:

```text
FigureSpec -> OperationPlan
```

Builders must never call Origin directly.

Only adapters translate plans into native Origin actions.

Unknown operations fail closed.

## Style rules

Only executable style fields enter applied output:

```text
series color
series line_color
series line_width_pt
series symbol
legend visibility
legend frame
```

Unsupported styles belong in audit information.

## Verification

A verified Origin deliverable requires:

1. authorized Origin worker;
2. native worksheet-backed graph;
3. save OPJU;
4. detach;
5. reopen;
6. binding readback;
7. Origin export;
8. output validation.

## Profiles

Quick: routine editable plotting.

Standard: scientific workflows with bounded assistance.

Release: strict evidence-required mode.

## Commands

```powershell
originplot.cmd doctor --origin-version 2022
originplot.cmd inspect data.xlsx
originplot.cmd plan data.xlsx --plot-type line --x X --y Y
originplot.cmd render figure.json
originplot.cmd verify output
```

## Failure classification

Classify failures in order:

1. semantic mapping
2. FigureSpec validation
3. OperationPlan compilation
4. Origin adapter execution
5. verification

Never hide failures behind visual output.

## Further documentation

- `docs/AGENT_QUICKSTART.md`
- `docs/CAPABILITY_MATRIX.md`
- `docs/DEVELOPMENT_GUIDE_v6.1.md`
