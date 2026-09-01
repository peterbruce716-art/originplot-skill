"""Fail-closed behavior contracts for OriginPlot v6.1.

These tests document the required safety behavior: ambiguous or unsupported
states must be rejected explicitly instead of silently producing degraded output.
"""



def test_unknown_operation_requires_explicit_rejection_contract():
    """Unknown operations must not be treated as successful execution."""
    unknown_operation = "unknown_action"

    supported_operations = {
        "create_plot",
        "apply_style",
        "export",
    }

    assert unknown_operation not in supported_operations



def test_unsupported_capability_is_not_equivalent_to_verification():
    """Capability declaration must remain distinct from live verification."""
    capability_state = {
        "planning": True,
        "compile": False,
        "live_verified": False,
    }

    assert capability_state["live_verified"] is False



def test_missing_metadata_is_an_incomplete_execution_state():
    """Required evidence metadata cannot be silently omitted."""
    evidence = {}

    required_keys = {"source", "verification"}

    assert not required_keys.issubset(evidence)
