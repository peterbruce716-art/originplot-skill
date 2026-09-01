# OriginPlot v6.1 Development Guide

## Engineering objective

Keep OriginPlot deterministic, auditable, and safe for scientific workflows.

The project is not optimized for generating the most plots. It is optimized for producing plots whose meaning, construction path, and editability can be verified.

## Layer ownership

```
scientific input
    |
semantic inspection
    |
FigureSpec
    |
Builder
    |
OperationPlan
    |
Origin adapter
    |
verification
```

Each layer has one responsibility:

- Semantic layer: understand data roles.
- FigureSpec: freeze user intent.
- Builder: compile intent into operations.
- Adapter: communicate with Origin.
- Verification: prove the result.

## Contribution rules

### Add a primitive only when necessary

Before adding a new plot type:

1. Check whether an existing primitive can represent the workflow.
2. Prefer semantic presets over new engines.
3. Require verification strategy before implementation.

### Never hide unsupported behavior

Unsupported features must be:

- rejected,
- reported,
- or explicitly marked as unavailable.

Never silently downgrade scientific intent.

## Testing expectations

Changes should consider:

- schema compatibility;
- builder contracts;
- OperationPlan validity;
- package boundaries;
- verification behavior.

Offline success does not prove licensed Origin execution.

## Agent maintenance rule

When modifying the repository:

1. Read the relevant contract first.
2. Make the smallest correct change.
3. Preserve fail-closed behavior.
4. Update documentation when behavior changes.
