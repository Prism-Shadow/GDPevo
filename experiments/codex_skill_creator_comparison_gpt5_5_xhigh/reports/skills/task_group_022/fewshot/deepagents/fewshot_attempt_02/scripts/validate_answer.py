#!/usr/bin/env python3
"""Dependency-free structural validator for Atlas answer templates."""

from __future__ import annotations

import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


def _schema_value(schema: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in schema:
            return schema[name]
    return None


def _json_type(value: Any) -> str:
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


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def _decimal_places(value: Any) -> int:
    dec = _decimal(value)
    if dec is None:
        return 0
    exponent = dec.as_tuple().exponent
    return max(0, -exponent)


def _check_type(expected: str, value: Any) -> bool:
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


def _validate(schema: dict[str, Any], value: Any, path: str, errors: list[str]) -> None:
    expected_type = schema.get("type")
    if expected_type and not _check_type(expected_type, value):
        errors.append(f"{path}: expected {expected_type}, got {_json_type(value)}")
        return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum")

    if expected_type in {"integer", "number"}:
        dec = _decimal(value)
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if dec is not None and minimum is not None and dec < Decimal(str(minimum)):
            errors.append(f"{path}: value is below minimum {minimum}")
        if dec is not None and maximum is not None and dec > Decimal(str(maximum)):
            errors.append(f"{path}: value is above maximum {maximum}")
        multiple_of = schema.get("multipleOf")
        if dec is not None and multiple_of is not None:
            step = Decimal(str(multiple_of))
            if step != 0 and dec.remainder_near(step) != 0:
                errors.append(f"{path}: value is not a multiple of {multiple_of}")
        precision = _schema_value(schema, "decimal_places", "precision", "x-precision")
        if (
            expected_type == "number"
            and isinstance(precision, int)
            and _decimal_places(value) > precision
        ):
            errors.append(f"{path}: value has more than {precision} decimal places")

    if expected_type == "string":
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{path}: string is shorter than {min_length}")
        pattern = schema.get("pattern")
        if pattern and re.fullmatch(pattern, value) is None:
            errors.append(f"{path}: string does not match pattern {pattern}")

    if expected_type == "array":
        min_items = _schema_value(schema, "minItems", "min_items")
        max_items = _schema_value(schema, "maxItems", "max_items")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: array has fewer than {min_items} items")
        if max_items is not None and len(value) > max_items:
            errors.append(f"{path}: array has more than {max_items} items")
        if _schema_value(schema, "uniqueItems", "unique_items") is True:
            seen: set[str] = set()
            for index, item in enumerate(value):
                key = json.dumps(item, sort_keys=True, separators=(",", ":"))
                if key in seen:
                    errors.append(f"{path}[{index}]: duplicate array item")
                seen.add(key)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for index, item in enumerate(value):
                _validate(item_schema, item, f"{path}[{index}]", errors)

    if expected_type == "object":
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        additional = _schema_value(schema, "additionalProperties", "additional_properties")
        if additional is False:
            extra = sorted(set(value) - set(properties))
            for key in extra:
                errors.append(f"{path}: unexpected key {key!r}")
        for key, child_schema in properties.items():
            if key in value and isinstance(child_schema, dict):
                _validate(child_schema, value[key], f"{path}.{key}", errors)


def main() -> int:
    if len(sys.argv) != 3:
        print(
            "Usage: validate_answer.py <answer_template.json> <answer.json>",
            file=sys.stderr,
        )
        return 2

    template = json.loads(Path(sys.argv[1]).read_text())
    answer = json.loads(Path(sys.argv[2]).read_text())
    errors: list[str] = []
    _validate(template, answer, "$", errors)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("answer structure is valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
