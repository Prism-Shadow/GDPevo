#!/usr/bin/env python3
"""Validate answer.json against the task's JSON-like answer template."""

import json
import re
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path


def schema_value(schema, *names, default=None):
    for name in names:
        if name in schema:
            return schema[name]
    return default


def type_matches(expected, value):
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    return True


def decimal_places(value):
    try:
        decimal = Decimal(str(value))
    except InvalidOperation:
        return None
    exponent = decimal.as_tuple().exponent
    return max(0, -exponent)


def is_multiple(value, step):
    try:
        number = Decimal(str(value))
        multiple = Decimal(str(step))
    except InvalidOperation:
        return False
    if multiple == 0:
        return True
    return number.remainder_near(multiple) == 0


def validate(schema, value, path="$"):
    errors = []
    expected_type = schema.get("type")
    if expected_type and not type_matches(expected_type, value):
        errors.append(f"{path}: expected {expected_type}, got {type(value).__name__}")
        return errors

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} is not in enum {schema['enum']!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        multiple = schema.get("multipleOf")
        precision = schema_value(schema, "decimal_places", "precision", "x-precision")
        if minimum is not None and value < minimum:
            errors.append(f"{path}: {value!r} is below minimum {minimum!r}")
        if maximum is not None and value > maximum:
            errors.append(f"{path}: {value!r} is above maximum {maximum!r}")
        if multiple is not None and not is_multiple(value, multiple):
            errors.append(f"{path}: {value!r} is not a multiple of {multiple!r}")
        if precision is not None:
            places = decimal_places(value)
            if places is not None and places > int(precision):
                errors.append(f"{path}: {value!r} has more than {precision} decimal places")

    if isinstance(value, str):
        pattern = schema.get("pattern")
        min_length = schema.get("minLength")
        if pattern and re.search(pattern, value) is None:
            errors.append(f"{path}: {value!r} does not match pattern {pattern!r}")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{path}: string is shorter than {min_length}")

    if isinstance(value, dict):
        required = schema.get("required", [])
        properties = schema.get("properties", {})
        additional = schema_value(schema, "additionalProperties", "additional_properties", default=True)

        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        if additional is False:
            for key in value:
                if key not in properties:
                    errors.append(f"{path}: unexpected key {key!r}")
        for key, child in properties.items():
            if key in value:
                errors.extend(validate(child, value[key], f"{path}.{key}"))

    if isinstance(value, list):
        min_items = schema_value(schema, "minItems", "min_items")
        max_items = schema_value(schema, "maxItems", "max_items")
        unique_items = schema_value(schema, "uniqueItems", "unique_items", default=False)
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: array has fewer than {min_items} items")
        if max_items is not None and len(value) > max_items:
            errors.append(f"{path}: array has more than {max_items} items")
        if unique_items:
            seen = set()
            for index, item in enumerate(value):
                marker = json.dumps(item, sort_keys=True, separators=(",", ":"))
                if marker in seen:
                    errors.append(f"{path}[{index}]: duplicate array item")
                seen.add(marker)
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                errors.extend(validate(item_schema, item, f"{path}[{index}]"))

    return errors


def main():
    if len(sys.argv) != 3:
        print("Usage: validate_answer.py <answer_template.json> <answer.json>", file=sys.stderr)
        sys.exit(2)

    template_path = Path(sys.argv[1])
    answer_path = Path(sys.argv[2])
    template = json.loads(template_path.read_text())
    answer = json.loads(answer_path.read_text())
    errors = validate(template, answer)
    if errors:
        print("answer.json failed validation:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        sys.exit(1)
    print("answer.json matches the template structure")


if __name__ == "__main__":
    main()
