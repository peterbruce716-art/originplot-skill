# OriginPlot Skill v6.1 Release Gate

## Purpose

This document defines the final quality gate before creating the v6.1 release candidate.

## Architecture Checks

- [ ] Semantic layer remains separated from execution.
- [ ] FigureSpec to OperationPlan flow remains stable.
- [ ] Adapter layer does not contain scientific interpretation.
- [ ] Runtime package does not depend on development-only assets.

## Test Requirements

Required checks:

```text
Contract tests
Capability tests
Fail-closed tests
Package boundary tests
```

## CI Requirements

Required automated checks:

```text
ruff check
ruff format --check
pytest
package import validation
```

## Release Criteria

A release candidate can be created only when:

- All CI checks pass.
- Unsupported behavior fails explicitly.
- Capability claims match verification level.
- Documentation matches implementation.

## Post Release

After v6.1.0-rc1 validation:

```text
rc1
 |
 PR review
 |
 merge main
 |
 tag v6.1.0
```
