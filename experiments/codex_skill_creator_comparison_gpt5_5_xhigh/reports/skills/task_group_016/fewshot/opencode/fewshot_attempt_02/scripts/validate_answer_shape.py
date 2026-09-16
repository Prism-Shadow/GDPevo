#!/usr/bin/env python3
"""Validate a draft answer against a synthetic clinic answer template."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def fields_for(spec: dict[str, Any]) -> dict[str, Any]:
    fields = spec.get("fields") or spec.get("field_specification") or spec.get("properties")
    return fields if isinstance(fields, dict) else {}


def required_keys_for(spec: dict[str, Any]) -> list[str]:
    keys = spec.get("required_keys") or spec.get("required_top_level_keys")
    return [key for key in keys if isinstance(key, str)] if isinstance(keys, list) else []


def type_list(type_spec: Any) -> list[str]:
    if isinstance(type_spec, list):
        return [str(item) for item in type_spec]
    if isinstance(type_spec, str):
        aliases = {
            "string_or_null": ["string", "null"],
            "integer_or_null": ["integer", "null"],
            "enum_or_null": ["enum", "null"],
            "list[enum]": ["list"],
            "list[string]": ["list"],
        }
        return aliases.get(type_spec, [type_spec])
    return []


def permits_null(spec: dict[str, Any]) -> bool:
    return bool(spec.get("nullable")) or "null" in type_list(spec.get("type"))


def is_type(value: Any, type_name: str) -> bool:
    if type_name in ("enum",):
        return isinstance(value, str)
    if type_name == "string":
        return isinstance(value, str)
    if type_name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if type_name == "number":
        return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)
    if type_name == "boolean":
        return isinstance(value, bool)
    if type_name in ("object",):
        return isinstance(value, dict)
    if type_name in ("list", "array"):
        return isinstance(value, list)
    if type_name == "null":
        return value is None
    return True


def item_spec_for(spec: dict[str, Any]) -> dict[str, Any]:
    items = spec.get("items")
    if isinstance(items, dict):
        return items
    if isinstance(items, str):
        return {"type": items}
    item_type = spec.get("item_type")
    if isinstance(item_type, str):
        return {"type": item_type, "allowed_values": spec.get("allowed_values")}
    return {}


def no_extra_top_level(template: dict[str, Any]) -> bool:
    text = json.dumps(template).lower()
    if "additional_properties" in template and "ignored" in str(template.get("additional_properties", "")).lower():
        return False
    markers = (
        "do not include extra top-level keys",
        "do not include extra top level keys",
        "extra_keys",
        "exactly one json object with the required keys",
    )
    return any(marker in text for marker in markers)


def validate_value(value: Any, spec: dict[str, Any], path: str, problems: list[str]) -> None:
    if value is None:
        if not permits_null(spec):
            problems.append(f"{path}: null is not permitted")
        return

    expected_types = [item for item in type_list(spec.get("type")) if item != "null"]
    if expected_types and not any(is_type(value, item) for item in expected_types):
        problems.append(f"{path}: expected {' or '.join(expected_types)}, got {type(value).__name__}")
        return

    for constant_key in ("expected_constant", "required_value"):
        if constant_key in spec and value != spec[constant_key]:
            problems.append(f"{path}: expected {spec[constant_key]!r}, got {value!r}")

    allowed = spec.get("allowed_values")
    if isinstance(allowed, list) and not isinstance(value, (list, dict)) and value not in allowed:
        problems.append(f"{path}: {value!r} is not in allowed_values")

    if isinstance(value, list):
        child_spec = item_spec_for(spec)
        child_allowed = child_spec.get("allowed_values")
        for index, item in enumerate(value):
            validate_value(item, child_spec, f"{path}[{index}]", problems)
            if isinstance(child_allowed, list) and item not in child_allowed:
                problems.append(f"{path}[{index}]: {item!r} is not in allowed_values")

    if isinstance(value, dict):
        child_fields = fields_for(spec)
        for key in required_keys_for(spec):
            if key not in value:
                problems.append(f"{path}.{key}: missing required key")
        for key, child_value in value.items():
            child_spec = child_fields.get(key)
            if isinstance(child_spec, dict):
                validate_value(child_value, child_spec, f"{path}.{key}", problems)


def template_top_spec(template: dict[str, Any]) -> dict[str, Any]:
    fields = fields_for(template)
    required = required_keys_for(template) or list(fields)
    return {
        "type": "object",
        "required_keys": required,
        "fields": fields,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, help="Path to answer_template.json")
    parser.add_argument("--answer", required=True, help="Path to draft answer JSON")
    args = parser.parse_args()

    template = load_json(args.template)
    answer = load_json(args.answer)

    problems: list[str] = []
    if not isinstance(template, dict):
        problems.append("template: expected a JSON object")
    if not isinstance(answer, dict):
        problems.append("answer: expected a JSON object")

    if not problems:
        top_spec = template_top_spec(template)
        validate_value(answer, top_spec, "$", problems)
        known_top = set(fields_for(top_spec)) | set(required_keys_for(top_spec))
        if no_extra_top_level(template):
            for key in answer:
                if key not in known_top:
                    problems.append(f"$.{key}: unexpected top-level key")

    result = {
        "ok": not problems,
        "problem_count": len(problems),
        "problems": problems,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
