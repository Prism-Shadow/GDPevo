#!/usr/bin/env python3
"""Validate a PeopleOps answer JSON against an answer_template.json."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value: Any) -> bool:
    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)


def validate_field(name: str, spec: dict[str, Any], value: Any) -> list[str]:
    errors: list[str] = []
    field_type = spec.get("type")

    if field_type == "string":
        if not isinstance(value, str):
            errors.append(f"{name}: expected string, got {type(value).__name__}")
    elif field_type == "integer":
        if not is_integer(value):
            errors.append(f"{name}: expected integer, got {type(value).__name__}")
    elif field_type == "number":
        if not is_number(value):
            errors.append(f"{name}: expected number, got {type(value).__name__}")
    elif field_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{name}: expected boolean, got {type(value).__name__}")
    elif field_type == "enum":
        allowed = spec.get("allowed_values", [])
        if value not in allowed:
            errors.append(f"{name}: expected one of {allowed}, got {value!r}")
    elif field_type == "list[string]":
        errors.extend(validate_list(name, value, lambda item: isinstance(item, str), "string"))
    elif field_type == "list[enum]":
        allowed = spec.get("allowed_values", [])
        errors.extend(validate_list(name, value, lambda item: item in allowed, f"one of {allowed}"))
    else:
        errors.append(f"{name}: unsupported template type {field_type!r}")

    return errors


def validate_list(name: str, value: Any, predicate: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        return [f"{name}: expected list, got {type(value).__name__}"]
    errors: list[str] = []
    for index, item in enumerate(value):
        if not predicate(item):
            errors.append(f"{name}[{index}]: expected {label}, got {item!r}")
    return errors


def validate(template: dict[str, Any], answer: dict[str, Any], allow_extra: bool) -> list[str]:
    errors: list[str] = []
    for key, spec in template.items():
        if key not in answer:
            errors.append(f"{key}: missing required field")
            continue
        errors.extend(validate_field(key, spec, answer[key]))

    if not allow_extra:
        for key in answer:
            if key not in template:
                errors.append(f"{key}: extra field not present in template")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template_json", help="Path to input/payloads/answer_template.json")
    parser.add_argument("answer_json", help="Path to proposed answer JSON")
    parser.add_argument("--allow-extra", action="store_true", help="Allow answer keys not present in the template")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        template = load_json(args.template_json)
        answer = load_json(args.answer_json)
    except Exception as exc:  # noqa: BLE001 - CLI should report concise failure.
        print(f"error: failed to load JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(template, dict):
        print("error: template root must be an object", file=sys.stderr)
        return 1
    if not isinstance(answer, dict):
        print("error: answer root must be an object", file=sys.stderr)
        return 1

    errors = validate(template, answer, allow_extra=args.allow_extra)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("OK: answer matches template")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
