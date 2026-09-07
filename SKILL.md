---
name: originplot
description: "AI workflow for auditable Origin/OriginPro scientific plotting. Inspect scientific tables, resolve semantic roles, create FigureSpec, compile OperationPlan, and execute verified editable Origin workflows when supported."
---

# OriginPlot Skill v6.1.3

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

## Origin window visibility (mandatory)

- The Origin application window must remain visible throughout every live Origin/OriginPro operation. Never call `op.set_show(False)`, create graph pages with `hidden=True`, or launch Origin with a hidden window style.
- On this machine, use the installed Origin 2022 GUI under `C:\program\origin2022`; the live batch runner resolves an install directory or `Origin.exe` launcher to the real `Origin64.exe` GUI and starts it with `WindowStyle Normal`.
- Before every live run, the runner force-stops only confirmed `Origin*.exe -Embedding` residue and records the stopped PIDs; visible Origin window processes are never targeted by this cleanup.
- Formal attach requires exactly one visible, non-`-Embedding` Origin process with a stable PID. Any `-Embedding` process remaining after cleanup is a hard failure and must never be selected as the working Origin instance.
- Any hidden Origin process that is not confirmed -Embedding is also a hard conflict; the runner never silently leaves a hidden Origin process alongside the visible working window.
- The live runner restores and foregrounds the selected Origin main window before attach and before each figure worker, recording the window handle and presentation result in batch evidence.
- The helper Python console may be redirected or hidden; that does not hide Origin. The Origin main window, worksheets, progress state, and graph page remain user-visible.
- For a reproducible local run, pass `-LaunchOriginExe C:\program\origin2022`; the runner resolves the directory to the installed GUI and can use either `fresh_extract` or a previously validated source bundle.

- Live benchmark runs sample the actual Origin window visibility and minimized state every 500 ms during each worker. Each figure must have valid pre-worker, post-worker, and post-display window evidence; foreground focus is recorded separately because users may switch applications.
- After each figure completes, keep its Origin graph visible for 3 seconds by default (`-FigureDisplaySeconds 1..60`). Print figure progress and elapsed time; leave the final Origin window open for review.
- The runner sets `visible_window_evidence_required=true` and invokes the auditor with `--require-visible-window-evidence`. Missing or hidden/minimized window samples fail this gate. Historical audits without this new evidence must not be described as having passed the new visibility gate.
- Embedding cleanup must additionally verify the process has no main window before stopping it, preserving every window-bearing Origin process.

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
