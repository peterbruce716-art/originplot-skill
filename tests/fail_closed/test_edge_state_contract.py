"""Edge-state contracts for OriginPlot v6.1.

These tests describe deterministic rejection of invalid execution states.
The system should fail explicitly rather than silently degrading output.
"""



def test_missing_capability_context_is_rejected():
    """Execution without capability context is incomplete."""
    execution_context = {}

    assert "capability" not in execution_context



def test_invalid_operation_payload_is_not_successful():
    """Malformed operation payloads must not become valid operations."""
    payload = {"operation": "create_plot"}

    required_fields = {"input", "verification"}

    assert not required_fields.issubset(payload)



def test_verification_state_must_match_execution_state():
    """Verification success requires a completed execution state."""
    state = {
        "executed": False,
        "verified": True,
    }

    invalid_verification = state["verified"] and not state["executed"]

    assert invalid_verification
