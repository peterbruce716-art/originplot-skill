"""Contract checks for the OperationPlan serialization boundary.

These tests intentionally focus on the public contract rather than Origin execution.
"""

from originplot.operation_plan import OperationPlan, OPERATION_PLAN_SCHEMA


def test_operation_plan_round_trip_preserves_contract():
    plan = OperationPlan(
        figure_id="demo",
        plot_type="line",
        source={"path": "data.csv"},
        profile="standard",
        operations=({"action": "create_plot"},),
        metadata={"version": "v6.1"},
    )

    payload = plan.to_dict()
    restored = OperationPlan.from_dict(payload)

    assert payload["schema"] == OPERATION_PLAN_SCHEMA
    assert restored.figure_id == "demo"
    assert restored.operations[0]["action"] == "create_plot"
    assert restored.metadata["version"] == "v6.1"


def test_operation_plan_rejects_unknown_schema():
    payload = {"schema": "unknown.schema"}

    try:
        OperationPlan.from_dict(payload)
    except ValueError as exc:
        assert "unsupported operation plan schema" in str(exc)
    else:
        raise AssertionError("unknown schemas must fail closed")
