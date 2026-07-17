#!/usr/bin/env python3
import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


EXPECTED = {
    "eligible_claim_ids": ["CLM-2025-FIN-042", "CLM-2025-OPS-017"],
    "not_ready_claim_ids": ["CLM-2025-0015", "CLM-2025-0038", "CLM-2025-0080"],
    "ap_balance_by_claim": {
        "CLM-2025-0015": "0.00",
        "CLM-2025-0038": "0.00",
        "CLM-2025-0080": "0.00",
        "CLM-2025-FIN-042": "0.00",
        "CLM-2025-OPS-017": "1842.36",
    },
    "stale_snapshot_corrections": {
        "CLM-2025-0015": "block_unapproved_claim",
        "CLM-2025-0038": "ignore_void_bill",
        "CLM-2025-0080": "exclude_amount_or_vendor_mismatch",
        "CLM-2025-FIN-042": "replace_with_matched_paid_bill",
        "CLM-2025-OPS-017": "mark_in_flight_payment",
    },
    "batch_status": "needs_ap_refresh",
}


def sorted_strings(value):
    return sorted(str(item).strip() for item in value) if isinstance(value, list) else None


def money(value):
    try:
        return str(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    except Exception:
        return None


POINTS = [
    ("eligible claim set", 2),
    ("not-ready claim set", 2),
    ("balances for eligible claims", 2),
    ("balances for not-ready claims", 2),
    ("stale corrections for eligible claims", 2),
    ("stale corrections for not-ready claims", 2),
    ("close log required flag and IDs", 2),
    ("batch status", 1),
]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/answer.json")
    total = sum(weight for _, weight in POINTS)
    try:
        pred = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(json.dumps({"score": 0, "earned_weight": 0, "total_weight": total, "error": str(exc)}))
        return 0

    balances = pred.get("ap_balance_by_claim", {})
    corrections = pred.get("stale_snapshot_corrections", {})
    close = pred.get("close_log_required", {})
    checks = [
        sorted_strings(pred.get("eligible_claim_ids")) == EXPECTED["eligible_claim_ids"],
        sorted_strings(pred.get("not_ready_claim_ids")) == EXPECTED["not_ready_claim_ids"],
        isinstance(balances, dict)
        and money(balances.get("CLM-2025-FIN-042")) == "0.00"
        and money(balances.get("CLM-2025-OPS-017")) == "1842.36",
        isinstance(balances, dict)
        and money(balances.get("CLM-2025-0015")) == "0.00"
        and money(balances.get("CLM-2025-0038")) == "0.00"
        and money(balances.get("CLM-2025-0080")) == "0.00",
        isinstance(corrections, dict)
        and corrections.get("CLM-2025-FIN-042") == "replace_with_matched_paid_bill"
        and corrections.get("CLM-2025-OPS-017") == "mark_in_flight_payment",
        isinstance(corrections, dict)
        and corrections.get("CLM-2025-0015") == "block_unapproved_claim"
        and corrections.get("CLM-2025-0038") == "ignore_void_bill"
        and corrections.get("CLM-2025-0080") == "exclude_amount_or_vendor_mismatch",
        isinstance(close, dict)
        and close.get("required") is True
        and sorted_strings(close.get("ids")) == ["CLOSE-2025-04-009"],
        pred.get("batch_status") == EXPECTED["batch_status"],
    ]
    earned = sum(weight for ok, (_, weight) in zip(checks, POINTS) if ok)
    details = [{"goal": goal, "weight": weight, "matched": bool(ok)} for ok, (goal, weight) in zip(checks, POINTS)]
    print(
        json.dumps(
            {"score": earned / total, "earned_weight": earned, "total_weight": total, "details": details}, indent=2
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
