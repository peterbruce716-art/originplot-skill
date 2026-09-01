# OriginPlot Skill v6.1 Final Audit

## Purpose

Final audit checklist before opening the v6.1.0-rc1 pull request.

## Architecture

- [ ] Semantic planning remains separated from execution.
- [ ] FigureSpec -> OperationPlan contract remains stable.
- [ ] Adapter layer only performs translation.
- [ ] Runtime dependencies remain isolated.

## Reliability

- [ ] Unsupported operations fail explicitly.
- [ ] Capability claims match verification level.
- [ ] Diagnostics are available for rejected operations.

## Validation

Required commands:

```text
ruff check
ruff format --check
pytest
package import validation
```

## Release Outcome

After all checks pass:

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
v6.1.0 release
```
