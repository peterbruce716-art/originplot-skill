# OriginPlot v6.1 Test Strategy

## Purpose

The test system protects the v6 architecture boundaries while allowing new plotting capabilities to evolve safely.

## Test layers

### 1. Contract tests

Validate stable interfaces:

- FigureSpec schema compatibility
- OperationPlan schema compatibility
- primitive identifiers
- metadata preservation

A valid object must remain valid after serialization and loading.

### 2. Capability tests

Validate that advertised capability matches reality:

- planning support is separated from native Origin execution;
- compile support is separated from live evidence;
- blocked primitives fail before entering unsupported live paths.

### 3. Fail-closed tests

Invalid behavior must stop explicitly:

- unknown OperationPlan actions;
- unsupported style fields;
- ambiguous semantic mappings;
- unavailable Origin capabilities.

Failure is preferred over silent scientific corruption.

### 4. Package boundary tests

Ensure:

- installed runtime does not depend on repository development scripts;
- benchmark modules remain isolated from ordinary product imports;
- runtime assets resolve consistently.

## Release gate

Before v6.1 release:

1. documentation contracts updated;
2. tests pass offline;
3. live Origin verification is only claimed when native gates pass;
4. release notes describe verified capabilities only.
