#!/usr/bin/env python3
"""Validate common licensing answer-template requirements."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def required_top_level_keys(template: dict) -> list[str]:
    if isinstance(template.get("required_top_level_keys"), list):
        return list(template["required_top_level_keys"])
    if isinstance(template.get("top_level_keys"), dict):
        return list(template["top_level_keys"].keys())
    if isinstance(template.get("schema"), dict) and all(isinstance(v, dict) for v in template["schema"].values()):
        return list(template["schema"].keys())
    return []


def add_error(errors: list[str], message: str):
    errors.append(message)


def check_keys(template: dict, answer: dict, errors: list[str], warnings: list[str]):
    required = required_top_level_keys(template)
    if required:
        missing = [key for key in required if key not in answer]
        extra = [key for key in answer if key not in required]
        if missing:
            add_error(errors, "missing top-level key(s): " + ", ".join(missing))
        if extra:
            warnings.append("extra top-level key(s): " + ", ".join(extra))


def check_application_summary(answer: dict, errors: list[str]):
    decisions = answer.get("application_decisions")
    summary = answer.get("summary")
    if not isinstance(decisions, list) or not isinstance(summary, dict):
        return
    ids = [row.get("application_id") for row in decisions if isinstance(row, dict)]
    if ids != sorted(ids):
        add_error(errors, "application_decisions are not ordered by application_id ascending")
    counts = {"APPROVE": 0, "HOLD": 0, "DENY": 0}
    for row in decisions:
        if isinstance(row, dict) and row.get("determination") in counts:
            counts[row["determination"]] += 1
    expected_fields = {
        "approve_count": counts["APPROVE"],
        "hold_count": counts["HOLD"],
        "deny_count": counts["DENY"],
    }
    for key, expected in expected_fields.items():
        if key in summary and summary[key] != expected:
            add_error(errors, f"summary.{key} is {summary[key]!r}, expected {expected}")
    high_ids = sorted(row.get("application_id") for row in decisions if isinstance(row, dict) and row.get("risk_tier") == "high")
    if "high_risk_application_ids" in summary and summary["high_risk_application_ids"] != high_ids:
        add_error(errors, "summary.high_risk_application_ids does not match high-risk decisions")
    impacted_ids = sorted(
        row.get("application_id") for row in decisions if isinstance(row, dict) and row.get("policy_impacted") is True
    )
    if "policy_impacted_application_ids" in summary and summary["policy_impacted_application_ids"] != impacted_ids:
        add_error(errors, "summary.policy_impacted_application_ids does not match policy_impacted decisions")


def check_queue_summary(answer: dict, errors: list[str]):
    queue = answer.get("queue")
    summary = answer.get("summary")
    if not isinstance(queue, list):
        return
    ranks = [row.get("rank") for row in queue if isinstance(row, dict)]
    expected_ranks = list(range(1, len(queue) + 1))
    if ranks != expected_ranks:
        add_error(errors, f"queue ranks are {ranks!r}, expected {expected_ranks!r}")
    if isinstance(summary, dict) and "queue_size" in summary and summary["queue_size"] != len(queue):
        add_error(errors, f"summary.queue_size is {summary['queue_size']!r}, expected {len(queue)}")
    for row in queue:
        if not isinstance(row, dict):
            continue
        ids = row.get("matched_violation_ids")
        if ids is not None and len(ids) != len(set(ids)):
            add_error(errors, f"duplicate matched_violation_ids for {row.get('license_no')}")


def expected_list_lengths(template: dict) -> dict[str, int]:
    lengths: dict[str, int] = {}
    top = template.get("top_level_keys")
    if isinstance(top, dict):
        for key, spec in top.items():
            if isinstance(spec, dict) and isinstance(spec.get("required_length"), int):
                lengths[key] = spec["required_length"]
    for key, spec in template.items():
        if isinstance(spec, dict) and isinstance(spec.get("length"), int):
            lengths[key] = spec["length"]
    return lengths


def check_common_lengths(template: dict, answer: dict, errors: list[str]):
    for key, expected in expected_list_lengths(template).items():
        value = answer.get(key)
        if isinstance(value, list) and len(value) != expected:
            add_error(errors, f"{key} length is {len(value)}, expected {expected}")


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: validate_answer_template.py <answer_template.json> <answer.json>", file=sys.stderr)
        return 2
    template_path, answer_path = sys.argv[1], sys.argv[2]
    try:
        template = load_json(template_path)
        answer = load_json(answer_path)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"Cannot read file: {exc}", file=sys.stderr)
        return 1
    if not isinstance(template, dict) or not isinstance(answer, dict):
        print("Template and answer must both be JSON objects.", file=sys.stderr)
        return 1

    errors: list[str] = []
    warnings: list[str] = []
    check_keys(template, answer, errors, warnings)
    check_common_lengths(template, answer, errors)
    check_application_summary(answer, errors)
    check_queue_summary(answer, errors)

    for warning in warnings:
        print("WARNING: " + warning)
    if errors:
        for error in errors:
            print("ERROR: " + error, file=sys.stderr)
        return 1
    print(f"OK: {Path(answer_path).name} matches common template checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
