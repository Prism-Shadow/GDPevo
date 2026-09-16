#!/usr/bin/env python3
"""Validate a PeopleOps answer JSON object against an answer_template.json file."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_scalar(field: str, type_name: str, value: Any, allowed: list[Any] | None) -> list[str]:
    errors: list[str] = []
    if type_name == "string":
        if not isinstance(value, str):
            errors.append(f"{field}: expected string")
    elif type_name == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            errors.append(f"{field}: expected number")
    elif type_name == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{field}: expected integer")
    elif type_name == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{field}: expected boolean")
    elif type_name == "enum":
        if not isinstance(value, str):
            errors.append(f"{field}: expected enum string")
    else:
        errors.append(f"{field}: unsupported type {type_name!r}")

    if allowed is not None and value not in allowed:
        errors.append(f"{field}: value {value!r} not in allowed_values")
    return errors


def validate_field(field: str, spec: dict[str, Any], value: Any) -> list[str]:
    type_name = spec.get("type")
    allowed = spec.get("allowed_values")
    if not isinstance(type_name, str):
        return [f"{field}: template type must be a string"]
    if allowed is not None and not isinstance(allowed, list):
        return [f"{field}: template allowed_values must be a list"]

    if type_name.startswith("list[") and type_name.endswith("]"):
        item_type = type_name[5:-1]
        if not isinstance(value, list):
            return [f"{field}: expected list"]
        errors: list[str] = []
        for index, item in enumerate(value):
            item_field = f"{field}[{index}]"
            if item_type == "enum":
                errors.extend(validate_scalar(item_field, "enum", item, allowed))
            else:
                errors.extend(validate_scalar(item_field, item_type, item, None))
        return errors

    return validate_scalar(field, type_name, value, allowed)


def validate(template: dict[str, Any], answer: Any) -> list[str]:
    if not isinstance(answer, dict):
        return ["answer: expected top-level JSON object"]
    errors: list[str] = []
    template_keys = set(template)
    answer_keys = set(answer)

    for key in sorted(template_keys - answer_keys):
        errors.append(f"{key}: missing required key")
    for key in sorted(answer_keys - template_keys):
        errors.append(f"{key}: extra key not present in template")

    for key in template:
        if key in answer:
            spec = template[key]
            if not isinstance(spec, dict):
                errors.append(f"{key}: template spec must be an object")
            else:
                errors.extend(validate_field(key, spec, answer[key]))
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", help="Path to input/payloads/answer_template.json")
    parser.add_argument("answer", help="Path to answer JSON")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    template = load_json(args.template)
    answer = load_json(args.answer)
    if not isinstance(template, dict):
        print("template: expected top-level JSON object", file=sys.stderr)
        return 1

    errors = validate(template, answer)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
