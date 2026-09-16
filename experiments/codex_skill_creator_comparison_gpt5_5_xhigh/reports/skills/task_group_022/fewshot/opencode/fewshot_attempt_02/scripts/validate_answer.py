#!/usr/bin/env python3
"""Validate an Atlas answer JSON against the staged answer template."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Set


def key(schema: Dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in schema:
            return schema[name]
    return default


def type_name(value: Any) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    if value is None:
        return "null"
    return type(value).__name__


def decimal_places(value: Any) -> int:
    try:
        dec = Decimal(str(value))
    except InvalidOperation:
        return 999
    normalized = dec.normalize()
    if normalized == normalized.to_integral():
        return 0
    return max(0, -normalized.as_tuple().exponent)


def multiple_of(value: Any, step: Any) -> bool:
    try:
        dec_value = Decimal(str(value))
        dec_step = Decimal(str(step))
    except InvalidOperation:
        return False
    if dec_step == 0:
        return True
    return dec_value % dec_step == 0


def unique_items(values: List[Any]) -> bool:
    seen: Set[str] = set()
    for item in values:
        marker = json.dumps(item, sort_keys=True, separators=(",", ":"))
        if marker in seen:
            return False
        seen.add(marker)
    return True


def validate(schema: Any, value: Any, path: str, errors: List[str]) -> None:
    if not isinstance(schema, dict):
        return

    expected = schema.get("type")
    if isinstance(expected, list):
        type_ok = any(check_type(t, value) for t in expected)
    elif isinstance(expected, str):
        type_ok = check_type(expected, value)
    else:
        type_ok = True
    if not type_ok:
        errors.append(f"{path}: expected {expected}, got {type_name(value)}")
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum {schema['enum']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            errors.append(f"{path}: {value!r} is below minimum {minimum!r}")
        if maximum is not None and value > maximum:
            errors.append(f"{path}: {value!r} is above maximum {maximum!r}")
        if "multipleOf" in schema and not multiple_of(value, schema["multipleOf"]):
            errors.append(f"{path}: {value!r} is not a multiple of {schema['multipleOf']!r}")
        precision = key(schema, "decimal_places", "precision", "x-precision")
        if precision is not None and int(precision) > 0 and decimal_places(value) > int(precision):
            errors.append(f"{path}: {value!r} has more than {precision} decimal places")
        if isinstance(value, float) and not math.isfinite(value):
            errors.append(f"{path}: non-finite number {value!r}")

    if isinstance(value, str) and "pattern" in schema:
        if not re.search(schema["pattern"], value):
            errors.append(f"{path}: value {value!r} does not match pattern {schema['pattern']!r}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        for prop in required:
            if prop not in value:
                errors.append(f"{path}: missing required key {prop!r}")
        additional = key(schema, "additionalProperties", "additional_properties", default=True)
        if additional is False:
            allowed = set(properties)
            for prop in value:
                if prop not in allowed:
                    errors.append(f"{path}: unexpected key {prop!r}")
        for prop, child in properties.items():
            if prop in value:
                validate(child, value[prop], f"{path}.{prop}", errors)

    if isinstance(value, list):
        min_items = key(schema, "minItems", "min_items")
        max_items = key(schema, "maxItems", "max_items")
        if min_items is not None and len(value) < int(min_items):
            errors.append(f"{path}: has {len(value)} items, below {min_items}")
        if max_items is not None and len(value) > int(max_items):
            errors.append(f"{path}: has {len(value)} items, above {max_items}")
        if key(schema, "uniqueItems", "unique_items", default=False) and not unique_items(value):
            errors.append(f"{path}: duplicate array items")
        item_schema = schema.get("items")
        if item_schema is not None:
            for idx, item in enumerate(value):
                validate(item_schema, item, f"{path}[{idx}]", errors)


def check_type(expected: str, value: Any) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template")
    parser.add_argument("answer")
    args = parser.parse_args()

    with open(args.template, "r", encoding="utf-8") as f:
        schema = json.load(f)
    with open(args.answer, "r", encoding="utf-8") as f:
        answer = json.load(f)

    errors: List[str] = []
    validate(schema, answer, "$", errors)
    if errors:
        for err in errors:
            print(err, file=sys.stderr)
        return 1
    print("answer.json matches the template constraints checked by this validator")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
