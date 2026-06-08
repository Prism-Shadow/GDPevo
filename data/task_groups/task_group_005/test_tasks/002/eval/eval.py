#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "batch_id": "grant_supplier_intake_april_2025",
    "review_date": "2025-04-30",
    "per_business": {
        "BUS-2025-0025": {
            "decision": "escalate",
            "risk_level": "high",
            "reportable_ubo_count": 0,
            "hard_stop_codes": ["bank_not_verified"],
            "required_action": "escalate_to_finance_risk",
        },
        "BUS-2025-0027": {
            "decision": "escalate",
            "risk_level": "high",
            "reportable_ubo_count": 1,
            "hard_stop_codes": [
                "invalid_tax_id",
                "license_expired_over_42_days",
                "missing_required_information",
            ],
            "required_action": "escalate_to_finance_risk",
        },
        "BUS-2025-0034": {
            "decision": "escalate",
            "risk_level": "high",
            "reportable_ubo_count": 4,
            "hard_stop_codes": [
                "bank_not_verified",
                "missing_required_information",
                "possible_pep",
                "shell_company_suspected",
            ],
            "required_action": "escalate_to_finance_risk",
        },
        "BUS-2025-0042": {
            "decision": "escalate",
            "risk_level": "high",
            "reportable_ubo_count": 0,
            "hard_stop_codes": [
                "bank_not_verified",
                "license_expired_over_42_days",
            ],
            "required_action": "escalate_to_finance_risk",
        },
        "BUS-2025-0052": {
            "decision": "escalate",
            "risk_level": "high",
            "reportable_ubo_count": 2,
            "hard_stop_codes": [
                "license_expired_over_42_days",
                "missing_required_information",
            ],
            "required_action": "escalate_to_finance_risk",
        },
    },
    "follow_up_business_ids": [
        "BUS-2025-0025",
        "BUS-2025-0027",
        "BUS-2025-0034",
        "BUS-2025-0042",
        "BUS-2025-0052",
    ],
    "intake_ready_count": 0,
    "batch_status": "blocked",
}


def normalized_list(value):
    if not isinstance(value, list):
        return None
    return sorted(str(item) for item in value)


def business_field(ids, field):
    def check(answer):
        per_business = answer.get("per_business")
        if not isinstance(per_business, dict):
            return False
        return all(
            per_business.get(business_id, {}).get(field) == EXPECTED["per_business"][business_id][field]
            for business_id in ids
        )

    return check


def hard_stop_codes(ids):
    def check(answer):
        per_business = answer.get("per_business")
        if not isinstance(per_business, dict):
            return False
        return all(
            normalized_list(per_business.get(business_id, {}).get("hard_stop_codes"))
            == EXPECTED["per_business"][business_id]["hard_stop_codes"]
            for business_id in ids
        )

    return check


def metadata(answer):
    return answer.get("batch_id") == EXPECTED["batch_id"] and answer.get("review_date") == EXPECTED["review_date"]


POINTS = [
    (
        "metadata_and_high_impact_decisions",
        3,
        lambda answer: (
            metadata(answer)
            and business_field(
                ["BUS-2025-0025", "BUS-2025-0027", "BUS-2025-0034"],
                "decision",
            )(answer)
        ),
    ),
    (
        "remaining_decisions_and_actions",
        2,
        lambda answer: (
            business_field(
                ["BUS-2025-0042", "BUS-2025-0052"],
                "decision",
            )(answer)
            and business_field(
                ["BUS-2025-0042", "BUS-2025-0052"],
                "required_action",
            )(answer)
        ),
    ),
    (
        "risk_levels",
        2,
        business_field(EXPECTED["per_business"].keys(), "risk_level"),
    ),
    (
        "ubo_counts",
        2,
        business_field(EXPECTED["per_business"].keys(), "reportable_ubo_count"),
    ),
    (
        "primary_hard_stop_codes",
        3,
        hard_stop_codes(["BUS-2025-0027", "BUS-2025-0034"]),
    ),
    (
        "remaining_hard_stop_codes",
        2,
        hard_stop_codes(["BUS-2025-0025", "BUS-2025-0042", "BUS-2025-0052"]),
    ),
    (
        "follow_up_business_set",
        2,
        lambda answer: normalized_list(answer.get("follow_up_business_ids")) == EXPECTED["follow_up_business_ids"],
    ),
    (
        "batch_status_and_ready_count",
        1,
        lambda answer: (
            answer.get("batch_status") == EXPECTED["batch_status"]
            and answer.get("intake_ready_count") == EXPECTED["intake_ready_count"]
        ),
    ),
]


def prediction_path():
    if len(sys.argv) > 1 and sys.argv[1]:
        return Path(sys.argv[1])
    env_path = os.environ.get("PREDICTION_FILE")
    if env_path:
        return Path(env_path)
    return Path("output") / "answer.json"


def load_answer():
    with prediction_path().open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def main():
    total = sum(weight for _, weight, _ in POINTS)
    try:
        answer = load_answer()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "max_score": 1.0,
                    "raw_score": 0,
                    "raw_total": total,
                    "error": str(exc),
                    "points": [],
                },
                indent=2,
            )
        )
        return 0

    raw_score = 0
    details = []
    for name, weight, check in POINTS:
        matched = bool(check(answer))
        if matched:
            raw_score += weight
        details.append({"name": name, "weight": weight, "matched": matched})

    print(
        json.dumps(
            {
                "score": raw_score / total,
                "max_score": 1.0,
                "raw_score": raw_score,
                "raw_total": total,
                "points": details,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
