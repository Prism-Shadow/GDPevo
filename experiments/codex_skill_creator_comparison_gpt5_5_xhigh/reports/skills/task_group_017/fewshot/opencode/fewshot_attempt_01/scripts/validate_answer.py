#!/usr/bin/env python3
"""Validate a draft answer against a task-local answer_template.json."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


ARRAY_SORT_KEYS = {
    "critical_findings": ("finding_id",),
    "category_statuses": ("category_code",),
    "priority_actions": ("priority_rank",),
    "retention_events": ("event_id",),
    "communication_gaps": ("event_id",),
    "available_archives": ("source_id",),
    "recommended_actions": ("priority_rank", "target_id"),
    "top_risks": ("priority_rank",),
    "category_coverage": ("category_code",),
    "retained_or_available_sources": ("source_id",),
    "action_plan": ("rank",),
    "readiness_statuses": ("category_code",),
    "issue_ledger": ("issue_id",),
    "privilege_corrections": ("correction_id",),
}

SORTED_STRING_LIST_KEYS = {
    "affected_categories",
    "blocking_refs",
    "categories_with_any_gap_or_loss",
    "categories_with_open_risk",
    "category_impacts",
    "issue_refs",
    "limits_irretrievable_loss_for_categories",
    "limits_loss_for_categories",
    "record_refs",
    "source_refs",
    "target_refs",
}

ENUM_ALIASES = {
    "recommended_action": "action_type",
    "current_coding": "coding",
    "correction_type": "privilege_correction_type",
}


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def enum_choices(template: dict[str, Any]) -> dict[str, set[Any]]:
    raw = template.get("enums") or template.get("enum_choices") or {}
    return {name: set(values) for name, values in raw.items() if isinstance(values, list)}


def required_item_keys(template: dict[str, Any]) -> dict[str, list[str]]:
    required: dict[str, list[str]] = {}
    fields = template.get("fields")
    if isinstance(fields, dict):
        for name, spec in fields.items():
            if isinstance(spec, dict) and isinstance(spec.get("item_required_keys"), list):
                required[name] = list(spec["item_required_keys"])
    schema = template.get("schema")
    if isinstance(schema, dict):
        for name, spec in schema.items():
            if (
                isinstance(spec, list)
                and spec
                and isinstance(spec[0], dict)
                and name not in required
            ):
                required[name] = list(spec[0].keys())
    return required


def sort_key_for_item(item: Any, keys: tuple[str, ...]) -> tuple[Any, ...]:
    if not isinstance(item, dict):
        return tuple()
    return tuple(item.get(key) for key in keys)


def is_sorted(items: list[Any], keys: tuple[str, ...]) -> bool:
    return items == sorted(items, key=lambda item: sort_key_for_item(item, keys))


def enum_name_for(field: str, path: tuple[str, ...], enums: dict[str, set[Any]]) -> str | None:
    if field in enums:
        return field
    if field in ENUM_ALIASES and ENUM_ALIASES[field] in enums:
        return ENUM_ALIASES[field]
    if field == "status":
        path_text = ".".join(path)
        if "retention_events" in path_text or "communication_gaps" in path_text:
            return "retention_status" if "retention_status" in enums else None
        if "top_risks" in path_text and "risk_status" in enums:
            return "risk_status"
        if "category_coverage" in path_text or "category_statuses" in path_text:
            return "category_status" if "category_status" in enums else None
    return None


def check_recursive(
    value: Any,
    path: tuple[str, ...],
    enums: dict[str, set[Any]],
    issues: list[str],
) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            enum_name = enum_name_for(key, path + (key,), enums)
            if enum_name and child is not None and child not in enums[enum_name]:
                issues.append(
                    f"{'.'.join(path + (key,))}: {child!r} is not in enum {enum_name}"
                )
            check_recursive(child, path + (key,), enums, issues)
    elif isinstance(value, list):
        if path and path[-1] in SORTED_STRING_LIST_KEYS and all(isinstance(x, str) for x in value):
            if value != sorted(value):
                issues.append(f"{'.'.join(path)} is not sorted ascending")
        for index, child in enumerate(value):
            check_recursive(child, path + (str(index),), enums, issues)


def validate(template: dict[str, Any], answer: Any) -> list[str]:
    issues: list[str] = []
    if not isinstance(answer, dict):
        return ["answer must be a JSON object"]

    required_top = template.get("required_top_level_keys")
    if isinstance(required_top, list):
        for key in required_top:
            if key not in answer:
                issues.append(f"missing top-level key: {key}")

    for section, keys in required_item_keys(template).items():
        items = answer.get(section)
        if items is None:
            continue
        if not isinstance(items, list):
            issues.append(f"{section} must be a list")
            continue
        for index, item in enumerate(items):
            if not isinstance(item, dict):
                issues.append(f"{section}[{index}] must be an object")
                continue
            for key in keys:
                if key not in item:
                    issues.append(f"{section}[{index}] missing key: {key}")

    for section, keys in ARRAY_SORT_KEYS.items():
        items = answer.get(section)
        if isinstance(items, list) and not is_sorted(items, keys):
            issues.append(f"{section} is not sorted by {', '.join(keys)}")

    check_recursive(answer, tuple(), enum_choices(template), issues)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", help="Path to input/payloads/answer_template.json")
    parser.add_argument("answer", help="Path to draft answer JSON")
    args = parser.parse_args()

    template = load_json(args.template)
    answer = load_json(args.answer)
    issues = validate(template, answer)
    if issues:
        for issue in issues:
            print(f"FAIL {issue}")
        return 1
    print("OK answer matches the reusable structural checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
