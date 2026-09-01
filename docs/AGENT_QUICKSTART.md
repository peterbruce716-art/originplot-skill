# OriginPlot Agent Quickstart

## Purpose

This document is the compact entry point for AI agents using OriginPlot. It intentionally does not replace `SKILL.md`; it provides the shortest reliable execution path.

## Decision flow

```text
Input scientific table
        |
        v
inspect columns and metadata
        |
        v
resolve semantic roles
        |
        v
create FigureSpec v6
        |
        v
compile OperationPlan
        |
        v
execute native Origin lifecycle when capability allows
        |
        v
verify save/reopen/binding/export
```

## Agent rules

1. Never infer scientific meaning from column names alone when ambiguity exists.
2. Never modify source data silently.
3. Never claim Origin execution from a dry-run or compile-only result.
4. Treat unsupported style fields as rejected, not partially applied.
5. Separate planning failures from Origin runtime failures.

## Error handling priority

When a run fails:

1. Check semantic mapping.
2. Check FigureSpec validity.
3. Check OperationPlan actions.
4. Check Origin adapter capability.
5. Check live verification gates.

Do not bypass validation to force a successful-looking figure.

## Minimal commands

```powershell
originplot.cmd doctor --origin-version 2022
originplot.cmd inspect data.xlsx
originplot.cmd plan data.xlsx --plot-type line --x X --y Y
originplot.cmd render figure.json --dry-run
originplot.cmd verify output
```

## Design principle

Prefer fewer deterministic capabilities over many approximate ones. A rejected unsupported operation is safer than an unverifiable scientific figure.
