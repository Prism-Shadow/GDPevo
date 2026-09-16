#!/usr/bin/env python3
"""Validate a PeopleOps final answer against answer_template.json."""

from __future__ import annotations

import json
import math
import sys
from typing import Any


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def check_scalar(field: str, expected_type: str, value: Any, spec: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if expected_type == "string":
        if not isinstance(value, str):
            errors.append(f"{field}: expected string")
    elif expected_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
            errors.append(f"{field}: expected finite number")
    elif expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"{field}: expected integer")
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            errors.append(f"{field}: expected boolean")
    elif expected_type == "enum":
        allowed = spec.get("allowed_values", [])
        if value not in allowed:
            errors.append(f"{field}: expected one of {allowed!r}")
    else:
        errors.append(f"{field}: unsupported template type {expected_type!r}")
    return errors


def check_field(field: str, spec: dict[str, Any], value: Any) -> list[str]:
    expected_type = spec.get("type")
    if expected_type == "list[string]":
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            return [f"{field}: expected list of strings"]
        return []
    if expected_type == "list[enum]":
        allowed = spec.get("allowed_values", [])
        if not isinstance(value, list):
            return [f"{field}: expected list of enum strings"]
        bad = [item for item in value if item not in allowed]
        if bad:
            return [f"{field}: values {bad!r} not in {allowed!r}"]
        return []
    return check_scalar(field, str(expected_type), value, spec)


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: validate_answer.py <answer_template.json> <answer.json>", file=sys.stderr)
        return 2

    template = load_json(sys.argv[1])
    answer = load_json(sys.argv[2])
    errors: list[str] = []

    if not isinstance(template, dict) or not isinstance(answer, dict):
        print("Both template and answer must be JSON objects", file=sys.stderr)
        return 2

    template_keys = set(template)
    answer_keys = set(answer)
    for key in sorted(template_keys - answer_keys):
        errors.append(f"{key}: missing required key")
    for key in sorted(answer_keys - template_keys):
        errors.append(f"{key}: extra key not present in template")
    for key in sorted(template_keys & answer_keys):
        spec = template[key]
        if not isinstance(spec, dict):
            errors.append(f"{key}: template spec must be an object")
            continue
        errors.extend(check_field(key, spec, answer[key]))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
