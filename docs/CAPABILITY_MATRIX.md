# OriginPlot v6.1 Capability Matrix

This document gives agents a compact view of what can be planned, executed, and verified.

| Capability | Planning | Native Origin execution | Verification gate |
|---|---|---|---|
| line | yes | capability dependent | save/reopen/binding/export |
| scatter | yes | capability dependent | save/reopen/binding/export |
| line_scatter | yes | capability dependent | save/reopen/binding/export |
| errorbar | yes | capability dependent | save/reopen/binding/export |
| bar | yes | capability dependent | save/reopen/binding/export |
| grouped_bar | yes | capability dependent | save/reopen/binding/export |
| stacked_bar | yes | capability dependent | save/reopen/binding/export |
| heatmap | yes | blocked unless native support is proven | compile evidence only |
| contour | yes | capability dependent | native evidence required |
| multi_panel | yes | blocked unless native support is proven | compile evidence only |

## Agent decision rule

Prefer this order:

1. Use existing primitive.
2. Add semantic/style preset if the workflow is domain-specific.
3. Add a new primitive only when existing primitives cannot represent the scientific intent.

Do not create a second plotting engine for a new scientific domain.

## Failure interpretation

- Semantic failure: data meaning is unresolved.
- Compile failure: FigureSpec or OperationPlan is invalid.
- Adapter failure: Origin integration cannot execute the plan.
- Verification failure: output exists but scientific editability is not proven.
