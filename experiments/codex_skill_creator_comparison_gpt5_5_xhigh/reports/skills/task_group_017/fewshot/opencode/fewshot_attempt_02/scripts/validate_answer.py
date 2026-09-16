#!/usr/bin/env python3
"""Validate common Review Hub answer-template requirements."""

from __future__ import annotations

import argparse
import json
import re
import sys
from typing import Any


ENUM_RE = re.compile(r"enum[: ]([a-zA-Z0-9_]+)")
SORTED_LIST_KEYS = {
    "affected_categories",
    "category_impacts",
    "blocking_refs",
    "issue_refs",
    "limits_loss_for_categories",
    "limits_irretrievable_loss_for_categories",
    "record_refs",
    "source_refs",
    "target_refs",
    "categories_with_any_gap_or_loss",
    "categories_with_open_risk",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("answer_json", help="Candidate answer JSON file")
    parser.add_argument("answer_template_json", help="Task-local answer_template.json")
    return parser.parse_args()


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def add_missing(errors: list[str], path: str, obj: Any, keys: list[str]) -> None:
    if not isinstance(obj, dict):
        errors.append(f"{path} must be an object")
        return
    for key in keys:
        if key not in obj:
            errors.append(f"{path} missing required key {key!r}")


def enum_name(spec: Any) -> str | None:
    if not isinstance(spec, str):
        return None
    match = ENUM_RE.search(spec)
    return match.group(1) if match else None


def validate_enums(errors: list[str], path: str, obj: Any, specs: dict[str, Any], enums: dict[str, list[str]]) -> None:
    if not isinstance(obj, dict):
        return
    for key, spec in specs.items():
        name = enum_name(spec)
        if name and key in obj and obj[key] is not None and name in enums:
            value = obj[key]
            if isinstance(value, list):
                for index, item in enumerate(value):
                    if item not in enums[name]:
                        errors.append(f"{path}.{key}[{index}] has {item!r}, not in enum {name}")
            elif value not in enums[name]:
                errors.append(f"{path}.{key} has {value!r}, not in enum {name}")


def validate_sorted_lists(errors: list[str], path: str, value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if key in SORTED_LIST_KEYS and isinstance(child, list):
                if child != sorted(child):
                    errors.append(f"{child_path} is not sorted ascending")
                if len(child) != len(set(map(json.dumps, child))):
                    errors.append(f"{child_path} contains duplicate values")
            validate_sorted_lists(errors, child_path, child)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_sorted_lists(errors, f"{path}[{index}]", child)


def validate_integer_counts(errors: list[str], path: str, value: Any) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if (
                key.endswith("_count")
                or key.endswith("_days")
                or key.endswith("_rank")
                or key in {"document_count", "withheld_count", "logged_count", "unlogged_count", "volume_count", "retention_years", "retention_period_months"}
            ):
                if child is not None and (not isinstance(child, int) or isinstance(child, bool)):
                    errors.append(f"{child_path} must be an integer or null")
            validate_integer_counts(errors, child_path, child)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            validate_integer_counts(errors, f"{path}[{index}]", child)


def validate_fields_section(errors: list[str], answer: dict[str, Any], template: dict[str, Any], enums: dict[str, list[str]]) -> None:
    fields = template.get("fields", {})
    if not isinstance(fields, dict):
        return
    for key, spec in fields.items():
        if key not in answer or not isinstance(spec, dict):
            continue
        value = answer[key]
        if "required_keys" in spec:
            add_missing(errors, key, value, spec["required_keys"])
        if "item_required_keys" in spec:
            if not isinstance(value, list):
                errors.append(f"{key} must be a list")
            else:
                item_specs = spec.get("item_fields") or spec.get("item_field_types") or {}
                for index, item in enumerate(value):
                    add_missing(errors, f"{key}[{index}]", item, spec["item_required_keys"])
                    validate_enums(errors, f"{key}[{index}]", item, item_specs, enums)
        if key == "metrics" and isinstance(value, dict):
            required = spec.get("required_keys") or spec.get("field_types", {}).keys()
            add_missing(errors, key, value, list(required))


def validate_schema_section(errors: list[str], answer: dict[str, Any], template: dict[str, Any], enums: dict[str, list[str]]) -> None:
    schema = template.get("schema", {})
    if not isinstance(schema, dict):
        return
    for key, spec in schema.items():
        if key not in answer:
            continue
        value = answer[key]
        if isinstance(spec, list) and spec and isinstance(spec[0], dict):
            if not isinstance(value, list):
                errors.append(f"{key} must be a list")
                continue
            item_specs = spec[0]
            for index, item in enumerate(value):
                add_missing(errors, f"{key}[{index}]", item, list(item_specs.keys()))
                validate_enums(errors, f"{key}[{index}]", item, item_specs, enums)
        elif isinstance(spec, dict):
            add_missing(errors, key, value, list(spec.keys()))


def sorted_key_for(list_name: str) -> str | None:
    return {
        "action_plan": "rank",
        "available_archives": "source_id",
        "category_coverage": "category_code",
        "category_statuses": "category_code",
        "communication_gaps": "event_id",
        "critical_findings": "finding_id",
        "issue_ledger": "issue_id",
        "priority_actions": "priority_rank",
        "privilege_corrections": "correction_id",
        "readiness_statuses": "category_code",
        "recommended_actions": "priority_rank",
        "retained_or_available_sources": "source_id",
        "retention_events": "event_id",
        "top_risks": "priority_rank",
    }.get(list_name)


def validate_list_order(errors: list[str], answer: dict[str, Any]) -> None:
    for key, sort_key in sorted_key_for_map().items():
        value = answer.get(key)
        if not isinstance(value, list) or not value:
            continue
        actual = [item.get(sort_key) if isinstance(item, dict) else None for item in value]
        expected = sorted(actual)
        if actual != expected:
            errors.append(f"{key} is not sorted by {sort_key}")


def sorted_key_for_map() -> dict[str, str]:
    keys = [
        "action_plan",
        "available_archives",
        "category_coverage",
        "category_statuses",
        "communication_gaps",
        "critical_findings",
        "issue_ledger",
        "priority_actions",
        "privilege_corrections",
        "readiness_statuses",
        "recommended_actions",
        "retained_or_available_sources",
        "retention_events",
        "top_risks",
    ]
    return {key: sorted_key_for(key) for key in keys if sorted_key_for(key)}


def main() -> int:
    args = parse_args()
    answer = load_json(args.answer_json)
    template = load_json(args.answer_template_json)
    errors: list[str] = []

    if not isinstance(answer, dict):
        errors.append("answer must be a JSON object")
    else:
        add_missing(errors, "answer", answer, template.get("required_top_level_keys", []))
        enums = template.get("enums") or template.get("enum_choices") or {}
        validate_fields_section(errors, answer, template, enums)
        validate_schema_section(errors, answer, template, enums)
        validate_sorted_lists(errors, "answer", answer)
        validate_integer_counts(errors, "answer", answer)
        validate_list_order(errors, answer)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
