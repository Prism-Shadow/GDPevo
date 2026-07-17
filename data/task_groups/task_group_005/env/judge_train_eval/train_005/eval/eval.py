#!/usr/bin/env python3
import json
import sys
from pathlib import Path


EXPECTED = {
    "target_business_ids": ["BUS-2025-0006", "BUS-2025-0009", "BUS-2025-0018", "BUS-2025-0041", "BUS-2025-0056"],
    "decisions": {
        "BUS-2025-0006": "hold",
        "BUS-2025-0009": "escalate",
        "BUS-2025-0018": "release",
        "BUS-2025-0041": "escalate",
        "BUS-2025-0056": "hold",
    },
    "bank_mismatch_ids": ["BUS-2025-0006", "BUS-2025-0041"],
    "invalid_tax_ids": ["BUS-2025-0009", "BUS-2025-0041"],
    "expired_license_ids": ["BUS-2025-0009", "BUS-2025-0041", "BUS-2025-0056"],
    "review_queue_ids": ["BUS-2025-0006", "BUS-2025-0009", "BUS-2025-0041", "BUS-2025-0056"],
    "risk_score_override_flags": ["BUS-2025-0006"],
}


def norm_list(value):
    return sorted(str(x) for x in value) if isinstance(value, list) else None


def decisions_match(pred, required):
    decisions = pred.get("decisions")
    return isinstance(decisions, dict) and all(decisions.get(k) == v for k, v in required.items())


POINTS = [
    ("target_entity_set", 1, lambda p: norm_list(p.get("target_business_ids")) == EXPECTED["target_business_ids"]),
    ("release_decision", 2, lambda p: decisions_match(p, {"BUS-2025-0018": "release"})),
    ("hold_decisions", 3, lambda p: decisions_match(p, {"BUS-2025-0006": "hold", "BUS-2025-0056": "hold"})),
    (
        "escalate_decisions",
        3,
        lambda p: decisions_match(p, {"BUS-2025-0009": "escalate", "BUS-2025-0041": "escalate"}),
    ),
    ("bank_mismatch_ids", 2, lambda p: norm_list(p.get("bank_mismatch_ids")) == EXPECTED["bank_mismatch_ids"]),
    ("invalid_tax_ids", 2, lambda p: norm_list(p.get("invalid_tax_ids")) == EXPECTED["invalid_tax_ids"]),
    ("expired_license_ids", 2, lambda p: norm_list(p.get("expired_license_ids")) == EXPECTED["expired_license_ids"]),
    (
        "review_queue_and_override_flags",
        2,
        lambda p: (
            norm_list(p.get("review_queue_ids")) == EXPECTED["review_queue_ids"]
            and norm_list(p.get("risk_score_override_flags")) == EXPECTED["risk_score_override_flags"]
        ),
    ),
]


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output/answer.json")
    total = sum(weight for _, weight, _ in POINTS)
    try:
        pred = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(json.dumps({"score": 0.0, "earned_weight": 0, "total_weight": total, "error": str(exc)}))
        return 0
    earned = 0
    checks = []
    for name, weight, check in POINTS:
        passed = bool(check(pred))
        earned += weight if passed else 0
        checks.append({"id": name, "weight": weight, "passed": passed})
    print(
        json.dumps(
            {"score": earned / total, "earned_weight": earned, "total_weight": total, "checks": checks},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
