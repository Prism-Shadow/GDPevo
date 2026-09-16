#!/usr/bin/env python3
"""Validate the subset of JSON Schema used by Atlas answer templates."""

import json
import math
import re
import sys
from decimal import Decimal, InvalidOperation


def keyword(schema, *names, default=None):
    for name in names:
        if name in schema:
            return schema[name]
    return default


def json_type(value):
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


def number_decimal_places(value):
    text = format(value, "f") if isinstance(value, float) else str(value)
    if "." not in text:
        return 0
    return len(text.rstrip("0").split(".", 1)[1])


def is_multiple(value, step):
    try:
        value_dec = Decimal(str(value))
        step_dec = Decimal(str(step))
    except InvalidOperation:
        return False
    if step_dec == 0:
        return False
    return value_dec.remainder_near(step_dec) == 0


def validate(schema, value, path, errors):
    expected_type = schema.get("type")
    if expected_type:
        allowed = expected_type if isinstance(expected_type, list) else [expected_type]
        actual = json_type(value)
        if actual == "integer" and "number" in allowed:
            pass
        elif actual not in allowed:
            errors.append(f"{path}: expected {expected_type}, got {actual}")
            return

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum {schema['enum']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        multiple_of = schema.get("multipleOf")
        precision = keyword(schema, "decimal_places", "precision", "x-precision")
        if minimum is not None and value < minimum:
            errors.append(f"{path}: {value} is less than minimum {minimum}")
        if maximum is not None and value > maximum:
            errors.append(f"{path}: {value} is greater than maximum {maximum}")
        if multiple_of is not None and not is_multiple(value, multiple_of):
            errors.append(f"{path}: {value} is not a multiple of {multiple_of}")
        if precision is not None and number_decimal_places(value) > int(precision):
            errors.append(f"{path}: {value} has more than {precision} decimal places")
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            errors.append(f"{path}: non-finite number is not valid JSON output")

    if isinstance(value, str):
        min_length = schema.get("minLength")
        pattern = schema.get("pattern")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{path}: string is shorter than minLength {min_length}")
        if pattern and not re.search(pattern, value):
            errors.append(f"{path}: {value!r} does not match pattern {pattern!r}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        additional = keyword(schema, "additionalProperties", "additional_properties", default=True)
        if additional is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected key {key!r}")
        for key, child in value.items():
            if key in properties:
                validate(properties[key], child, f"{path}.{key}", errors)

    if isinstance(value, list):
        min_items = keyword(schema, "minItems", "min_items")
        max_items = keyword(schema, "maxItems", "max_items")
        unique_items = keyword(schema, "uniqueItems", "unique_items", default=False)
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: array has fewer than {min_items} items")
        if max_items is not None and len(value) > max_items:
            errors.append(f"{path}: array has more than {max_items} items")
        if unique_items:
            seen = set()
            for item in value:
                key = json.dumps(item, sort_keys=True, separators=(",", ":"))
                if key in seen:
                    errors.append(f"{path}: array items are not unique")
                    break
                seen.add(key)
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                validate(item_schema, item, f"{path}[{index}]", errors)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: validate_answer.py <answer_template.json> <answer.json>")
    with open(sys.argv[1], "r", encoding="utf-8") as handle:
        schema = json.load(handle)
    with open(sys.argv[2], "r", encoding="utf-8") as handle:
        answer = json.load(handle)

    errors = []
    validate(schema, answer, "$", errors)
    if errors:
        print("Validation failed:")
        for error in errors:
            print(f"- {error}")
        raise SystemExit(1)
    print("Validation passed.")


if __name__ == "__main__":
    main()
