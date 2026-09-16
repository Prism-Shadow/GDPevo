#!/usr/bin/env python3
"""Validate a JSON answer against the task's answer_template.json.

The staged templates are lightweight contracts rather than full JSON Schema
documents, so this checker focuses on high-value mistakes: missing keys, enum
typos, non-integer counts, and sorting issues.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


SORT_KEYS = {
    "critical_findings": ("finding_id",),
    "retention_events": ("event_id",),
    "communication_gaps": ("event_id",),
    "available_archives": ("source_id",),
    "top_risks": ("priority_rank",),
    "category_statuses": ("category_code",),
    "category_coverage": ("category_code",),
    "readiness_statuses": ("category_code",),
    "retained_or_available_sources": ("source_id",),
    "issue_ledger": ("issue_id",),
    "privilege_corrections": ("correction_id",),
    "recommended_actions": ("priority_rank", "target_id"),
    "priority_actions": ("priority_rank",),
    "action_plan": ("rank",),
}


REF_LIST_KEYS = {
    "source_refs",
    "issue_refs",
    "record_refs",
    "target_refs",
    "blocking_refs",
}


CATEGORY_LIST_KEYS = {
    "affected_categories",
    "category_impacts",
    "category_sets",
    "categories_with_open_risk",
    "categories_with_any_gap_or_loss",
    "limits_loss_for_categories",
    "limits_irretrievable_loss_for_categories",
}


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def enum_sets(template: dict[str, Any]) -> dict[str, set[str]]:
    raw = template.get("enums") or template.get("enum_choices") or {}
    return {name: set(values) for name, values in raw.items() if isinstance(values, list)}


def enum_ref(text: Any) -> str | None:
    if not isinstance(text, str):
        return None
    match = re.search(r"enum[: ]([A-Za-z0-9_]+)", text)
    return match.group(1) if match else None


def expects_integer(text: Any) -> bool:
    return isinstance(text, str) and "integer" in text.lower()


def top_field_contract(template: dict[str, Any], key: str) -> dict[str, Any]:
    fields = template.get("fields")
    if isinstance(fields, dict) and isinstance(fields.get(key), dict):
        return fields[key]
    schema = template.get("schema")
    if isinstance(schema, dict):
        value = schema.get(key)
        if isinstance(value, list) and value and isinstance(value[0], dict):
            return {
                "item_required_keys": list(value[0].keys()),
                "item_fields": value[0],
                "item_field_types": value[0],
            }
        if isinstance(value, dict):
            return {"required_keys": list(value.keys()), "field_types": value}
        if isinstance(value, str):
            return {"type": value}
    return {}


def item_field_defs(contract: dict[str, Any]) -> dict[str, Any]:
    for key in ("item_field_types", "item_fields"):
        value = contract.get(key)
        if isinstance(value, dict):
            return value
    return {}


def metric_field_defs(contract: dict[str, Any]) -> dict[str, Any]:
    value = contract.get("field_types")
    return value if isinstance(value, dict) else {}


def check_required_keys(
    answer: dict[str, Any],
    template: dict[str, Any],
    errors: list[str],
) -> None:
    required = template.get("required_top_level_keys")
    if not isinstance(required, list):
        return
    missing = [key for key in required if key not in answer]
    extra = [key for key in answer if key not in required]
    if missing:
        errors.append(f"Missing top-level keys: {missing}")
    if extra:
        errors.append(f"Unexpected top-level keys: {extra}")


def check_object_required(
    path: str,
    obj: Any,
    required: list[str],
    errors: list[str],
) -> None:
    if not isinstance(obj, dict):
        errors.append(f"{path} must be an object")
        return
    missing = [key for key in required if key not in obj]
    if missing:
        errors.append(f"{path} missing keys: {missing}")


def check_sorted_list(path: str, values: Any, errors: list[str]) -> None:
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        return
    sorted_values = sorted(values)
    if values != sorted_values:
        errors.append(f"{path} is not sorted ascending: {values}")


def sort_tuple(item: Any, keys: tuple[str, ...]) -> tuple[Any, ...]:
    if not isinstance(item, dict):
        return tuple()
    return tuple(item.get(key) for key in keys)


def check_section_sort(
    key: str,
    section: Any,
    errors: list[str],
) -> None:
    keys = SORT_KEYS.get(key)
    if not keys or not isinstance(section, list):
        return
    actual = [sort_tuple(item, keys) for item in section]
    expected = sorted(actual)
    if actual != expected:
        errors.append(f"{key} is not sorted by {keys}: {actual}")


def check_enum_value(
    path: str,
    value: Any,
    enum_name: str,
    enums: dict[str, set[str]],
    errors: list[str],
) -> None:
    allowed = enums.get(enum_name)
    if not allowed:
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            if item not in allowed:
                errors.append(f"{path}[{index}] has invalid enum {item!r}; expected {enum_name}")
    elif value not in allowed:
        errors.append(f"{path} has invalid enum {value!r}; expected {enum_name}")


def validate_field_values(
    path: str,
    obj: dict[str, Any],
    field_defs: dict[str, Any],
    enums: dict[str, set[str]],
    errors: list[str],
) -> None:
    for key, descriptor in field_defs.items():
        if key not in obj:
            continue
        value = obj[key]
        ref = enum_ref(descriptor)
        if ref:
            check_enum_value(f"{path}.{key}", value, ref, enums, errors)
        if expects_integer(descriptor) and value is not None:
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"{path}.{key} must be an integer or null, got {type(value).__name__}")
        if key in CATEGORY_LIST_KEYS or key in REF_LIST_KEYS:
            check_sorted_list(f"{path}.{key}", value, errors)


def walk_nested_lists(path: str, obj: Any, errors: list[str]) -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            child_path = f"{path}.{key}" if path else key
            if key in CATEGORY_LIST_KEYS or key in REF_LIST_KEYS:
                check_sorted_list(child_path, value, errors)
            walk_nested_lists(child_path, value, errors)
    elif isinstance(obj, list):
        for index, item in enumerate(obj):
            walk_nested_lists(f"{path}[{index}]", item, errors)


def validate_answer(template: dict[str, Any], answer: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(template, dict):
        return ["Template must be a JSON object"]
    if not isinstance(answer, dict):
        return ["Answer must be a JSON object"]

    enums = enum_sets(template)
    check_required_keys(answer, template, errors)

    for top_key, section in answer.items():
        contract = top_field_contract(template, top_key)
        check_section_sort(top_key, section, errors)

        if isinstance(section, list):
            required = contract.get("item_required_keys")
            if not isinstance(required, list):
                required = []
            field_defs = item_field_defs(contract)
            for index, item in enumerate(section):
                path = f"{top_key}[{index}]"
                if required:
                    check_object_required(path, item, required, errors)
                if isinstance(item, dict):
                    validate_field_values(path, item, field_defs, enums, errors)

        elif isinstance(section, dict):
            required = contract.get("required_keys")
            if isinstance(required, list):
                check_object_required(top_key, section, required, errors)
            validate_field_values(top_key, section, metric_field_defs(contract), enums, errors)

    walk_nested_lists("", answer, errors)
    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--template", required=True, help="Path to input/payloads/answer_template.json")
    parser.add_argument("--answer", required=True, help="Path to candidate answer JSON")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        template = load_json(args.template)
        answer = load_json(args.answer)
    except Exception as exc:  # noqa: BLE001 - convert JSON/file errors to clear CLI output.
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    errors = validate_answer(template, answer)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("Template validation passed.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
