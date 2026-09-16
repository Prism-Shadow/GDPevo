#!/usr/bin/env python3
"""Validate an Atlas answer JSON against the common task template subset."""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path


def load_json(path: str) -> object:
    with Path(path).open("r", encoding="utf-8") as f:
        return json.load(f)


def template_get(schema: dict, *names: str, default=None):
    for name in names:
        if name in schema:
            return schema[name]
    return default


def is_integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value: object) -> bool:
    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)


def check_multiple_of(value: float, step: float) -> bool:
    if step == 0:
        return True
    quotient = value / step
    return math.isclose(quotient, round(quotient), rel_tol=0, abs_tol=1e-9)


def validate(value: object, schema: object, path: str, errors: list[str]) -> None:
    if not isinstance(schema, dict):
        return

    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object")
            return

        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")

        properties = schema.get("properties", {})
        additional = template_get(schema, "additionalProperties", "additional_properties", default=True)
        if additional is False:
            extra = sorted(set(value) - set(properties))
            for key in extra:
                errors.append(f"{path}: unexpected key {key!r}")

        for key, child_schema in properties.items():
            if key in value:
                validate(value[key], child_schema, f"{path}.{key}", errors)
        return

    if expected_type == "array":
        if not isinstance(value, list):
            errors.append(f"{path}: expected array")
            return

        min_items = template_get(schema, "minItems", "min_items")
        max_items = template_get(schema, "maxItems", "max_items")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: expected at least {min_items} items")
        if max_items is not None and len(value) > max_items:
            errors.append(f"{path}: expected at most {max_items} items")
        if template_get(schema, "uniqueItems", "unique_items", default=False):
            normalized = [json.dumps(item, sort_keys=True) for item in value]
            if len(normalized) != len(set(normalized)):
                errors.append(f"{path}: array items are not unique")

        item_schema = schema.get("items")
        if item_schema is not None:
            for index, item in enumerate(value):
                validate(item, item_schema, f"{path}[{index}]", errors)
        return

    if expected_type == "string":
        if not isinstance(value, str):
            errors.append(f"{path}: expected string")
            return
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: value {value!r} not in enum")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{path}: value {value!r} does not match pattern")
        min_length = template_get(schema, "minLength", "min_length")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{path}: expected string length at least {min_length}")
        return

    if expected_type == "integer":
        if not is_integer(value):
            errors.append(f"{path}: expected integer")
            return
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and value < minimum:
            errors.append(f"{path}: value below minimum {minimum}")
        if maximum is not None and value > maximum:
            errors.append(f"{path}: value above maximum {maximum}")
        return

    if expected_type == "number":
        if not is_number(value):
            errors.append(f"{path}: expected number")
            return
        number = float(value)
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        multiple_of = template_get(schema, "multipleOf", "multiple_of")
        if minimum is not None and number < minimum:
            errors.append(f"{path}: value below minimum {minimum}")
        if maximum is not None and number > maximum:
            errors.append(f"{path}: value above maximum {maximum}")
        if multiple_of is not None and not check_multiple_of(number, float(multiple_of)):
            errors.append(f"{path}: value is not a multiple of {multiple_of}")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: validate_answer.py <answer_template.json> <answer.json>", file=sys.stderr)
        return 2

    template = load_json(sys.argv[1])
    answer = load_json(sys.argv[2])
    errors: list[str] = []
    validate(answer, template, "$", errors)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("answer.json matches the supported template constraints")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
