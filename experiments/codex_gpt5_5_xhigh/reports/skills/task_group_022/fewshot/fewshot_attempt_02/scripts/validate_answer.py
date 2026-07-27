#!/usr/bin/env python3
"""Validate an answer JSON object against the supplied task answer template."""

from __future__ import annotations

import json
import math
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def schema_name(schema: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in schema:
            return schema[name]
    return None


def is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def decimal_places(value: Any) -> int:
    try:
        decimal = Decimal(str(value)).normalize()
    except InvalidOperation:
        return 10**9
    return max(0, -decimal.as_tuple().exponent)


def multiple_of(value: Any, step: Any) -> bool:
    try:
        return Decimal(str(value)) % Decimal(str(step)) == 0
    except InvalidOperation:
        return False


def validate(schema: dict[str, Any], value: Any, path: str, errors: list[str]) -> None:
    expected = schema.get("type")
    if expected == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object")
            return
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: missing required field")
        if schema_name(schema, "additionalProperties", "additional_properties") is False:
            for key in value:
                if key not in props:
                    errors.append(f"{path}.{key}: additional field is not allowed")
        for key, child in props.items():
            if key in value:
                validate(child, value[key], f"{path}.{key}", errors)
        return

    if expected == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array")
            return
        min_items = schema_name(schema, "minItems", "min_items")
        max_items = schema_name(schema, "maxItems", "max_items")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: expected at least {min_items} items")
        if max_items is not None and len(value) > max_items:
            errors.append(f"{path}: expected at most {max_items} items")
        if schema_name(schema, "uniqueItems", "unique_items"):
            encoded = [json.dumps(item, sort_keys=True, separators=(",", ":")) for item in value]
            if len(encoded) != len(set(encoded)):
                errors.append(f"{path}: duplicate items are not allowed")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate(item_schema, item, f"{path}[{index}]", errors)
        return

    if expected == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{path}: expected integer")
            return
    elif expected == "number":
        if not is_number(value):
            errors.append(f"{path}: expected number")
            return
    elif expected == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string")
            return
    elif expected == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{path}: expected boolean")
            return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum")
    if isinstance(value, str) and "pattern" in schema and not re.search(schema["pattern"], value):
        errors.append(f"{path}: value does not match pattern {schema['pattern']!r}")
    if is_number(value):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value is below minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: value is above maximum {schema['maximum']}")
        if "multipleOf" in schema and not multiple_of(value, schema["multipleOf"]):
            errors.append(f"{path}: value is not a multiple of {schema['multipleOf']}")
        places = schema_name(schema, "decimal_places", "precision", "x-precision")
        if places is not None and expected == "number" and decimal_places(value) > int(places):
            errors.append(f"{path}: value has more than {places} decimal places")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: validate_answer.py <answer_template.json> <answer.json>", file=sys.stderr)
        return 2
    template = load_json(sys.argv[1])
    answer = load_json(sys.argv[2])
    errors: list[str] = []
    validate(template, answer, "$", errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
