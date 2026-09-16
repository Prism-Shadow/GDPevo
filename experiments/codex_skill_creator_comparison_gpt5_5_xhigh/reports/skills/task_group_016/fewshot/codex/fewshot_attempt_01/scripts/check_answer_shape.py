#!/usr/bin/env python3
"""Validate a clinic-task answer JSON against the provided answer_template.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def required_top_level(template: dict[str, Any]) -> list[str]:
    for key in ("required_top_level_keys", "required_keys"):
        value = template.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, str)]
    return []


def template_disallows_extra(template: dict[str, Any]) -> bool:
    text = json.dumps(template).lower()
    return "do not include extra" in text or "extra top-level keys" in text


def field_specs(template: dict[str, Any]) -> dict[str, Any]:
    value = template.get("fields") or template.get("field_specification") or {}
    return value if isinstance(value, dict) else {}


def type_names(raw: Any) -> set[str]:
    if isinstance(raw, list):
        return {"null" if item is None else str(item) for item in raw}
    if raw is None:
        return set()
    text = str(raw)
    aliases = {
        "string_or_null": {"string", "null"},
        "enum_or_null": {"enum", "null"},
        "integer_or_null": {"integer", "null"},
        "list[enum]": {"array"},
        "list[string]": {"array"},
        "array": {"array"},
        "list": {"array"},
    }
    return aliases.get(text, {text})


def matches_type(value: Any, spec: dict[str, Any]) -> bool:
    names = type_names(spec.get("type") or spec.get("top_level_type"))
    if not names:
        return True
    if value is None:
        return "null" in names
    checks = {
        "string": isinstance(value, str),
        "enum": isinstance(value, str),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "number": (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
    }
    return any(checks.get(name, True) for name in names if name != "null")


def validate_value(path: str, value: Any, spec: Any, errors: list[str]) -> None:
    if not isinstance(spec, dict):
        return
    if not matches_type(value, spec):
        errors.append(f"{path}: wrong type for spec {spec.get('type')!r}")
        return

    for constant_key in ("required_value", "expected_constant"):
        if constant_key in spec and value != spec[constant_key]:
            errors.append(f"{path}: expected {spec[constant_key]!r}, got {value!r}")

    allowed = spec.get("allowed_values")
    if isinstance(allowed, list) and value not in allowed and not isinstance(value, list):
        errors.append(f"{path}: {value!r} is not in allowed_values")

    if isinstance(value, list):
        item_spec = spec.get("items")
        if item_spec is None and "item_type" in spec:
            item_spec = {"type": spec.get("item_type"), "allowed_values": allowed}
        if isinstance(item_spec, str):
            item_spec = {"type": item_spec}
        for index, item in enumerate(value):
            validate_value(f"{path}[{index}]", item, item_spec, errors)
            if isinstance(allowed, list) and item not in allowed:
                errors.append(f"{path}[{index}]: {item!r} is not in allowed_values")

    if isinstance(value, dict):
        nested_specs = spec.get("fields") or spec.get("properties") or {}
        nested_required = spec.get("required_keys") or []
        if isinstance(nested_required, list):
            for key in nested_required:
                if key not in value:
                    errors.append(f"{path}.{key}: missing required key")
        if isinstance(nested_specs, dict):
            for key, nested_spec in nested_specs.items():
                if key in value:
                    validate_value(f"{path}.{key}", value[key], nested_spec, errors)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", help="Path to answer_template.json")
    parser.add_argument("answer", help="Path to draft answer JSON")
    parser.add_argument("--allow-extra", action="store_true", help="Do not fail on extra top-level keys")
    args = parser.parse_args()

    template = json.loads(Path(args.template).read_text())
    answer = json.loads(Path(args.answer).read_text())
    if not isinstance(template, dict) or not isinstance(answer, dict):
        print("Both template and answer must be JSON objects.", file=sys.stderr)
        return 2

    errors: list[str] = []
    required = required_top_level(template)
    for key in required:
        if key not in answer:
            errors.append(f"{key}: missing required top-level key")

    if template_disallows_extra(template) and not args.allow_extra:
        extras = sorted(set(answer) - set(required))
        for key in extras:
            errors.append(f"{key}: extra top-level key")

    specs = field_specs(template)
    for key, spec in specs.items():
        if key in answer:
            validate_value(key, answer[key], spec, errors)

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Answer shape is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
