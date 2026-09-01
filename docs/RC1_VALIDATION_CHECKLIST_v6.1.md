# OriginPlot Skill v6.1 RC1 Validation Checklist

## Purpose

Checklist for validating the v6.1 release candidate before opening the final pull request.

## Repository State

- [ ] Working tree changes are committed.
- [ ] Version metadata is consistent.
- [ ] Changelog reflects user-visible changes.

## Quality Gates

- [ ] `ruff check` passes.
- [ ] `ruff format --check` passes.
- [ ] `pytest` passes.
- [ ] Package import validation passes.

## Architecture Review

- [ ] Semantic decisions remain separated from execution.
- [ ] FigureSpec -> OperationPlan contract is unchanged.
- [ ] Adapter layer only translates execution plans.
- [ ] Unsupported operations fail explicitly.

## Release Decision

Only after all checks pass:

```text
v6.1.0-rc1
    |
    v
Pull Request
    |
    v
main merge
    |
    v
v6.1.0 tag
```
