#!/usr/bin/env python3
"""Lightweight checker for Northwind custom answer_template.json files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


META_KEYS = {
    "allowed",
    "allowed_values",
    "contents",
    "description",
    "field_rules",
    "field_types",
    "fields",
    "format",
    "item_fields",
    "item_required_keys",
    "item_type",
    "ordering",
    "precision",
    "required_integer_keys",
    "required_keys",
    "required_top_level_keys",
    "required_value",
    "row_keys",
    "top_level_required_keys",
    "type",
    "unit",
    "units",
    "value_type",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", help="Path to input/payloads/answer_template.json")
    parser.add_argument("answer", help="Path to candidate answer JSON")
    return parser.parse_args()


def load_json(path: str) -> Any:
    try:
        return json.loads(Path(path).read_text())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path} is not valid JSON: {exc}") from exc


def require_keys(value: Any, keys: list[str], path: str, issues: list[str]) -> None:
    if not isinstance(value, dict):
        issues.append(f"{path}: expected object with keys {keys}")
        return
    for key in keys:
        if key not in value:
            issues.append(f"{path}: missing required key {key!r}")


def check_hint(hint: str, value: Any, path: str, issues: list[str]) -> None:
    text = hint.lower()
    if "list" in text:
        if not isinstance(value, list):
            issues.append(f"{path}: expected list from template hint {hint!r}")
        return
    elif "integer" in text and (not isinstance(value, int) or isinstance(value, bool)):
        issues.append(f"{path}: expected integer from template hint {hint!r}")
    elif (
        any(token in text for token in ("number", "currency", "percent"))
        and (not isinstance(value, (int, float)) or isinstance(value, bool))
    ):
        issues.append(f"{path}: expected number from template hint {hint!r}")
    elif ("string" in text or "yyyy-mm-dd" in text) and not isinstance(value, str):
        issues.append(f"{path}: expected string from template hint {hint!r}")


def child_maps(schema: dict[str, Any]) -> list[dict[str, Any]]:
    maps: list[dict[str, Any]] = []
    for key in ("fields", "field_rules", "item_fields", "field_types", "row_keys"):
        value = schema.get(key)
        if isinstance(value, dict):
            maps.append(value)
    return maps


def direct_child_keys(schema: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in schema.items()
        if key not in META_KEYS and isinstance(value, (dict, list, str))
    }


def walk(schema: Any, value: Any, path: str, issues: list[str]) -> None:
    if isinstance(schema, str):
        check_hint(schema, value, path, issues)
        return

    if isinstance(schema, list):
        return

    if not isinstance(schema, dict):
        return

    schema_type = schema.get("type")
    if isinstance(schema_type, str):
        check_hint(schema_type, value, path, issues)

    required = schema.get("required_keys")
    if isinstance(required, list):
        require_keys(value, [str(key) for key in required], path, issues)

    required_ints = schema.get("required_integer_keys")
    if isinstance(required_ints, list):
        keys = [str(key) for key in required_ints]
        require_keys(value, keys, path, issues)
        if isinstance(value, dict):
            for key in keys:
                if key in value and (not isinstance(value[key], int) or isinstance(value[key], bool)):
                    issues.append(f"{path}.{key}: expected integer")

    item_keys = schema.get("item_required_keys")
    if item_keys is None and isinstance(schema.get("row_keys"), dict):
        item_keys = list(schema["row_keys"].keys())
    if isinstance(item_keys, list):
        if not isinstance(value, list):
            issues.append(f"{path}: expected list with item keys {item_keys}")
        else:
            for index, item in enumerate(value):
                item_path = f"{path}[{index}]"
                require_keys(item, [str(key) for key in item_keys], item_path, issues)
                if isinstance(item, dict):
                    for cmap in child_maps(schema):
                        for key, child_schema in cmap.items():
                            if key in item:
                                walk(child_schema, item[key], f"{item_path}.{key}", issues)

    if isinstance(value, dict):
        for cmap in child_maps(schema):
            for key, child_schema in cmap.items():
                if key in value:
                    walk(child_schema, value[key], f"{path}.{key}", issues)

        for key, child_schema in direct_child_keys(schema).items():
            if key not in value:
                issues.append(f"{path}: missing template-described key {key!r}")
            else:
                walk(child_schema, value[key], f"{path}.{key}", issues)


def main() -> int:
    args = parse_args()
    template = load_json(args.template)
    answer = load_json(args.answer)
    issues: list[str] = []

    top_keys: list[str] = []
    if isinstance(template, dict):
        for key_name in ("required_top_level_keys", "top_level_required_keys"):
            value = template.get(key_name)
            if isinstance(value, list):
                top_keys.extend(str(key) for key in value)

    if top_keys:
        require_keys(answer, top_keys, "$", issues)

    walk(template, answer, "$", issues)

    if issues:
        for issue in issues:
            print(issue, file=sys.stderr)
        return 1

    print("template shape check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
