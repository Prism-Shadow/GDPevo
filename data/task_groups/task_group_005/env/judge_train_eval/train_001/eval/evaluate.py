import json
import sys
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


SCORING_POINTS = [
    ("payable_claim_ids", 3, "Payable claim set"),
    ("blocked_claim_ids", 3, "Blocked claim set"),
    ("paid_claim_ids", 2, "Paid claim set"),
    ("ap_open_balance_total", 2, "Valid open AP reimbursement balance"),
    ("crm_required_claim_ids", 2, "CRM cleanup claim set"),
    ("batch_status", 2, "Overall batch close status"),
    ("reviewed_claim_count", 1, "Reviewed batch count"),
    ("partition_consistency", 1, "Claim partition covers the requested batch once"),
]

REQUESTED_CLAIMS = {
    "CLM-2025-OPS-017",
    "CLM-2025-FIN-042",
    "CLM-2025-0090",
    "CLM-2025-0080",
    "CLM-2025-0038",
    "CLM-2025-0037",
}


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def as_set(value):
    if not isinstance(value, list):
        return None
    return {str(item) for item in value}


def cents(value):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return None


def partition_ok(pred):
    parts = []
    for key in ("payable_claim_ids", "blocked_claim_ids", "paid_claim_ids"):
        value = pred.get(key)
        if not isinstance(value, list):
            return False
        parts.extend(str(item) for item in value)
    return set(parts) == REQUESTED_CLAIMS and len(parts) == len(set(parts)) == len(REQUESTED_CLAIMS)


def main():
    if len(sys.argv) != 3:
        print("usage: evaluate.py <prediction.json> <answer.json>", file=sys.stderr)
        return 2

    pred_path = Path(sys.argv[1])
    answer_path = Path(sys.argv[2])
    pred = load_json(pred_path)
    answer = load_json(answer_path)

    total_weight = sum(weight for _, weight, _ in SCORING_POINTS)
    earned = 0
    details = []

    for key, weight, label in SCORING_POINTS:
        if key == "partition_consistency":
            matched = partition_ok(pred)
        elif key.endswith("_claim_ids"):
            matched = as_set(pred.get(key)) == as_set(answer.get(key))
        elif key == "ap_open_balance_total":
            matched = cents(pred.get(key)) == cents(answer.get(key))
        else:
            matched = pred.get(key) == answer.get(key)
        if matched:
            earned += weight
        details.append(
            {
                "key": key,
                "label": label,
                "weight": weight,
                "matched": matched,
            }
        )

    result = {
        "score": earned / total_weight,
        "earned_weight": earned,
        "total_weight": total_weight,
        "details": details,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
