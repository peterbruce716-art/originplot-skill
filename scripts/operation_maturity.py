from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA = "originplot.operation_maturity.v1"
STATUS_VALUES = {"declared_only", "implemented_unverified", "verified", "unsupported"}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def maturity_status(record: dict[str, Any]) -> str:
    if record.get("unsupported") is True:
        return "unsupported"
    keys = ["registry", "adapter_implemented", "doctor_verified", "inspector_readback", "integration_test"]
    if all(record.get(key) is True for key in keys):
        return "verified"
    if record.get("adapter_implemented") is True:
        return "implemented_unverified"
    return "declared_only"


def normalize(records: list[dict[str, Any]]) -> dict[str, Any]:
    normalized = []
    for item in records:
        row = dict(item)
        row["status"] = maturity_status(row)
        if row["status"] not in STATUS_VALUES:
            raise ValueError(f"invalid maturity status: {row['status']}")
        normalized.append(row)
    return {"schema": SCHEMA, "operations": normalized, "status_values": sorted(STATUS_VALUES)}


def load_matrix(path: Path) -> dict[str, Any]:
    payload = read_json(path)
    if payload.get("schema") != SCHEMA:
        raise ValueError(f"operation maturity schema must be {SCHEMA}")
    return normalize(list(payload.get("operations") or []))


def status_by_operation(matrix: dict[str, Any]) -> dict[str, str]:
    return {str(item.get("operation_id")): str(item.get("status")) for item in matrix.get("operations", [])}


def validate_plan(operation_plan: dict[str, Any], matrix: dict[str, Any]) -> dict[str, Any]:
    statuses = status_by_operation(matrix)
    failures = []
    for operation in operation_plan.get("operations", []):
        op_id = str(operation.get("operation_id"))
        status = statuses.get(op_id, "declared_only")
        if status != "verified":
            failures.append({"code": "OPERATION_MATURITY_UNVERIFIED", "operation_id": op_id, "status": status})
    return {
        "schema": "originplot.operation_maturity_plan_check.v1",
        "status": "ok" if not failures else "failed",
        "failures": failures,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate operation maturity for an OriginPlot operation plan.")
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--operation-plan", type=Path)
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args()
    matrix = load_matrix(args.matrix)
    result = matrix if not args.operation_plan else validate_plan(read_json(args.operation_plan), matrix)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if result.get("status", "ok") == "ok" else 2


if __name__ == "__main__":
    raise SystemExit(main())
