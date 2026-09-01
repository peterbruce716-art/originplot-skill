# OriginPlot v6.1 Architecture Audit

## Purpose

This checklist keeps the v6.1 refactor focused on reliability rather than feature accumulation.

## Layer boundaries

```text
semantic
   -> FigureSpec
   -> builders
   -> OperationPlan
   -> adapter
   -> verification
```

Each layer should have one responsibility:

- semantic: understand column roles, never perform scientific interpretation;
- spec: define a frozen executable contract;
- builders: compile specifications only;
- OperationPlan: remain declarative;
- adapter: translate only validated operations into Origin calls;
- verification: prove the delivered artifact state.

## Forbidden regressions

- Builders importing Origin APIs.
- Adapters modifying scientific input data.
- Silent fallback from unsupported features.
- Treating compile success as live Origin evidence.
- Adding domain-specific plotting engines when a primitive plus preset is sufficient.

## Review checklist

### Builders

- Can the workflow compile to an existing primitive?
- Are unsupported mappings rejected explicitly?
- Is output deterministic for identical FigureSpec input?

### Adapter

- Are unknown operations rejected?
- Are Origin lifecycle failures reported with context?
- Are save/reopen/readback gates preserved?

### Runtime

- Are profiles loaded from package-owned locations?
- Is the worker lifecycle isolated?
- Are environment checks separate from evidence claims?

### Tests

Required coverage should include:

- schema validation;
- invalid operation rejection;
- capability boundary checks;
- package isolation;
- fail-closed behavior.

## Release rule

A version upgrade requires evidence for the changed capability. Documentation improvements alone do not promote native Origin evidence.
