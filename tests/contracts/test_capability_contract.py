from contracts.capability import CapabilitySet, validate_capability_subset


def test_capability_subset_has_no_missing_operations():
    builder = CapabilitySet.from_iterable(
        "line_builder",
        ["create_graph", "add_plot"],
    )

    adapter = CapabilitySet.from_iterable(
        "origin_adapter",
        ["create_graph", "add_plot", "export"],
    )

    assert validate_capability_subset(
        builder.operations,
        adapter.operations,
    ) == set()


def test_capability_subset_reports_missing_operations():
    assert validate_capability_subset(
        ["create_surface"],
        ["create_graph"],
    ) == {"create_surface"}
