#!/usr/bin/env python3
"""Evaluator for train_004."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STANDARD_ANSWER = ROOT / "output" / "answer.json"


SCORING_POINTS = [
    {
        "id": "SP001",
        "weight": 3,
        "goal": "Correct sponsor status set and badge sponsor/attendee classification.",
    },
    {
        "id": "SP002",
        "weight": 2,
        "goal": "Correct campaign member create/update/no-action decisions.",
    },
    {
        "id": "SP003",
        "weight": 2,
        "goal": "Correct open opportunity total for qualified non-sponsor leads.",
    },
    {
        "id": "SP004",
        "weight": 2,
        "goal": "Correct unpaid sponsor follow-up account set and amount.",
    },
    {
        "id": "SP005",
        "weight": 2,
        "goal": "Correct normalized contacts for badge-only leads.",
    },
    {
        "id": "SP006",
        "weight": 1,
        "goal": "Correct event follow-up due date.",
    },
    {
        "id": "SP007",
        "weight": 1,
        "goal": "Correct exclusion reason counts.",
    },
]


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def by_key(rows: Any, key: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in as_list(rows):
        if isinstance(row, dict) and row.get(key) is not None:
            result[str(row[key])] = row
    return result


def selected_map(rows: Any, key: str, fields: list[str]) -> dict[str, dict[str, Any]]:
    mapped = by_key(rows, key)
    return {item_key: {field: mapped[item_key].get(field) for field in fields} for item_key in sorted(mapped)}


def sorted_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def check_sp001(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    sponsor_fields = ["account_name", "sponsor_status", "amount_usd"]
    badge_fields = ["company_name", "classification", "exclusion_reason"]
    return selected_map(pred.get("sponsor_statuses"), "account_id", sponsor_fields) == selected_map(
        exp.get("sponsor_statuses"), "account_id", sponsor_fields
    ) and selected_map(pred.get("badge_decisions"), "badge_id", badge_fields) == selected_map(
        exp.get("badge_decisions"), "badge_id", badge_fields
    )


def check_sp002(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    fields = ["account_name", "contact_name", "action", "target_status"]
    return selected_map(pred.get("campaign_member_actions"), "subject_key", fields) == selected_map(
        exp.get("campaign_member_actions"), "subject_key", fields
    )


def check_sp003(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    p_summary = pred.get("opportunity_summary", {})
    e_summary = exp.get("opportunity_summary", {})
    if not isinstance(p_summary, dict) or not isinstance(e_summary, dict):
        return False
    return (
        sorted_strings(p_summary.get("qualified_non_sponsor_account_names"))
        == sorted_strings(e_summary.get("qualified_non_sponsor_account_names"))
        and p_summary.get("lead_opportunity_amount_usd") == e_summary.get("lead_opportunity_amount_usd")
        and p_summary.get("open_opportunity_total_usd") == e_summary.get("open_opportunity_total_usd")
        and p_summary.get("open_opportunity_count") == e_summary.get("open_opportunity_count")
    )


def check_sp004(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    p_followup = pred.get("sponsor_followup", {})
    e_followup = exp.get("sponsor_followup", {})
    if not isinstance(p_followup, dict) or not isinstance(e_followup, dict):
        return False
    return (
        sorted_strings(p_followup.get("unpaid_sponsor_account_names"))
        == sorted_strings(e_followup.get("unpaid_sponsor_account_names"))
        and p_followup.get("unpaid_sponsor_total_usd") == e_followup.get("unpaid_sponsor_total_usd")
        and p_followup.get("followup_due_date") == e_followup.get("followup_due_date")
    )


def check_sp005(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    fields = ["contact_name", "normalized_email", "normalized_phone"]
    return selected_map(pred.get("badge_only_contacts"), "company_name", fields) == selected_map(
        exp.get("badge_only_contacts"), "company_name", fields
    )


def check_sp006(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    p_event = pred.get("event", {})
    e_event = exp.get("event", {})
    if not isinstance(p_event, dict) or not isinstance(e_event, dict):
        return False
    return p_event.get("event_id") == e_event.get("event_id") and p_event.get("lead_followup_due_date") == e_event.get(
        "lead_followup_due_date"
    )


def check_sp007(pred: dict[str, Any], exp: dict[str, Any]) -> bool:
    return pred.get("exclusion_counts") == exp.get("exclusion_counts")


CHECKS = {
    "SP001": check_sp001,
    "SP002": check_sp002,
    "SP003": check_sp003,
    "SP004": check_sp004,
    "SP005": check_sp005,
    "SP006": check_sp006,
    "SP007": check_sp007,
}


def evaluate(prediction_path: Path) -> dict[str, Any]:
    expected = load_json(STANDARD_ANSWER)
    try:
        prediction = load_json(prediction_path)
    except Exception as exc:  # noqa: BLE001 - evaluator should return JSON for all failures.
        return {
            "total_score": 0.0,
            "error": f"Could not parse prediction JSON: {exc}",
            "scoring_points": [
                {
                    "id": point["id"],
                    "goal": point["goal"],
                    "weight": point["weight"],
                    "passed": False,
                    "score": 0.0,
                }
                for point in SCORING_POINTS
            ],
        }

    if not isinstance(prediction, dict):
        prediction = {}

    total_weight = sum(point["weight"] for point in SCORING_POINTS)
    scoring_points = []
    total_score = 0.0
    for point in SCORING_POINTS:
        passed = bool(CHECKS[point["id"]](prediction, expected))
        score = point["weight"] / total_weight if passed else 0.0
        total_score += score
        scoring_points.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "passed": passed,
                "score": round(score, 6),
            }
        )

    return {
        "total_score": round(total_score, 6),
        "scoring_points": scoring_points,
    }


def main() -> None:
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else STANDARD_ANSWER
    print(json.dumps(evaluate(prediction_path), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
