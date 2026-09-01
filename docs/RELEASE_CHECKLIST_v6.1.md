# OriginPlot v6.1 Release Readiness Checklist

This checklist defines the final gate before merging the v6.1 optimization branch.

## Architecture

- [ ] Semantic inspection remains separate from plotting compilation.
- [ ] Builders only compile FigureSpec into OperationPlan.
- [ ] Origin adapters remain the only native execution boundary.
- [ ] Verification reports only evidence-backed results.

## Agent Safety

- [ ] Unsupported capabilities fail closed.
- [ ] Ambiguous scientific meaning requires explicit mapping.
- [ ] No silent data transformation is introduced.
- [ ] No unsupported style field is reported as applied.

## Quality Gates

- [ ] Contract tests pass.
- [ ] Capability tests pass.
- [ ] Fail-closed tests pass.
- [ ] Package boundary tests pass.

## Release Review

- [ ] README reflects v6.1 architecture.
- [ ] SKILL.md remains concise and execution-oriented.
- [ ] Changelog is updated.
- [ ] Version tags and release notes match the published state.
