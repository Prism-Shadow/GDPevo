#!/usr/bin/env python3
"""Validate a PeopleOps answer JSON against an answer_template.json file."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def fail(message: str) -> None:
    print(f"Invalid answer: {message}", file=sys.stderr)
    raise SystemExit(1)


def check_scalar(field: str, expected: str, value: Any) -> None:
    if expected == "string":
        if not isinstance(value, str):
            fail(f"{field} must be a string")
    elif expected == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            fail(f"{field} must be an integer")
    elif expected == "number":
        if not (
            (isinstance(value, int) and not isinstance(value, bool))
            or isinstance(value, float)
        ):
            fail(f"{field} must be a number")
    elif expected == "boolean":
        if not isinstance(value, bool):
            fail(f"{field} must be a boolean")
    else:
        fail(f"{field} has unsupported template type {expected!r}")


def check_enum(field: str, spec: dict[str, Any], value: Any) -> None:
    if not isinstance(value, str):
        fail(f"{field} must be an enum string")
    allowed = spec.get("allowed_values")
    if not isinstance(allowed, list):
        fail(f"{field} enum template is missing allowed_values")
    if value not in allowed:
        fail(f"{field} must be one of {allowed}, got {value!r}")


def check_list(field: str, item_type: str, spec: dict[str, Any], value: Any) -> None:
    if not isinstance(value, list):
        fail(f"{field} must be a list")
    if item_type == "string":
        for index, item in enumerate(value):
            if not isinstance(item, str):
                fail(f"{field}[{index}] must be a string")
    elif item_type == "enum":
        allowed = spec.get("allowed_values")
        if not isinstance(allowed, list):
            fail(f"{field} enum-list template is missing allowed_values")
        for index, item in enumerate(value):
            if not isinstance(item, str) or item not in allowed:
                fail(f"{field}[{index}] must be one of {allowed}, got {item!r}")
    else:
        fail(f"{field} has unsupported list item type {item_type!r}")


def validate(template: dict[str, Any], answer: dict[str, Any]) -> None:
    missing = sorted(set(template) - set(answer))
    extra = sorted(set(answer) - set(template))
    if missing:
        fail(f"missing key(s): {', '.join(missing)}")
    if extra:
        fail(f"unexpected key(s): {', '.join(extra)}")

    for field, spec in template.items():
        if not isinstance(spec, dict):
            fail(f"{field} template spec must be an object")
        expected_type = spec.get("type")
        value = answer[field]

        if expected_type == "enum":
            check_enum(field, spec, value)
        elif isinstance(expected_type, str) and expected_type.startswith("list["):
            if not expected_type.endswith("]"):
                fail(f"{field} has malformed list type {expected_type!r}")
            item_type = expected_type[5:-1]
            check_list(field, item_type, spec, value)
        elif isinstance(expected_type, str):
            check_scalar(field, expected_type, value)
        else:
            fail(f"{field} template is missing a string type")


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "Usage: validate_answer.py <answer_template.json> <answer.json>",
            file=sys.stderr,
        )
        return 2

    template = load_json(argv[1])
    answer = load_json(argv[2])
    if not isinstance(template, dict):
        fail("template root must be an object")
    if not isinstance(answer, dict):
        fail("answer root must be an object")

    validate(template, answer)
    print("Answer matches template shape and enum constraints.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
