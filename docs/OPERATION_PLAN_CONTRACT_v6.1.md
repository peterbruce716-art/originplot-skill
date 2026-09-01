# OriginPlot v6.1 OperationPlan Contract

## Purpose

OperationPlan is the stable boundary between plot compilation and Origin execution.

```text
FigureSpec
    |
    v
OperationPlan
    |
    v
Origin adapter
```

Builders create plans. Adapters execute plans. They must not be mixed.

## Contract rules

1. Every plan declares `originplot.operation_plan.v1` schema.
2. Unknown schemas fail immediately.
3. Operations are declarative actions, not arbitrary Origin code.
4. Adapter execution must reject unknown actions before creating output.
5. A successful compilation is not live Origin verification.

## Validation layers

- schema validation: structure is valid
- semantic validation: requested operation has scientific meaning
- capability validation: target primitive is supported
- live validation: Origin lifecycle and editability gates pass

## Agent rule

Never add Origin API calls to builders. Never bypass OperationPlan to make a feature appear supported.
