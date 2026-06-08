#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "payable_claim_ids": ["CLM-2025-0085", "CLM-2025-OPS-017"],
    "blocked_claim_ids": ["CLM-2025-0011", "CLM-2025-0064"],
    "paid_claim_ids": ["CLM-2025-0032", "CLM-2025-FIN-042"],
    "ap_open_balance_total": 3240.90,
    "crm_close_claim_ids": ["CLM-2025-0032", "CLM-2025-FIN-042"],
    "exception_reason_by_claim": {
        "CLM-2025-0011": "blocked_not_approved",
        "CLM-2025-0032": "paid_confirmed",
        "CLM-2025-0064": "blocked_missing_receipt",
        "CLM-2025-0085": "payable_approved_unpaid",
        "CLM-2025-FIN-042": "paid_stale_snapshot_conflict",
        "CLM-2025-OPS-017": "payable_approved_unpaid",
    },
    "batch_status": "ready_to_pay_with_blocks",
}


def norm_list(value):
    if not isinstance(value, list):
        return None
    return sorted(str(item).strip() for item in value)


def money(value):
    try:
        return round(float(value) + 1e-9, 2)
    except (TypeError, ValueError):
        return None


def reasons_match(answer, claim_ids):
    reasons = answer.get("exception_reason_by_claim")
    if not isinstance(reasons, dict):
        return False
    return all(reasons.get(cid) == EXPECTED["exception_reason_by_claim"][cid] for cid in claim_ids)


POINTS = [
    ("payable_claim_ids", 3, lambda a: norm_list(a.get("payable_claim_ids")) == EXPECTED["payable_claim_ids"]),
    ("blocked_claim_ids", 2, lambda a: norm_list(a.get("blocked_claim_ids")) == EXPECTED["blocked_claim_ids"]),
    ("paid_claim_ids", 2, lambda a: norm_list(a.get("paid_claim_ids")) == EXPECTED["paid_claim_ids"]),
    (
        "ap_open_balance_total",
        2,
        lambda a: money(a.get("ap_open_balance_total")) == money(EXPECTED["ap_open_balance_total"]),
    ),
    ("crm_close_claim_ids", 1, lambda a: norm_list(a.get("crm_close_claim_ids")) == EXPECTED["crm_close_claim_ids"]),
    (
        "exception_reasons_payable_paid",
        3,
        lambda a: reasons_match(a, ["CLM-2025-0085", "CLM-2025-OPS-017", "CLM-2025-0032", "CLM-2025-FIN-042"]),
    ),
    ("exception_reasons_blocked", 2, lambda a: reasons_match(a, ["CLM-2025-0011", "CLM-2025-0064"])),
    ("batch_status", 1, lambda a: a.get("batch_status") == EXPECTED["batch_status"]),
]


def load_prediction():
    if len(sys.argv) > 1:
        path = Path(sys.argv[1])
    elif os.environ.get("PREDICTION_FILE"):
        path = Path(os.environ["PREDICTION_FILE"])
    else:
        path = Path("answer.json")
    with path.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    try:
        answer = load_prediction()
    except Exception as exc:
        total = sum(weight for _, weight, _ in POINTS)
        print(
            json.dumps(
                {
                    "score": 0.0,
                    "max_score": 1.0,
                    "raw_score": 0,
                    "raw_total": total,
                    "error": f"Could not parse prediction JSON: {exc}",
                    "points": [],
                },
                indent=2,
            )
        )
        return 0

    raw_total = sum(weight for _, weight, _ in POINTS)
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
