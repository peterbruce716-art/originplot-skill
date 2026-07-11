from __future__ import annotations

import json
from pathlib import Path
from typing import Any


TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
}


class SchemaValidationError(ValueError):
    pass


def read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def validate_json_schema(payload: Any, schema: dict[str, Any], *, label: str = "document") -> None:
    errors: list[str] = []
    _validate(payload, schema, label, errors)
    if errors:
        raise SchemaValidationError("; ".join(errors))


def validate_json_file(payload_path: str | Path, schema_path: str | Path, *, label: str | None = None) -> None:
    payload = read_json(payload_path)
    schema = read_json(schema_path)
    validate_json_schema(payload, schema, label=label or str(payload_path))


def _validate(value: Any, schema: dict[str, Any], path: str, errors: list[str]) -> None:
    if "const" in schema and value != schema["const"]:
        errors.append(f"{path} must equal {schema['const']!r}")
        return

    expected_type = schema.get("type")
    if isinstance(expected_type, str):
        py_type = TYPE_MAP.get(expected_type)
        if py_type is not None and not isinstance(value, py_type):
            errors.append(f"{path} must be {expected_type}")
            return

    enum = schema.get("enum")
    if isinstance(enum, list) and value not in enum:
        errors.append(f"{path} must be one of {enum!r}")

    if isinstance(value, dict):
        required = schema.get("required") or []
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key} is required")
        properties = schema.get("properties") or {}
        for key, subschema in properties.items():
            if key in value and isinstance(subschema, dict):
                _validate(value[key], subschema, f"{path}.{key}", errors)
        if schema.get("additionalProperties") is False:
            allowed = set(properties)
            for key in value:
                if key not in allowed:
                    errors.append(f"{path}.{key} is not allowed")

    if isinstance(value, list):
        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")
        if isinstance(min_items, int) and len(value) < min_items:
            errors.append(f"{path} must contain at least {min_items} items")
        if isinstance(max_items, int) and len(value) > max_items:
            errors.append(f"{path} must contain at most {max_items} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate(item, item_schema, f"{path}[{index}]", errors)
