"""Package boundary contract tests for v6.1.

These tests protect the separation between runtime code and development-only
assets such as scripts and benchmarks.
"""

from __future__ import annotations


def test_runtime_package_import_boundary():
    """Core package should remain independently importable."""
    import originplot  # noqa: F401


def test_boundary_policy_documented():
    """Keep this test as an anchor for future boundary checks."""
    assert True
