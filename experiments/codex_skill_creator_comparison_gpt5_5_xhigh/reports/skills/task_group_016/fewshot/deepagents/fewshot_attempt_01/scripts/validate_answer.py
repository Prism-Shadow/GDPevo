#!/usr/bin/env python3
"""Validate a clinic protocol JSON answer against the provided template."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"{path}: invalid JSON: {exc}") from exc


def field_specs(template: dict[str, Any]) -> dict[str, Any]:
    return template.get("fields") or template.get("field_specification") or {}


def required_top_keys(template: dict[str, Any]) -> list[str]:
    keys = template.get("required_top_level_keys") or template.get("required_keys") or []
    return [key for key in keys if isinstance(key, str)]


def type_names(spec: dict[str, Any]) -> set[str]:
    raw = spec.get("type")
    if raw is None and spec.get("item_type"):
        raw = spec.get("item_type")
    if isinstance(raw, list):
        return {str(item) for item in raw}
    if isinstance(raw, str):
        aliases = {
            "string_or_null": {"string", "null"},
            "integer_or_null": {"integer", "null"},
            "enum_or_null": {"enum", "null"},
            "list[enum]": {"array"},
            "list[string]": {"array"},
            "list": {"array"},
        }
        return aliases.get(raw, {raw})
    if spec.get("nullable") is True:
        return {"null"}
    return set()


def is_timestamp(value: str, require_z: bool) -> bool:
    if require_z and not value.endswith("Z"):
        return False
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})?$", value))


def allowed_values(spec: dict[str, Any]) -> list[Any] | None:
    values = spec.get("allowed_values")
    if isinstance(values, list):
        return values
    item_spec = spec.get("items")
    if isinstance(item_spec, dict) and isinstance(item_spec.get("allowed_values"), list):
        return item_spec["allowed_values"]
    return None


def check_scalar(value: Any, spec: dict[str, Any], path: str, errors: list[str]) -> None:
    names = type_names(spec)
    constant = spec.get("expected_constant", spec.get("required_value"))
    if constant is not None and value != constant:
        errors.append(f"{path}: expected constant {constant!r}")

    if value is None:
        if "null" not in names and spec.get("nullable") is not True:
            errors.append(f"{path}: null is not permitted")
        return

    allowed = allowed_values(spec)
    if allowed is not None and value not in allowed:
        errors.append(f"{path}: value {value!r} is not in allowed_values")

    if "enum" in names:
        return
    if "string" in names and not isinstance(value, str):
        errors.append(f"{path}: expected string")
    if "integer" in names and (not isinstance(value, int) or isinstance(value, bool)):
        errors.append(f"{path}: expected integer")
    if "number" in names and (not isinstance(value, (int, float)) or isinstance(value, bool)):
        errors.append(f"{path}: expected number")
    if "boolean" in names and not isinstance(value, bool):
        errors.append(f"{path}: expected boolean")

    fmt = str(spec.get("format", ""))
    if isinstance(value, str) and "ISO-8601" in fmt:
        if not is_timestamp(value, "trailing Z" in fmt):
            errors.append(f"{path}: expected ISO-8601 timestamp")


def item_spec(parent: dict[str, Any]) -> dict[str, Any]:
    raw = parent.get("items")
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        return {"type": raw}
    if parent.get("item_type"):
        return {"type": parent["item_type"], "allowed_values": parent.get("allowed_values")}
    raw_type = parent.get("type")
    if raw_type == "list[enum]":
        return {"type": "enum", "allowed_values": parent.get("allowed_values")}
    if raw_type == "list[string]":
        return {"type": "string"}
    return {}


def validate_value(value: Any, spec: dict[str, Any], path: str, errors: list[str]) -> None:
    names = type_names(spec)
    if value is None:
        check_scalar(value, spec, path, errors)
        return

    if "object" in names or spec.get("fields") or spec.get("properties"):
        if not isinstance(value, dict):
            errors.append(f"{path}: expected object")
            return
        child_specs = spec.get("fields") or spec.get("properties") or {}
        for key in spec.get("required_keys", []):
            if key not in value:
                errors.append(f"{path}.{key}: missing required key")
        for key, child_spec in child_specs.items():
            if key in value and isinstance(child_spec, dict):
                validate_value(value[key], child_spec, f"{path}.{key}", errors)
        return

    if "array" in names:
        if not isinstance(value, list):
            errors.append(f"{path}: expected array")
            return
        spec_for_item = item_spec(spec)
        for index, entry in enumerate(value):
            validate_value(entry, spec_for_item, f"{path}[{index}]", errors)
        if len(value) != len({json.dumps(entry, sort_keys=True) for entry in value}):
            errors.append(f"{path}: duplicate entries")
        return

    check_scalar(value, spec, path, errors)


def validate(template: dict[str, Any], answer: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not isinstance(answer, dict):
        return ["answer must be a JSON object"]

    required = required_top_keys(template)
    specs = field_specs(template)

    for key in required:
        if key not in answer:
            errors.append(f"{key}: missing required top-level key")
    extra = sorted(set(answer) - set(required))
    if extra:
        errors.append(f"extra top-level key(s): {', '.join(extra)}")

    for key in required:
        spec = specs.get(key)
        if key in answer and isinstance(spec, dict):
            validate_value(answer[key], spec, key, errors)

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: validate_answer.py <answer_template.json> <answer.json>", file=sys.stderr)
        return 2
    template = load_json(Path(argv[1]))
    answer = load_json(Path(argv[2]))
    errors = validate(template, answer)
    if errors:
        print("Invalid answer:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Answer matches the template structure.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
