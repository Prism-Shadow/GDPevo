#!/usr/bin/env python3
"""Validate a PeopleOps answer JSON against the staged answer template schema."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterable


def error(messages: list[str], path: str, message: str) -> None:
    messages.append(f"{path}: {message}")


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_number(value: Any) -> bool:
    return (isinstance(value, int) or isinstance(value, float)) and not isinstance(value, bool)


def validate_leaf(schema: dict[str, Any], value: Any, path: str, messages: list[str]) -> None:
    schema_type = schema.get("type")

    if schema_type == "string":
        if not isinstance(value, str):
            error(messages, path, f"expected string, got {type(value).__name__}")
        return

    if schema_type == "number":
        if not is_number(value):
            error(messages, path, f"expected number, got {type(value).__name__}")
        return

    if schema_type == "integer":
        if not is_int(value):
            error(messages, path, f"expected integer, got {type(value).__name__}")
        return

    if schema_type == "boolean":
        if not isinstance(value, bool):
            error(messages, path, f"expected boolean, got {type(value).__name__}")
        return

    if schema_type == "enum":
        allowed = schema.get("allowed_values", [])
        if not isinstance(value, str):
            error(messages, path, f"expected enum string, got {type(value).__name__}")
        elif value not in allowed:
            error(messages, path, f"value {value!r} is not one of {allowed!r}")
        return

    if isinstance(schema_type, str) and schema_type.startswith("list[") and schema_type.endswith("]"):
        if not isinstance(value, list):
            error(messages, path, f"expected list, got {type(value).__name__}")
            return

        item_kind = schema_type[5:-1]
        allowed = schema.get("allowed_values", [])
        for index, item in enumerate(value):
            item_path = f"{path}[{index}]"
            if item_kind == "string":
                if not isinstance(item, str):
                    error(messages, item_path, f"expected string, got {type(item).__name__}")
            elif item_kind == "number":
                if not is_number(item):
                    error(messages, item_path, f"expected number, got {type(item).__name__}")
            elif item_kind == "integer":
                if not is_int(item):
                    error(messages, item_path, f"expected integer, got {type(item).__name__}")
            elif item_kind == "boolean":
                if not isinstance(item, bool):
                    error(messages, item_path, f"expected boolean, got {type(item).__name__}")
            elif item_kind == "enum":
                if not isinstance(item, str):
                    error(messages, item_path, f"expected enum string, got {type(item).__name__}")
                elif item not in allowed:
                    error(messages, item_path, f"value {item!r} is not one of {allowed!r}")
            else:
                error(messages, path, f"unsupported list item type {item_kind!r}")
                break
        return

    if schema_type == "object":
        props = schema.get("properties")
        if props is None:
            error(messages, path, "object schema is missing properties")
            return
        validate_mapping(props, value, path, messages)
        return

    error(messages, path, f"unsupported schema type {schema_type!r}")


def validate_mapping(schema: dict[str, Any], value: Any, path: str, messages: list[str]) -> None:
    if not isinstance(value, dict):
        error(messages, path, f"expected object, got {type(value).__name__}")
        return

    schema_keys = set(schema)
    value_keys = set(value)

    for key in sorted(schema_keys - value_keys):
        error(messages, f"{path}.{key}" if path else key, "missing required key")

    for key in sorted(value_keys - schema_keys):
        error(messages, f"{path}.{key}" if path else key, "unexpected key")

    for key in sorted(schema_keys & value_keys):
        child_path = f"{path}.{key}" if path else key
        child_schema = schema[key]
        child_value = value[key]
        if isinstance(child_schema, dict) and "type" in child_schema:
            validate_leaf(child_schema, child_value, child_path, messages)
        elif isinstance(child_schema, dict):
            validate_mapping(child_schema, child_value, child_path, messages)
        else:
            error(messages, child_path, f"unsupported schema node {type(child_schema).__name__}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: validate_answer.py <answer_template.json> <candidate.json>", file=sys.stderr)
        return 2

    template_path = Path(argv[1])
    candidate_path = Path(argv[2])

    try:
        schema = load_json(template_path)
        candidate = load_json(candidate_path)
    except FileNotFoundError as exc:
        print(f"file not found: {exc.filename}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"invalid JSON in {exc.doc!r}: {exc}", file=sys.stderr)
        return 2

    messages: list[str] = []
    validate_mapping(schema, candidate, "", messages)

    if messages:
        print("validation failed:", file=sys.stderr)
        for message in messages:
            print(f"- {message}", file=sys.stderr)
        return 1

    print("validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
