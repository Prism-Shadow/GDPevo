#!/usr/bin/env python3
"""Lightweight validator for clinic answer_template.json files."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def top_required(template: dict[str, Any]) -> list[str]:
    for key in ("required_top_level_keys", "required_keys"):
        value = template.get(key)
        if isinstance(value, list):
            return [str(item) for item in value]
    return []


def field_specs(template: dict[str, Any]) -> dict[str, Any]:
    for key in ("fields", "field_specification", "properties"):
        value = template.get(key)
        if isinstance(value, dict):
            return value
    return {}


def allows_null(spec: dict[str, Any]) -> bool:
    typ = spec.get("type")
    if typ is None:
        return True
    if isinstance(typ, list):
        return "null" in typ or None in typ
    return str(typ).endswith("_or_null") or str(typ) == "nullable"


def allowed_values(spec: dict[str, Any]) -> list[Any] | None:
    values = spec.get("allowed_values")
    if isinstance(values, list):
        return values
    items = spec.get("items")
    if isinstance(items, dict) and isinstance(items.get("allowed_values"), list):
        return items["allowed_values"]
    return None


def nested_required(spec: dict[str, Any]) -> list[str]:
    value = spec.get("required_keys")
    if isinstance(value, list):
        return [str(item) for item in value]
    return []


def nested_fields(spec: dict[str, Any]) -> dict[str, Any]:
    for key in ("fields", "properties"):
        value = spec.get(key)
        if isinstance(value, dict):
            return value
    return {}


def validate_value(path: str, value: Any, spec: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    if value is None:
        if not allows_null(spec):
            errors.append(f"{path}: null is not permitted")
        return

    expected_constant = spec.get("expected_constant", spec.get("required_value"))
    if expected_constant is not None and value != expected_constant:
        errors.append(f"{path}: expected constant {expected_constant!r}, got {value!r}")

    allowed = allowed_values(spec)
    if allowed is not None:
        if isinstance(value, list):
            bad = [item for item in value if item not in allowed]
            if bad:
                errors.append(f"{path}: values not in allowed_values: {bad!r}")
        elif value not in allowed:
            errors.append(f"{path}: value {value!r} not in allowed_values")

    if isinstance(value, list):
        if len(value) != len(set(json.dumps(item, sort_keys=True) for item in value)):
            warnings.append(f"{path}: list contains duplicates")
        item_spec = spec.get("items")
        if isinstance(item_spec, dict):
            for idx, item in enumerate(value):
                validate_value(f"{path}[{idx}]", item, item_spec, errors, warnings)

    if isinstance(value, dict):
        for key in nested_required(spec):
            if key not in value:
                errors.append(f"{path}: missing required nested key {key!r}")
        for key, child_spec in nested_fields(spec).items():
            if key in value and isinstance(child_spec, dict):
                validate_value(f"{path}.{key}", value[key], child_spec, errors, warnings)


def extras_disallowed(template: dict[str, Any]) -> bool:
    text = json.dumps(template).lower()
    return (
        "do not include extra top-level keys" in text
        or "extra top-level keys" in text
        or "extra_keys" in text
    ) and "ignored by the evaluator" not in text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("template")
    parser.add_argument("answer")
    args = parser.parse_args()

    template = load_json(args.template)
    answer = load_json(args.answer)
    if not isinstance(template, dict):
        raise SystemExit("Template must be a JSON object")
    if not isinstance(answer, dict):
        raise SystemExit("Answer must be a JSON object")

    errors: list[str] = []
    warnings: list[str] = []
    required = top_required(template)
    for key in required:
        if key not in answer:
            errors.append(f"$: missing required top-level key {key!r}")

    if extras_disallowed(template):
        extra = sorted(set(answer) - set(required))
        if extra:
            errors.append(f"$: extra top-level keys: {extra!r}")
    else:
        extra = sorted(set(answer) - set(required))
        if extra:
            warnings.append(f"$: extra top-level keys present: {extra!r}")

    specs = field_specs(template)
    for key, spec in specs.items():
        if key in answer and isinstance(spec, dict):
            validate_value(f"$.{key}", answer[key], spec, errors, warnings)

    report = {"errors": errors, "warnings": warnings}
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
