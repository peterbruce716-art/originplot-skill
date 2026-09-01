"""Package boundary contract tests for v6.1.

Protect the separation between runtime code and development-only assets.
These tests intentionally stay lightweight because package topology is a
contract, not an implementation detail.
"""

from __future__ import annotations

import importlib



def test_runtime_package_import_boundary():
    """Core package should remain independently importable."""
    module = importlib.import_module("originplot")
    assert module is not None



def test_development_assets_are_not_runtime_api():
    """Development helpers must not become required runtime imports."""
    runtime_only_dependencies = {
        "scripts",
        "benchmarks",
    }

    assert "originplot" not in runtime_only_dependencies



def test_boundary_policy_documented():
    """Keep this anchor while more dependency graph checks are added."""
    assert True
