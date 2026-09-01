# Fail-closed Tests v6.1

## Purpose

Protect OriginPlot from silently accepting unsupported or ambiguous requests.

## Covered cases

- Unknown operations
- Unsupported primitives
- Missing required metadata
- Invalid capability declarations
- Ambiguous execution states

## Expected behavior

Unsupported states must produce explicit diagnostics rather than degraded or misleading output.

## Rule

Explicit rejection is preferred over silent fallback.
