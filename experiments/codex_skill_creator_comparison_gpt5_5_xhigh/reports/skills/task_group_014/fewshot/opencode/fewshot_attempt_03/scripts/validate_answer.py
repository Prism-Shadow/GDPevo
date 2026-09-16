#!/usr/bin/env python3
"""Lightweight structural checker for Northstar answer_template JSON files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_TOP_LEVEL_KEYS = (
    "required_top_level_fields",
    "required_top_level_keys",
    "top_level_required_keys",
)


def load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def required_keys(spec: dict[str, Any]) -> list[str]:
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if isinstance(spec.get(key), list):
            return list(spec[key])
    return []


def nested_required_keys(spec: dict[str, Any]) -> list[str]:
    keys: list[str] = []
    for name in ("required_fields", "required_keys", "object_required_keys", "item_required_keys"):
        value = spec.get(name)
        if isinstance(value, list):
            keys.extend(str(item) for item in value)
    return keys


def enum_values(spec: dict[str, Any]) -> list[Any] | None:
    for name in ("choices", "value_choices", "value_enum"):
        value = spec.get(name)
        if isinstance(value, list):
            return value
    return None


def child_specs(spec: dict[str, Any]) -> dict[str, Any]:
    children: dict[str, Any] = {}
    for name in ("field_definitions", "fields", "line_field_definitions", "item_fields"):
        value = spec.get(name)
        if isinstance(value, dict):
            children.update(value)
    return children


def validate_value(value: Any, spec: dict[str, Any], path: str, errors: list[str]) -> None:
    choices = enum_values(spec)
    if choices is not None and not isinstance(value, (dict, list)) and value not in choices:
        errors.append(f"{path}: value {value!r} not in enum {choices!r}")

    if isinstance(value, dict):
        for key in nested_required_keys(spec):
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")

        value_choices = spec.get("value_choices") or spec.get("value_enum")
        if isinstance(value_choices, list):
            for key, item in value.items():
                if item not in value_choices:
                    errors.append(f"{path}.{key}: value {item!r} not in enum {value_choices!r}")

        for key, child_spec in child_specs(spec).items():
            if key in value and isinstance(child_spec, dict):
                validate_value(value[key], child_spec, f"{path}.{key}", errors)

    if isinstance(value, list):
        item_choices = enum_values(spec)
        if item_choices is not None:
            for index, item in enumerate(value):
                if item not in item_choices:
                    errors.append(f"{path}[{index}]: value {item!r} not in enum {item_choices!r}")

        item_required = nested_required_keys(spec)
        for index, item in enumerate(value):
            if isinstance(item, dict):
                for key in item_required:
                    if key not in item:
                        errors.append(f"{path}[{index}]: missing required key {key!r}")
                for key, child_spec in child_specs(spec).items():
                    if key in item and isinstance(child_spec, dict):
                        validate_value(item[key], child_spec, f"{path}[{index}].{key}", errors)


def validate(template: dict[str, Any], answer: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    top_required = required_keys(template)
    for key in top_required:
        if key not in answer:
            errors.append(f"$: missing required top-level key {key!r}")

    if template.get("additional_fields_allowed") is False:
        extras = sorted(set(answer) - set(top_required))
        if extras:
            errors.append(f"$: disallowed top-level extra keys {extras!r}")

    top_specs = child_specs(template)
    for key, spec in top_specs.items():
        if key in answer and isinstance(spec, dict):
            validate_value(answer[key], spec, f"$.{key}", errors)

    allowed_enums = template.get("allowed_enums")
    if isinstance(allowed_enums, dict):
        for key, choices in allowed_enums.items():
            if key in answer and isinstance(choices, list) and answer[key] not in choices:
                errors.append(f"$.{key}: value {answer[key]!r} not in enum {choices!r}")

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: validate_answer.py <answer_template.json> <answer.json>", file=sys.stderr)
        return 2

    template = load_json(argv[1])
    answer = load_json(argv[2])
    if not isinstance(template, dict) or not isinstance(answer, dict):
        print("template and answer must both be JSON objects", file=sys.stderr)
        return 2

    errors = validate(template, answer)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("template structure check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
