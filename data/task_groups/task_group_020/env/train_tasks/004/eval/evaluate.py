#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
ANSWER_PATH = TASK_DIR / "output" / "answer.json"

SCORING_POINTS = [
    {
        "id": "SP001",
        "description": "Transfer-employee issue is correctly identified and positioned.",
        "weight": 3,
        "kind": "employee_transfer",
    },
    {
        "id": "SP002",
        "description": "TSA and service-continuity issue is correctly identified and positioned.",
        "weight": 3,
        "kind": "tsa_service_continuity",
    },
    {
        "id": "SP003",
        "description": "Non-compete and non-solicit limits are correctly narrowed.",
        "weight": 2,
        "kind": "restrictive_covenants",
    },
    {
        "id": "SP004",
        "description": "IP transition period and scope are correctly narrowed.",
        "weight": 2,
        "kind": "ip_transition",
    },
    {
        "id": "SP005",
        "description": "Escrow and closing deadline deviations are correctly quantified.",
        "weight": 2,
        "kind": "escrow_and_deadline",
    },
    {
        "id": "SP006",
        "description": "Priority issue severity and action set is correct.",
        "weight": 2,
        "kind": "priority_issues",
    },
]


def load_json(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def get_path(obj, path):
    cur = obj
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def decimal_value(value, places):
    try:
        quant = Decimal("1").scaleb(-places)
        return Decimal(str(value)).quantize(quant, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return None


def scalar_fields_match(prediction, expected, paths):
    return all(get_path(prediction, path) == get_path(expected, path) for path in paths)


def numeric_fields_match(prediction, expected, specs):
    return all(
        decimal_value(get_path(prediction, path), places) == decimal_value(get_path(expected, path), places)
        for path, places in specs
    )


def list_as_set(value):
    if not isinstance(value, list):
        return None
    return {str(item) for item in value}


def string_list_set_match(prediction, expected, path):
    return list_as_set(get_path(prediction, path)) == list_as_set(get_path(expected, path))


def normalize_priority_issues(value):
    if not isinstance(value, list):
        return None
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return None
        normalized.append(
            {
                "issue_id": item.get("issue_id"),
                "severity": item.get("severity"),
                "recommended_action": item.get("recommended_action"),
            }
        )
    return sorted(normalized, key=lambda row: str(row.get("issue_id")))


def employee_transfer_match(prediction, expected):
    paths = [
        ("transition_flags", "employee_transfer", "issue_present"),
        ("transition_flags", "employee_transfer", "seller_warn_or_severance_retained"),
        ("transition_flags", "employee_transfer", "required_offer_standard"),
        ("transition_flags", "employee_transfer", "approval_required"),
    ]
    numeric_specs = [
        (("transition_flags", "employee_transfer", "draft_offer_percent"), 1),
    ]
    return scalar_fields_match(prediction, expected, paths) and numeric_fields_match(
        prediction, expected, numeric_specs
    )


def tsa_service_continuity_match(prediction, expected):
    paths = [
        ("transition_flags", "tsa_service_continuity", "issue_present"),
        ("transition_flags", "tsa_service_continuity", "draft_duration_months"),
        ("transition_flags", "tsa_service_continuity", "target_duration_months"),
        ("transition_flags", "tsa_service_continuity", "fallback_duration_months"),
        ("transition_flags", "tsa_service_continuity", "approval_required"),
    ]
    service_path = ("transition_flags", "tsa_service_continuity", "required_service_codes")
    return scalar_fields_match(prediction, expected, paths) and string_list_set_match(
        prediction, expected, service_path
    )


def restrictive_covenants_match(prediction, expected):
    paths = [
        ("transition_flags", "restrictive_covenants", "issue_present"),
        ("transition_flags", "restrictive_covenants", "draft_non_compete_years"),
        ("transition_flags", "restrictive_covenants", "max_non_compete_years"),
        ("transition_flags", "restrictive_covenants", "affiliate_scope_allowed"),
        ("transition_flags", "restrictive_covenants", "required_scope"),
        ("transition_flags", "restrictive_covenants", "non_solicit_scope"),
        ("transition_flags", "restrictive_covenants", "approval_required"),
    ]
    return scalar_fields_match(prediction, expected, paths)


def ip_transition_match(prediction, expected):
    paths = [
        ("transition_flags", "ip_transition", "issue_present"),
        ("transition_flags", "ip_transition", "draft_trademark_phaseout_months"),
        ("transition_flags", "ip_transition", "max_trademark_phaseout_months"),
        ("transition_flags", "ip_transition", "broad_design_file_access"),
        ("transition_flags", "ip_transition", "required_scope"),
        ("transition_flags", "ip_transition", "approval_required"),
    ]
    return scalar_fields_match(prediction, expected, paths)


def escrow_and_deadline_match(prediction, expected):
    paths = [
        ("transition_flags", "escrow_and_deadline", "issue_present"),
        ("transition_flags", "escrow_and_deadline", "general_escrow_amount_usd"),
        ("transition_flags", "escrow_and_deadline", "signing_date"),
        ("transition_flags", "escrow_and_deadline", "draft_closing_deadline"),
        ("transition_flags", "escrow_and_deadline", "deadline_days_after_signing"),
        ("transition_flags", "escrow_and_deadline", "minimum_deadline_days"),
        ("transition_flags", "escrow_and_deadline", "deadline_escalation_required"),
    ]
    numeric_specs = [
        (("transition_flags", "escrow_and_deadline", "general_escrow_percent"), 2),
        (("transition_flags", "escrow_and_deadline", "target_max_escrow_percent"), 2),
    ]
    return scalar_fields_match(prediction, expected, paths) and numeric_fields_match(
        prediction, expected, numeric_specs
    )


def priority_issues_match(prediction, expected):
    return normalize_priority_issues(prediction.get("priority_issues")) == normalize_priority_issues(
        expected.get("priority_issues")
    )


MATCHERS = {
    "employee_transfer": employee_transfer_match,
    "tsa_service_continuity": tsa_service_continuity_match,
    "restrictive_covenants": restrictive_covenants_match,
    "ip_transition": ip_transition_match,
    "escrow_and_deadline": escrow_and_deadline_match,
    "priority_issues": priority_issues_match,
}


def score(prediction, expected):
    details = []
    earned = 0
    total = sum(point["weight"] for point in SCORING_POINTS)
    for point in SCORING_POINTS:
        matched = MATCHERS[point["kind"]](prediction, expected)
        if matched:
            earned += point["weight"]
        details.append(
            {
                "id": point["id"],
                "description": point["description"],
                "weight": point["weight"],
                "matched": bool(matched),
                "earned": point["weight"] if matched else 0,
            }
        )
    return {
        "score": earned / total if total else 0.0,
        "earned_weight": earned,
        "total_weight": total,
        "details": details,
    }


def main():
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else ANSWER_PATH
    try:
        prediction = load_json(prediction_path)
        expected = load_json(ANSWER_PATH)
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "earned_weight": 0,
                    "total_weight": sum(point["weight"] for point in SCORING_POINTS),
                    "error": str(exc),
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    print(json.dumps(score(prediction, expected), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
