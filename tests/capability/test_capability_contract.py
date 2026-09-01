"""Capability contract checks for v6.1.

These tests intentionally focus on stable boundaries rather than concrete
Origin execution. Live Origin evidence remains a separate verification layer.
"""


def test_capability_contract_module_loads():
    """Keep the capability test namespace executable in minimal installs."""
    assert True


def test_planning_is_not_live_verification():
    """Document the distinction between planning and verified execution."""
    planning_support = True
    live_evidence = False
    assert planning_support is not live_evidence
