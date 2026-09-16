#!/usr/bin/env python3
"""Lightweight answer-template validator for Atlas JSON outputs."""

from __future__ import annotations

import argparse
import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def schema_get(schema: dict[str, Any], camel: str, snake: str | None = None) -> Any:
    if camel in schema:
        return schema[camel]
    if snake and snake in schema:
        return schema[snake]
    return None


def decimal_places(value: Any) -> int:
    try:
        dec = Decimal(str(value))
    except InvalidOperation:
        return 999
    exponent = dec.as_tuple().exponent
    return max(0, -exponent)


def check_type(path: str, expected: str, value: Any, errors: list[str]) -> bool:
    if expected == "object":
        ok = isinstance(value, dict)
    elif expected == "array":
        ok = isinstance(value, list)
    elif expected == "string":
        ok = isinstance(value, str)
    elif expected == "integer":
        ok = isinstance(value, int) and not isinstance(value, bool)
    elif expected == "number":
        ok = (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    elif expected == "boolean":
        ok = isinstance(value, bool)
    else:
        ok = True
    if not ok:
        errors.append(f"{path}: expected {expected}, got {type(value).__name__}")
    return ok


def validate(path: str, schema: dict[str, Any], value: Any, errors: list[str]) -> None:
    expected_type = schema.get("type")
    if expected_type and not check_type(path, expected_type, value, errors):
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum {schema['enum']!r}")

    if expected_type in {"integer", "number"} and isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: value {value!r} below minimum {schema['minimum']!r}")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: value {value!r} above maximum {schema['maximum']!r}")
        if "multipleOf" in schema:
            try:
                if Decimal(str(value)) % Decimal(str(schema["multipleOf"])) != 0:
                    errors.append(f"{path}: value {value!r} is not a multiple of {schema['multipleOf']!r}")
            except InvalidOperation:
                errors.append(f"{path}: value {value!r} cannot be checked for multipleOf")
        precision = schema.get("precision")
        if precision is None:
            precision = schema.get("decimal_places")
        if precision is None:
            precision = schema.get("x-precision")
        if precision is not None and expected_type == "number" and decimal_places(value) > int(precision):
            errors.append(f"{path}: value {value!r} has more than {precision} decimal places")

    if expected_type == "string":
        if "minLength" in schema and len(value) < schema["minLength"]:
            errors.append(f"{path}: string shorter than minLength {schema['minLength']}")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], value):
            errors.append(f"{path}: value {value!r} does not match pattern {schema['pattern']!r}")

    if expected_type == "array":
        min_items = schema_get(schema, "minItems", "min_items")
        max_items = schema_get(schema, "maxItems", "max_items")
        unique_items = schema_get(schema, "uniqueItems", "unique_items")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: array has fewer than {min_items} items")
        if max_items is not None and len(value) > max_items:
            errors.append(f"{path}: array has more than {max_items} items")
        if unique_items:
            seen = set()
            for item in value:
                key = json.dumps(item, sort_keys=True)
                if key in seen:
                    errors.append(f"{path}: array items are not unique")
                    break
                seen.add(key)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                validate(f"{path}[{index}]", item_schema, item, errors)

    if expected_type == "object":
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        additional = schema_get(schema, "additionalProperties", "additional_properties")
        if additional is False:
            extras = sorted(set(value) - set(properties))
            for key in extras:
                errors.append(f"{path}: unexpected key {key!r}")
        for key, child_schema in properties.items():
            if key in value and isinstance(child_schema, dict):
                validate(f"{path}.{key}", child_schema, value[key], errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template")
    parser.add_argument("answer")
    args = parser.parse_args()

    template = json.loads(Path(args.template).read_text(encoding="utf-8"))
    answer = json.loads(Path(args.answer).read_text(encoding="utf-8"))
    errors: list[str] = []
    validate("$", template, answer, errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("answer.json conforms to template")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
