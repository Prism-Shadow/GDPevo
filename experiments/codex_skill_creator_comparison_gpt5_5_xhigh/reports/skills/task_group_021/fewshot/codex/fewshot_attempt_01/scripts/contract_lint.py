#!/usr/bin/env python3
"""Lightweight JSON answer contract checks without third-party packages."""

import json
import re
import sys


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def type_ok(value, expected):
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


def check_schema(schema, value, path, errors):
    if not isinstance(schema, dict):
        return
    expected = schema.get("type")
    if expected and not type_ok(value, expected):
        errors.append(f"{path}: expected {expected}, got {type(value).__name__}")
        return
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value {value!r} not in enum")
    if isinstance(value, str) and schema.get("pattern"):
        if not re.search(schema["pattern"], value):
            errors.append(f"{path}: value {value!r} does not match pattern")
    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{path}: too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{path}: too many items")
        if schema.get("uniqueItems"):
            seen = set()
            for item in value:
                marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if marker in seen:
                    errors.append(f"{path}: duplicate array item {item!r}")
                    break
                seen.add(marker)
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                check_schema(item_schema, item, f"{path}[{index}]", errors)
    if isinstance(value, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}: missing required key {key!r}")
        props = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            extra = sorted(set(value) - set(props))
            if extra:
                errors.append(f"{path}: extra key(s) {', '.join(extra)}")
        for key, prop_schema in props.items():
            if key in value:
                check_schema(prop_schema, value[key], f"{path}.{key}", errors)


def check_custom_template(template, value, errors):
    if not isinstance(value, dict):
        errors.append("$: answer must be an object")
        return
    required = template.get("required_top_level_keys", [])
    for key in required:
        if key not in value:
            errors.append(f"$: missing required top-level key {key!r}")
    if template.get("additional_top_level_keys_allowed") is False:
        extra = sorted(set(value) - set(required))
        if extra:
            errors.append(f"$: extra top-level key(s) {', '.join(extra)}")
    contracts = template.get("field_contract", {})
    for key, spec in contracts.items():
        if key not in value or not isinstance(spec, dict):
            continue
        required_keys = spec.get("required_keys")
        if required_keys and isinstance(value[key], dict):
            for req in required_keys:
                if req not in value[key]:
                    errors.append(f"$.{key}: missing required key {req!r}")
        item_required = spec.get("item_required_keys")
        if item_required and isinstance(value[key], list):
            for index, item in enumerate(value[key]):
                if not isinstance(item, dict):
                    errors.append(f"$.{key}[{index}]: expected object")
                    continue
                for req in item_required:
                    if req not in item:
                        errors.append(f"$.{key}[{index}]: missing required key {req!r}")
        length = spec.get("length")
        if length is not None and isinstance(value[key], list) and len(value[key]) != length:
            errors.append(f"$.{key}: expected length {length}, got {len(value[key])}")


def main():
    if len(sys.argv) != 3:
        print("Usage: contract_lint.py <answer_template.json> <answer.json>", file=sys.stderr)
        return 2
    template = load_json(sys.argv[1])
    answer = load_json(sys.argv[2])
    errors = []
    if "$schema" in template and "properties" in template:
        check_schema(template, answer, "$", errors)
    else:
        check_custom_template(template, answer, errors)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
