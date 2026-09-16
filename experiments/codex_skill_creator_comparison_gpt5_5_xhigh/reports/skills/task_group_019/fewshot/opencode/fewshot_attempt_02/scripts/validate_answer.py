#!/usr/bin/env python3
"""Lightweight validator for licensing answer_template.json files."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def template_top_keys(template: Dict[str, Any]) -> Optional[List[str]]:
    if isinstance(template.get("required_top_level_keys"), list):
        return list(template["required_top_level_keys"])
    if isinstance(template.get("top_level_keys"), dict):
        return list(template["top_level_keys"].keys())
    instructions = template.get("instructions")
    if isinstance(instructions, dict) and isinstance(instructions.get("top_level_keys"), list):
        return list(instructions["top_level_keys"])
    return None


def item_spec_for(template: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    if key == "application_decisions":
        top = template.get("top_level_keys", {}).get("application_decisions", {})
        if isinstance(top, dict) and isinstance(top.get("item_schema"), dict):
            return top["item_schema"]
        if isinstance(template.get("application_decisions_item"), dict):
            return template["application_decisions_item"]
    if key == "queue":
        queue = template.get("queue", {})
        if isinstance(queue, dict) and isinstance(queue.get("item"), dict):
            return queue["item"]
    return None


def summary_spec(template: Dict[str, Any]) -> Dict[str, Any]:
    summary = template.get("summary")
    if not isinstance(summary, dict):
        return {}
    if isinstance(summary.get("required_keys"), dict):
        return summary["required_keys"]
    if isinstance(summary.get("fields"), dict):
        return summary["fields"]
    return {}


def field_specs(template: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(template.get("schema"), dict):
        return template["schema"]
    if isinstance(template.get("field_definitions"), dict):
        return template["field_definitions"]
    return {}


def allowed_values(spec: Dict[str, Any]) -> Optional[List[Any]]:
    values = spec.get("allowed_values")
    if isinstance(values, list):
        return values
    items = spec.get("items")
    if isinstance(items, dict) and isinstance(items.get("allowed_values"), list):
        return items["allowed_values"]
    return None


def required_child_keys(spec: Dict[str, Any]) -> List[str]:
    keys = spec.get("required_keys")
    if isinstance(keys, list):
        return keys
    if isinstance(keys, dict):
        return list(keys.keys())
    return []


def child_specs(spec: Dict[str, Any]) -> Dict[str, Any]:
    for key in ("properties", "fields", "item_schema"):
        value = spec.get(key)
        if isinstance(value, dict):
            return value
    return {}


def type_name(spec: Dict[str, Any]) -> str:
    value = spec.get("type")
    return value if isinstance(value, str) else ""


def wants_lexical_sorted(spec: Dict[str, Any]) -> bool:
    ordering = spec.get("ordering")
    if not isinstance(ordering, str):
        return False
    text = ordering.lower()
    if "violation date" in text:
        return False
    return (
        ("sort" in text and "ascending" in text and "code" in text)
        or "lexical" in text
        or "alphabetically" in text
        or "license numbers ascending" in text
        or "application ids ascending" in text
        or "violation_id ascending" in text
    )


def object_sort_field(spec: Dict[str, Any]) -> Optional[str]:
    ordering = spec.get("ordering")
    if not isinstance(ordering, str):
        return None
    text = ordering.lower()
    if "check_code" in text:
        return "check_code"
    if "rank" in text:
        return "rank"
    return None


def has_duplicates(values: Iterable[Any]) -> bool:
    seen = set()
    for value in values:
        marker = json.dumps(value, sort_keys=True)
        if marker in seen:
            return True
        seen.add(marker)
    return False


def validate_value(value: Any, spec: Dict[str, Any], path: str, errors: List[str]) -> None:
    expected = type_name(spec)
    allowed = allowed_values(spec)

    if expected in {"string", "enum"} and not isinstance(value, str):
        errors.append(f"{path}: expected string")
    if expected == "integer" and not isinstance(value, int):
        errors.append(f"{path}: expected integer")
    if expected == "boolean" and not isinstance(value, bool):
        errors.append(f"{path}: expected boolean")

    if allowed is not None and not isinstance(value, list) and value not in allowed:
        errors.append(f"{path}: value {value!r} not in allowed_values")

    if expected.startswith("list") or expected == "array" or "items" in spec:
        if not isinstance(value, list):
            errors.append(f"{path}: expected list")
            return
        if has_duplicates(value):
            errors.append(f"{path}: contains duplicate items")
        if wants_lexical_sorted(spec) and all(isinstance(item, str) for item in value) and value != sorted(value):
            errors.append(f"{path}: expected ascending sort order")
        sort_field = object_sort_field(spec)
        if sort_field and all(isinstance(item, dict) and sort_field in item for item in value):
            if value != sorted(value, key=lambda item: item[sort_field]):
                errors.append(f"{path}: expected ascending sort order by {sort_field}")
        item_spec = spec.get("items")
        if isinstance(item_spec, dict):
            for index, item in enumerate(value):
                if item_spec.get("type") == "object":
                    validate_object(item, item_spec, f"{path}[{index}]", errors)
                else:
                    validate_value(item, item_spec, f"{path}[{index}]", errors)
        elif allowed is not None:
            for index, item in enumerate(value):
                if item not in allowed:
                    errors.append(f"{path}[{index}]: value {item!r} not in allowed_values")


def validate_object(value: Any, spec: Dict[str, Any], path: str, errors: List[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected object")
        return
    for key in required_child_keys(spec):
        if key not in value:
            errors.append(f"{path}: missing required key {key!r}")
    for key, child in child_specs(spec).items():
        if key in value and isinstance(child, dict):
            validate_value(value[key], child, f"{path}.{key}", errors)


def validate_named_object(value: Any, specs: Dict[str, Any], path: str, errors: List[str]) -> None:
    if not isinstance(value, dict):
        errors.append(f"{path}: expected object")
        return
    for key, spec in specs.items():
        if key not in value:
            errors.append(f"{path}: missing key {key!r}")
        elif isinstance(spec, dict):
            validate_value(value[key], spec, f"{path}.{key}", errors)


def validate_consistency(answer: Dict[str, Any], errors: List[str]) -> None:
    decisions = answer.get("application_decisions")
    summary = answer.get("summary")
    if isinstance(decisions, list) and isinstance(summary, dict):
        counts = {"APPROVE": 0, "HOLD": 0, "DENY": 0}
        high = []
        policy = []
        for item in decisions:
            if not isinstance(item, dict):
                continue
            determination = item.get("determination")
            if determination in counts:
                counts[determination] += 1
            if item.get("risk_tier") == "high" and "application_id" in item:
                high.append(item["application_id"])
            if item.get("policy_impacted") is True and "application_id" in item:
                policy.append(item["application_id"])
        expected_counts = {
            "approve_count": counts["APPROVE"],
            "hold_count": counts["HOLD"],
            "deny_count": counts["DENY"],
        }
        for key, expected in expected_counts.items():
            if key in summary and summary[key] != expected:
                errors.append(f"summary.{key}: expected {expected} from application_decisions")
        if "high_risk_application_ids" in summary and summary["high_risk_application_ids"] != sorted(high):
            errors.append("summary.high_risk_application_ids: does not match high-risk decisions")
        if "policy_impacted_application_ids" in summary and summary["policy_impacted_application_ids"] != sorted(policy):
            errors.append("summary.policy_impacted_application_ids: does not match policy_impacted decisions")

    queue = answer.get("queue")
    if isinstance(queue, list) and isinstance(summary, dict):
        if "queue_size" in summary and summary["queue_size"] != len(queue):
            errors.append("summary.queue_size: does not equal queue length")
        ranks = [item.get("rank") for item in queue if isinstance(item, dict)]
        if ranks != list(range(1, len(queue) + 1)):
            errors.append("queue.rank: expected contiguous ranks starting at 1")
        close = sorted(
            item.get("license_no")
            for item in queue
            if isinstance(item, dict) and item.get("match_confidence") in {"close_address", "uncertain"}
        )
        board = sorted(
            item.get("license_no")
            for item in queue
            if isinstance(item, dict) and item.get("next_step_label") == "board_review"
        )
        if "close_or_uncertain_match_license_numbers" in summary and summary["close_or_uncertain_match_license_numbers"] != close:
            errors.append("summary.close_or_uncertain_match_license_numbers: does not match queue")
        if "board_review_license_numbers" in summary and summary["board_review_license_numbers"] != board:
            errors.append("summary.board_review_license_numbers: does not match queue")


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: validate_answer.py TEMPLATE_JSON ANSWER_JSON", file=sys.stderr)
        return 2

    template_path, answer_path = sys.argv[1], sys.argv[2]
    template = load_json(template_path)
    answer = load_json(answer_path)
    if not isinstance(template, dict) or not isinstance(answer, dict):
        print("template and answer must be JSON objects", file=sys.stderr)
        return 1

    errors: List[str] = []
    top_keys = template_top_keys(template)
    if top_keys is not None:
        for key in top_keys:
            if key not in answer:
                errors.append(f"top-level: missing key {key!r}")
        extra = sorted(set(answer) - set(top_keys))
        if extra:
            errors.append(f"top-level: unexpected keys {extra}")

    for key, specs in field_specs(template).items():
        if key in answer and isinstance(specs, dict):
            validate_value(answer[key], specs, key, errors)

    for list_key in ("application_decisions", "queue"):
        spec = item_spec_for(template, list_key)
        if spec and list_key in answer:
            value = answer[list_key]
            if not isinstance(value, list):
                errors.append(f"{list_key}: expected list")
                continue
            declared = template.get("top_level_keys", {}).get(list_key, {}).get("required_length")
            if declared is None:
                declared = template.get(list_key, {}).get("length")
            if isinstance(declared, int) and len(value) != declared:
                errors.append(f"{list_key}: expected length {declared}, found {len(value)}")
            for index, item in enumerate(value):
                validate_named_object(item, spec, f"{list_key}[{index}]", errors)

    if isinstance(answer.get("summary"), dict):
        validate_named_object(answer["summary"], summary_spec(template), "summary", errors)

    validate_consistency(answer, errors)

    report = {
        "template": str(Path(template_path)),
        "answer": str(Path(answer_path)),
        "ok": not errors,
        "errors": errors,
    }
    print(json.dumps(report, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
