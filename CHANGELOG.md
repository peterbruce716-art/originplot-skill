# Changelog

## 6.1.2

### Changed
- Reduced SKILL guidance duplication to improve AI context efficiency.
- Kept scientific safety rules, capability boundaries, and verification requirements explicit.
- Improved agent workflow readability for faster decision routing.

### Validation
- Existing CI validation remains authoritative:
  - ruff check
  - ruff format
  - pytest
  - package validation

## 6.1.1

### Added
- Production quality gate documentation from semantic validation through live verification.
- Clearer AI agent stop conditions to prevent promotion of partial or preview-only results.
- Stronger separation between planning support, native execution, and verified evidence.
- Package metadata synchronization with the v6.1.1 stable version.

### Changed
- Updated Skill guidance to emphasize fail-closed scientific plotting workflows.
- Improved completion criteria for editable Origin deliverables.
- Removed release-version ambiguity between documentation and Python package metadata.

### Validation
- ruff check
- ruff format --check
- pytest
- package import validation
- shareable package validation

## 6.1.0rc1

### Added
- Release candidate tracking for the v6.1 architecture hardening work.
- Explicit release validation workflow documentation.
- Stronger CI and package boundary validation.
- Clearer documentation for FigureSpec, OperationPlan, primitive maturity, and fail-closed execution boundaries.

## 6.0.0

- Initial v6 architecture release.
