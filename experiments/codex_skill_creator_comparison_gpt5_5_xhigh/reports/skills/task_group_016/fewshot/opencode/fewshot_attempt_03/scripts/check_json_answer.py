#!/usr/bin/env python3
"""Lightweight structural checker for synthetic clinic answer templates.

This is not a substitute for clinical reasoning. It catches common mistakes:
invalid JSON, missing required keys, extra top-level keys when disallowed,
wrong primitive types, enum values not listed in the template, and nulls where
the template does not allow them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def template_required_top(template: dict[str, Any]) -> list[str]:
    if isinstance(template.get("required_top_level_keys"), list):
        return list(template["required_top_level_keys"])
    if isinstance(template.get("required_keys"), list):
        return list(template["required_keys"])
    return []


def template_fields(template: dict[str, Any]) -> dict[str, Any]:
    for key in ("fields", "field_specification"):
        if isinstance(template.get(key), dict):
            return template[key]
    return {}


def allows_extra_top(template: dict[str, Any]) -> bool:
    if template.get("additional_properties") is not None:
        value = template.get("additional_properties")
        if isinstance(value, bool):
            return value
        return False
    output_rules = template.get("output_rules")
    if isinstance(output_rules, dict) and "extra_keys" in output_rules:
        return False
    fmt = template.get("format")
    if isinstance(fmt, str) and "extra top-level keys" in fmt.lower():
        return False
    return False


def type_names(spec: dict[str, Any]) -> set[str]:
    raw = spec.get("type", spec.get("top_level_type"))
    if raw is None:
        raw = spec.get("item_type")
    if isinstance(raw, list):
        names = {str(item) for item in raw}
    elif isinstance(raw, str):
        names = {raw}
    else:
        names = set()
    normalized: set[str] = set()
    for name in names:
        if name == "list[enum]":
            normalized.add("list")
            normalized.add("enum")
        elif name == "list[string]":
            normalized.add("list")
            normalized.add("string")
        elif name == "array":
            normalized.add("list")
        elif name == "object":
            normalized.add("object")
        elif name == "string_or_null":
            normalized.update({"string", "null"})
        elif name == "integer_or_null":
            normalized.update({"integer", "null"})
        elif name == "enum_or_null":
            normalized.update({"enum", "null"})
        else:
            normalized.add(name)
    if spec.get("nullable") is True:
        normalized.add("null")
    return normalized


def is_allowed_type(value: Any, names: set[str]) -> bool:
    if not names:
        return True
    if value is None:
        return "null" in names
    checks = {
        "string": isinstance(value, str),
        "enum": isinstance(value, str),
        "number": isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "list": isinstance(value, list),
        "array": isinstance(value, list),
        "object": isinstance(value, dict),
    }
    return any(checks.get(name, False) for name in names if name != "null")


def child_fields(spec: dict[str, Any]) -> dict[str, Any]:
    for key in ("fields", "properties"):
        if isinstance(spec.get(key), dict):
            return spec[key]
    return {}


def required_keys(spec: dict[str, Any]) -> list[str]:
    keys = spec.get("required_keys")
    return list(keys) if isinstance(keys, list) else []


def validate_value(value: Any, spec: dict[str, Any], path: str, errors: list[str]) -> None:
    names = type_names(spec)
    if not is_allowed_type(value, names):
        errors.append(f"{path}: expected {sorted(names)}, got {type(value).__name__}")
        return
    if value is None:
        return

    allowed_values = spec.get("allowed_values")
    if isinstance(allowed_values, list):
        if isinstance(value, list):
            for index, item in enumerate(value):
                if item not in allowed_values:
                    errors.append(f"{path}[{index}]: value {item!r} not in allowed_values")
        elif value not in allowed_values:
            errors.append(f"{path}: value {value!r} not in allowed_values")

    if isinstance(value, dict):
        fields = child_fields(spec)
        for key in required_keys(spec):
            if key not in value:
                errors.append(f"{path}.{key}: missing required key")
        for key, child_spec in fields.items():
            if key in value and isinstance(child_spec, dict):
                validate_value(value[key], child_spec, f"{path}.{key}", errors)

    if isinstance(value, list):
        item_spec = spec.get("items")
        if isinstance(item_spec, dict):
            for index, item in enumerate(value):
                validate_value(item, item_spec, f"{path}[{index}]", errors)
        elif isinstance(item_spec, str):
            for index, item in enumerate(value):
                if item_spec == "string" and not isinstance(item, str):
                    errors.append(f"{path}[{index}]: expected string")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check answer JSON against a provided answer_template.json.")
    parser.add_argument("template", type=Path)
    parser.add_argument("answer", type=Path)
    args = parser.parse_args()

    template = load_json(args.template)
    answer = load_json(args.answer)
    if not isinstance(template, dict):
        print("Template root is not an object", file=sys.stderr)
        return 2
    if not isinstance(answer, dict):
        print("Answer root is not an object", file=sys.stderr)
        return 2

    errors: list[str] = []
    required = template_required_top(template)
    fields = template_fields(template)

    for key in required:
        if key not in answer:
            errors.append(f"{key}: missing required top-level key")

    if not allows_extra_top(template):
        extras = sorted(set(answer) - set(required))
        if extras:
            errors.append(f"extra top-level keys: {extras}")

    for key, spec in fields.items():
        if key in answer and isinstance(spec, dict):
            validate_value(answer[key], spec, key, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
