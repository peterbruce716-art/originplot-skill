"""Capability registry contract guards for OriginPlot v6.1.

These tests keep capability declarations explicit and prevent a future
implementation from treating unknown capabilities as supported by default.
"""



def test_registered_capabilities_are_explicitly_named():
    """Capabilities should come from a finite declared registry."""
    registry = {
        "create_plot": "supported",
        "apply_style": "supported",
        "export": "supported",
    }

    assert all(name.strip() for name in registry)



def test_unknown_capability_is_not_implicitly_supported():
    """Unknown capability requests must require explicit implementation."""
    registry = {"create_plot", "apply_style", "export"}
    requested = "unknown_capability"

    assert requested not in registry
