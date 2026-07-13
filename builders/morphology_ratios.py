from __future__ import annotations

from typing import Any, Iterable, Mapping


def validate_morphology_ratio_contracts(
    measurements: Iterable[Mapping[str, Any]],
    contracts: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Validate declared morphology ratios against post-export measurements."""
    declared = [dict(contract) for contract in contracts]
    measured = [dict(measurement) for measurement in measurements]
    mismatches: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    if not declared:
        mismatches.append(
            {
                "property": "morphology_ratio_contracts",
                "expected": "at least one explicit contract",
                "actual": "missing",
            }
        )

    measurement_index: dict[tuple[str, str, str, str], float] = {}
    for item in measured:
        try:
            key = (
                str(item["scope_id"]),
                str(item["morphology_id"]),
                str(item["metric"]),
                str(item["item"]),
            )
            value = float(item["value"])
        except (KeyError, TypeError, ValueError) as exc:
            mismatches.append({"property": "measurement_schema", "measurement": item, "error": str(exc)})
            continue
        if value <= 0:
            mismatches.append({"property": "measurement_positive", "measurement": item, "actual": value})
            continue
        measurement_index[key] = value

    for contract in declared:
        required = (
            "morphology_id",
            "scope_id",
            "metric",
            "reference_item",
            "expected_ratios",
            "tolerance",
            "audit_stage",
        )
        missing = [key for key in required if key not in contract]
        if missing:
            mismatches.append(
                {
                    "property": "contract_schema",
                    "morphology_id": contract.get("morphology_id"),
                    "missing": missing,
                }
            )
            continue

        morphology_id = str(contract["morphology_id"])
        scope_id = str(contract["scope_id"])
        metric = str(contract["metric"])
        reference_item = str(contract["reference_item"])
        contract_mismatches: list[dict[str, Any]] = []
        try:
            expected = {str(key): float(value) for key, value in dict(contract["expected_ratios"]).items()}
            tolerance = float(contract["tolerance"])
        except (TypeError, ValueError) as exc:
            mismatches.append(
                {
                    "property": "contract_schema",
                    "scope_id": scope_id,
                    "morphology_id": morphology_id,
                    "error": str(exc),
                }
            )
            continue
        if tolerance < 0:
            contract_mismatches.append({"property": "tolerance", "expected": ">= 0", "actual": tolerance})
        if reference_item not in expected:
            contract_mismatches.append(
                {"property": "reference_item", "expected": "present in expected_ratios", "actual": reference_item}
            )

        values: dict[str, float] = {}
        for item in expected:
            key = (scope_id, morphology_id, metric, item)
            if key not in measurement_index:
                contract_mismatches.append(
                    {"property": "measurement", "item": item, "expected": "post-export value", "actual": "missing"}
                )
            else:
                values[item] = measurement_index[key]

        actual_ratios: dict[str, float] = {}
        deltas: dict[str, float] = {}
        reference_value = values.get(reference_item)
        if reference_value:
            for item, expected_ratio in expected.items():
                if item not in values:
                    continue
                actual_ratio = values[item] / reference_value
                delta = abs(actual_ratio - expected_ratio)
                actual_ratios[item] = actual_ratio
                deltas[item] = delta
                if delta > tolerance:
                    contract_mismatches.append(
                        {
                            "property": "ratio_tolerance",
                            "item": item,
                            "expected": expected_ratio,
                            "actual": actual_ratio,
                            "delta": delta,
                            "tolerance": tolerance,
                        }
                    )

        ordered_items = [str(item) for item in contract.get("ordered_descending", [])]
        if ordered_items and all(item in values for item in ordered_items):
            for wider, narrower in zip(ordered_items, ordered_items[1:]):
                if values[wider] <= values[narrower]:
                    contract_mismatches.append(
                        {
                            "property": "ordered_descending",
                            "expected": f"{wider} > {narrower}",
                            "actual": f"{values[wider]} <= {values[narrower]}",
                        }
                    )

        result = {
            "morphology_id": morphology_id,
            "scope_id": scope_id,
            "metric": metric,
            "audit_stage": contract["audit_stage"],
            "reference_item": reference_item,
            "expected_ratios": expected,
            "actual_values": values,
            "actual_ratios": actual_ratios,
            "absolute_deltas": deltas,
            "tolerance": tolerance,
            "status": "ok" if not contract_mismatches else "failed",
            "mismatches": contract_mismatches,
        }
        results.append(result)
        mismatches.extend(
            {"scope_id": scope_id, "morphology_id": morphology_id, **mismatch}
            for mismatch in contract_mismatches
        )

    return {
        "schema": "originplot.morphology_ratio_validation.v1",
        "status": "ok" if not mismatches else "failed",
        "contracts_declared": len(declared),
        "contracts_evaluated": len(results),
        "results": results,
        "mismatches": mismatches,
    }
