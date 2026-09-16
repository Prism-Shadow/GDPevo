#!/usr/bin/env python3
"""Lightweight checker for Northstar answer_template.json top-level shape."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


TOP_LEVEL_KEYS = (
    "required_top_level_fields",
    "required_top_level_keys",
    "top_level_required_keys",
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def required_top_level(template: dict[str, Any]) -> list[str]:
    for key in TOP_LEVEL_KEYS:
        value = template.get(key)
        if isinstance(value, list):
            return [str(item) for item in value]
    return []


def additional_fields_allowed(template: dict[str, Any]) -> bool:
    if template.get("additional_fields_allowed") is False:
        return False
    additional = template.get("additional_properties")
    if additional is False:
        return False
    if isinstance(additional, str) and "not allowed" in additional.lower():
        return False
    return True


def field_definitions(template: dict[str, Any]) -> dict[str, Any]:
    merged: dict[str, Any] = {}
    for key in ("fields", "field_definitions"):
        value = template.get(key)
        if isinstance(value, dict):
            merged.update(value)
    return merged


def required_nested(definition: dict[str, Any]) -> list[str]:
    for key in ("required_fields", "required_keys", "object_required_keys"):
        value = definition.get(key)
        if isinstance(value, list):
            return [str(item) for item in value]
    return []


def check_nested(answer: dict[str, Any], fields: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for name, definition in fields.items():
        if name not in answer or not isinstance(definition, dict):
            continue
        required = required_nested(definition)
        if required and isinstance(answer[name], dict):
            missing = [key for key in required if key not in answer[name]]
            if missing:
                errors.append(f"{name} missing nested keys: {', '.join(missing)}")
        elif required and isinstance(answer[name], list):
            for index, item in enumerate(answer[name]):
                if not isinstance(item, dict):
                    errors.append(f"{name}[{index}] is not an object")
                    continue
                missing = [key for key in required if key not in item]
                if missing:
                    errors.append(f"{name}[{index}] missing keys: {', '.join(missing)}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Check answer JSON against the top-level template contract.")
    parser.add_argument("template", type=Path)
    parser.add_argument("answer", type=Path)
    args = parser.parse_args()

    template = load_json(args.template)
    answer = load_json(args.answer)
    if not isinstance(template, dict):
        print("template root is not an object", file=sys.stderr)
        return 1
    if not isinstance(answer, dict):
        print("answer root is not an object", file=sys.stderr)
        return 1

    errors: list[str] = []
    required = required_top_level(template)
    missing = [key for key in required if key not in answer]
    if missing:
        errors.append(f"missing top-level keys: {', '.join(missing)}")

    if required and not additional_fields_allowed(template):
        unexpected = [key for key in answer if key not in required]
        if unexpected:
            errors.append(f"unexpected top-level keys: {', '.join(unexpected)}")

    errors.extend(check_nested(answer, field_definitions(template)))

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("Template check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
