#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "release_bill_ids": ["AP-2025-0010", "AP-2025-0106"],
    "hold_bill_ids": ["AP-2025-0041", "AP-2025-0065", "AP-2025-REIM-017"],
    "hold_reason_by_bill": {
        "AP-2025-0010": "released",
        "AP-2025-0041": "compliance_escalation",
        "AP-2025-0065": "ap_claim_not_approved",
        "AP-2025-0106": "released",
        "AP-2025-REIM-017": "compliance_escalation",
    },
    "compliance_blocked_business_ids": [
        "BUS-2025-0023",
        "BUS-2025-0041",
        "BUS-2025-0058",
    ],
    "payment_priority_ranking": ["AP-2025-0106", "AP-2025-0010"],
    "ap_balance_released_total": 40210.43,
    "board_status": "release_with_holds",
}


def norm_list(value):
    if not isinstance(value, list):
        return None
    return sorted(str(item).strip() for item in value)


def exact_list(value):
    if not isinstance(value, list):
        return None
    return [str(item).strip() for item in value]


def money(value):
    try:
        return round(float(value) + 1e-9, 2)
    except (TypeError, ValueError):
        return None


def reasons_match(answer, bill_ids):
    reasons = answer.get("hold_reason_by_bill")
    if not isinstance(reasons, dict):
        return False
    return all(reasons.get(bill_id) == EXPECTED["hold_reason_by_bill"][bill_id] for bill_id in bill_ids)


POINTS = [
    (
        "release_bill_ids",
        3,
        lambda a: (
            norm_list(a.get("release_bill_ids")) == EXPECTED["release_bill_ids"]
            and reasons_match(a, ["AP-2025-0010", "AP-2025-0106"])
        ),
    ),
    ("hold_bill_ids", 2, lambda a: norm_list(a.get("hold_bill_ids")) == EXPECTED["hold_bill_ids"]),
    ("claim_gate_hold_reason", 2, lambda a: reasons_match(a, ["AP-2025-0065"])),
    ("compliance_hold_reasons", 3, lambda a: reasons_match(a, ["AP-2025-0041", "AP-2025-REIM-017"])),
    (
        "compliance_blocked_business_ids",
        3,
        lambda a: norm_list(a.get("compliance_blocked_business_ids")) == EXPECTED["compliance_blocked_business_ids"],
    ),
    (
        "payment_priority_ranking",
        2,
        lambda a: exact_list(a.get("payment_priority_ranking")) == EXPECTED["payment_priority_ranking"],
    ),
    (
        "ap_balance_released_total",
        2,
        lambda a: money(a.get("ap_balance_released_total")) == money(EXPECTED["ap_balance_released_total"]),
    ),
    ("board_status", 1, lambda a: a.get("board_status") == EXPECTED["board_status"]),
]


def load_prediction():
    if len(sys.argv) > 1 and sys.argv[1]:
        path = Path(sys.argv[1])
    elif os.environ.get("PREDICTION_FILE"):
        path = Path(os.environ["PREDICTION_FILE"])
    else:
        path = Path("answer.json")
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    raw_total = sum(weight for _, weight, _ in POINTS)
    try:
        answer = load_prediction()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "max_score": 1.0,
                    "raw_score": 0,
                    "raw_total": raw_total,
                    "error": f"Could not parse prediction JSON: {exc}",
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
                "score": raw_score / raw_total if raw_total else 0.0,
                "max_score": 1.0,
                "raw_score": raw_score,
                "raw_total": raw_total,
                "points": details,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
