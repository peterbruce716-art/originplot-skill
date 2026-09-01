# OriginPlot v6.1 Test Layout

This directory documents the quality gates for the v6.1 optimization line.

## Test layers

### contract

Protect stable interfaces:

- FigureSpec serialization
- OperationPlan schema
- primitive registry contracts

### capability

Verify that declared support is separated into:

- planning support
- compile support
- live Origin evidence

### fail_closed

Ensure unsupported requests stop explicitly:

- unknown operations
- unsupported styles
- ambiguous semantic mappings

### package_boundary

Prevent architecture drift:

- runtime must not depend on development scripts
- benchmark code must not leak into product core
- installed package must contain required runtime assets

The test suite should preserve the v6 principle:

```
explicit failure > silent incorrect success
```
