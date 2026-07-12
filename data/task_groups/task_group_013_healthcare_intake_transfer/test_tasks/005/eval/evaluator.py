#!/usr/bin/env python3
import json
import sys
from pathlib import Path


TRANSFER_QUEUE_IDS = ["Q-5203", "Q-5255"]
NON_TRANSFER_QUEUE_IDS = ["Q-5219", "Q-5226", "Q-5237", "Q-5241"]
REF_PROGRAM_CHART_QUEUE_IDS = ["Q-5219", "Q-5226", "Q-5241"]

POINTS = [
    ("task_metadata", 1),
    ("family_classifications", 1),
    ("next_actions", 2),
    ("transfer_owner_routing", 2),
    ("non_transfer_owner_routing", 1),
    ("transfer_blockers", 1),
    ("referral_program_chart_blockers", 2),
    ("registration_blockers", 1),
    ("due_priorities", 1),
    ("rollup_counts", 2),
]

SET_FIELDS = {"blockers"}


def load_json(path):
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def normalize(value):
    if isinstance(value, dict):
        normalized = {}
        for key, child in value.items():
            item = normalize(child)
            if key in SET_FIELDS and isinstance(item, list):
                item = sorted(item)
            normalized[key] = item
        if isinstance(normalized.get("queue_reviews"), list):
            normalized["queue_reviews"] = sorted(
                normalized["queue_reviews"],
                key=lambda row: row.get("queue_id", "") if isinstance(row, dict) else "",
            )
        if isinstance(normalized.get("action_rollup"), list):
            normalized["action_rollup"] = sorted(
                normalized["action_rollup"],
                key=lambda row: row.get("next_action", "") if isinstance(row, dict) else "",
            )
        if isinstance(normalized.get("owner_rollup"), list):
            normalized["owner_rollup"] = sorted(
                normalized["owner_rollup"],
                key=lambda row: row.get("owner", "") if isinstance(row, dict) else "",
            )
        return normalized
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


def queue_map(answer):
    rows = answer.get("queue_reviews")
    if not isinstance(rows, list):
        return {}
    return {row.get("queue_id"): row for row in rows if isinstance(row, dict) and isinstance(row.get("queue_id"), str)}


def field_map(answer, field, queue_ids=None):
    rows = queue_map(answer)
    ids = queue_ids or sorted(rows)
    return {queue_id: rows.get(queue_id, {}).get(field) for queue_id in ids}


def rollup_map(answer, field):
    rows = answer.get(field)
    if not isinstance(rows, list):
        return rows
    key = "next_action" if field == "action_rollup" else "owner"
    return {row.get(key): row.get("count") for row in rows if isinstance(row, dict) and isinstance(row.get(key), str)}


def score(expected, actual):
    expected = normalize(expected)
    actual = normalize(actual)

    checks = {
        "task_metadata": (
            actual.get("task_id") == expected.get("task_id")
            and actual.get("review_date") == expected.get("review_date")
        ),
        "family_classifications": field_map(actual, "family") == field_map(expected, "family"),
        "next_actions": field_map(actual, "next_action") == field_map(expected, "next_action"),
        "transfer_owner_routing": (
            field_map(actual, "owner", TRANSFER_QUEUE_IDS) == field_map(expected, "owner", TRANSFER_QUEUE_IDS)
        ),
        "non_transfer_owner_routing": (
            field_map(actual, "owner", NON_TRANSFER_QUEUE_IDS) == field_map(expected, "owner", NON_TRANSFER_QUEUE_IDS)
        ),
        "transfer_blockers": (
            field_map(actual, "blockers", TRANSFER_QUEUE_IDS) == field_map(expected, "blockers", TRANSFER_QUEUE_IDS)
        ),
        "referral_program_chart_blockers": (
            field_map(actual, "blockers", REF_PROGRAM_CHART_QUEUE_IDS)
            == field_map(expected, "blockers", REF_PROGRAM_CHART_QUEUE_IDS)
        ),
        "registration_blockers": (
            field_map(actual, "blockers", ["Q-5237"]) == field_map(expected, "blockers", ["Q-5237"])
        ),
        "due_priorities": field_map(actual, "due_priority") == field_map(expected, "due_priority"),
        "rollup_counts": (
            rollup_map(actual, "action_rollup") == rollup_map(expected, "action_rollup")
            and rollup_map(actual, "owner_rollup") == rollup_map(expected, "owner_rollup")
        ),
    }

    earned = 0
    details = []
    for name, weight in POINTS:
        passed = checks[name]
        if passed:
            earned += weight
        details.append(
            {
                "name": name,
                "awarded": weight if passed else 0,
                "possible": weight,
                "passed": passed,
            }
        )

    max_score = sum(weight for _, weight in POINTS)
    return {
        "score": earned,
        "max_score": max_score,
        "passed": earned == max_score,
        "details": details,
    }


def main():
    if len(sys.argv) != 3:
        print("Usage: evaluator.py EXPECTED_JSON ACTUAL_JSON", file=sys.stderr)
        return 2

    try:
        expected = load_json(sys.argv[1])
        actual = load_json(sys.argv[2])
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(weight for _, weight in POINTS),
                    "passed": False,
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 1

    result = score(expected, actual)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
