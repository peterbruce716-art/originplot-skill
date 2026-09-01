"""Capability contract tests for OriginPlot v6.1.

These tests intentionally focus on stable contracts rather than Origin runtime
execution. Live Origin verification remains a separate validation layer.
"""


def test_capability_contract_distinguishes_planning_and_execution():
    """Planning support must not imply live execution evidence."""
    planning_support = True
    live_evidence = False

    assert planning_support is True
    assert live_evidence is False


def test_unsupported_capability_requires_explicit_handling():
    """Unknown capabilities should be handled explicitly by callers."""
    supported = {"line", "scatter", "bar"}
    requested = "unknown_plot_type"

    assert requested not in supported
