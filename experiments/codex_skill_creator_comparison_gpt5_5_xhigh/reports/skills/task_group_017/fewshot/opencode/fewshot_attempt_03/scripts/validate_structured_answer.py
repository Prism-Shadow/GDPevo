#!/usr/bin/env python3
"""Validate common Investigation Review Hub structured JSON answers."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


LIST_FIELDS_TO_CHECK = {
    "affected_categories",
    "category_impacts",
    "source_refs",
    "issue_refs",
    "record_refs",
    "blocking_refs",
    "target_refs",
    "categories_with_open_risk",
    "categories_with_any_gap_or_loss",
    "limits_loss_for_categories",
    "limits_irretrievable_loss_for_categories",
}

SORT_KEYS = (
    "priority_rank",
    "rank",
    "category_code",
    "finding_id",
    "issue_id",
    "correction_id",
    "event_id",
    "source_id",
    "target_id",
    "action_id",
    "risk_id",
)


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def enum_choices(template: dict[str, Any]) -> dict[str, set[Any]]:
    choices: dict[str, set[Any]] = {}
    for section in ("enums", "enum_choices"):
        for name, values in template.get(section, {}).items():
            if isinstance(values, list):
                choices[name] = set(values)
    return choices


def descriptor_enum_name(descriptor: Any) -> str | None:
    if not isinstance(descriptor, str):
        return None
    match = re.search(r"enum[: ]([A-Za-z0-9_]+)", descriptor)
    return match.group(1) if match else None


def list_sort_key(item: Any) -> Any:
    if not isinstance(item, dict):
        return item
    for key in SORT_KEYS:
        if key in item:
            return item[key]
    return json.dumps(item, sort_keys=True)


def is_sorted(values: list[Any]) -> bool:
    return values == sorted(values, key=list_sort_key)


def check_sorted_lists(value: Any, path: str, errors: list[str]) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in LIST_FIELDS_TO_CHECK and isinstance(child, list):
                if child != sorted(child):
                    errors.append(f"{child_path} is not sorted ascending")
                if len(child) != len(set(json.dumps(v, sort_keys=True) for v in child)):
                    errors.append(f"{child_path} contains duplicate values")
            check_sorted_lists(child, child_path, errors)
    elif isinstance(value, list):
        for idx, child in enumerate(value):
            check_sorted_lists(child, f"{path}[{idx}]", errors)


def check_top_level(template: dict[str, Any], answer: dict[str, Any], errors: list[str]) -> None:
    required = template.get("required_top_level_keys", [])
    for key in required:
        if key not in answer:
            errors.append(f"Missing required top-level key: {key}")
    extra = [key for key in answer if required and key not in required]
    if extra:
        errors.append(f"Unexpected top-level keys not listed in template: {', '.join(extra)}")


def check_item_requirements(template: dict[str, Any], answer: dict[str, Any], errors: list[str]) -> None:
    fields = template.get("fields", {})
    for section, spec in fields.items():
        required = spec.get("item_required_keys") if isinstance(spec, dict) else None
        if not required or section not in answer:
            continue
        if not isinstance(answer[section], list):
            errors.append(f"{section} should be a list")
            continue
        for idx, item in enumerate(answer[section]):
            if not isinstance(item, dict):
                errors.append(f"{section}[{idx}] should be an object")
                continue
            for key in required:
                if key not in item:
                    errors.append(f"{section}[{idx}] missing required key: {key}")

    schema = template.get("schema", {})
    for section, prototype in schema.items():
        if not (isinstance(prototype, list) and prototype and isinstance(prototype[0], dict)):
            continue
        if section not in answer:
            continue
        if not isinstance(answer[section], list):
            errors.append(f"{section} should be a list")
            continue
        required = list(prototype[0].keys())
        for idx, item in enumerate(answer[section]):
            if not isinstance(item, dict):
                errors.append(f"{section}[{idx}] should be an object")
                continue
            for key in required:
                if key not in item:
                    errors.append(f"{section}[{idx}] missing required key: {key}")


def check_section_order(answer: dict[str, Any], errors: list[str]) -> None:
    for section, value in answer.items():
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            if not is_sorted(value):
                errors.append(f"{section} is not sorted by its apparent key/rank")


def enum_specs_from_template(template: dict[str, Any]) -> dict[str, dict[str, str]]:
    specs: dict[str, dict[str, str]] = {}

    fields = template.get("fields", {})
    for section, spec in fields.items():
        if not isinstance(spec, dict):
            continue
        item_specs = spec.get("item_field_types") or spec.get("item_fields") or {}
        if isinstance(item_specs, dict):
            for field, descriptor in item_specs.items():
                enum_name = descriptor_enum_name(descriptor)
                if enum_name:
                    specs.setdefault(section, {})[field] = enum_name

    schema = template.get("schema", {})
    for section, prototype in schema.items():
        if isinstance(prototype, list) and prototype and isinstance(prototype[0], dict):
            for field, descriptor in prototype[0].items():
                enum_name = descriptor_enum_name(descriptor)
                if enum_name:
                    specs.setdefault(section, {})[field] = enum_name
    return specs


def check_enums(template: dict[str, Any], answer: dict[str, Any], errors: list[str]) -> None:
    choices = enum_choices(template)
    specs = enum_specs_from_template(template)
    for section, field_specs in specs.items():
        items = answer.get(section)
        if not isinstance(items, list):
            continue
        for idx, item in enumerate(items):
            if not isinstance(item, dict):
                continue
            for field, enum_name in field_specs.items():
                if field not in item or item[field] is None:
                    continue
                allowed = choices.get(enum_name)
                if allowed is None:
                    continue
                values = item[field] if isinstance(item[field], list) else [item[field]]
                for value in values:
                    if value not in allowed:
                        errors.append(f"{section}[{idx}].{field} contains {value!r}, not in enum {enum_name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True)
    parser.add_argument("--answer", required=True)
    args = parser.parse_args()

    template = load_json(args.template)
    answer = load_json(args.answer)
    if not isinstance(template, dict) or not isinstance(answer, dict):
        print("Template and answer must both be JSON objects", file=sys.stderr)
        return 1

    errors: list[str] = []
    check_top_level(template, answer, errors)
    check_item_requirements(template, answer, errors)
    check_section_order(answer, errors)
    check_sorted_lists(answer, "", errors)
    check_enums(template, answer, errors)

    if errors:
        print("Validation failed:", file=sys.stderr)
        for err in errors:
            print(f"- {err}", file=sys.stderr)
        return 1

    print("Validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
