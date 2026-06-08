#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path


EXPECTED = {
    "close_readiness": "not_ready",
    "exception_ids": [
        "CLM-2025-0085",
        "CLM-2025-OPS-017",
        "PREPAID-1250",
        "PREPAID-1251",
    ],
    "exception_type_by_id": {
        "CLM-2025-0085": "reimbursement_unreconciled",
        "CLM-2025-OPS-017": "reimbursement_unreconciled",
        "PREPAID-1250": "prepaid_variance",
        "PREPAID-1251": "prepaid_variance",
    },
    "materiality_by_exception": {
        "CLM-2025-0085": "low",
        "CLM-2025-OPS-017": "low",
        "PREPAID-1250": "high",
        "PREPAID-1251": "high",
    },
    "owner_queue_by_exception": {
        "CLM-2025-0085": "ap",
        "CLM-2025-OPS-017": "ap",
        "PREPAID-1250": "accounting",
        "PREPAID-1251": "accounting",
    },
    "top_priority_exception_ids": [
        "PREPAID-1250",
        "PREPAID-1251",
        "CLM-2025-OPS-017",
        "CLM-2025-0085",
    ],
    "close_impact_by_exception": {
        "CLM-2025-0085": 1398.54,
        "CLM-2025-OPS-017": 1842.36,
        "PREPAID-1250": -290855.05,
        "PREPAID-1251": 79342.94,
    },
    "impact_direction_by_exception": {
        "CLM-2025-0085": "increase_liability",
        "CLM-2025-OPS-017": "increase_liability",
        "PREPAID-1250": "decrease_asset",
        "PREPAID-1251": "increase_asset",
    },
    "net_close_impact_total": -208271.21,
}


def norm_list(value):
    if not isinstance(value, list):
        return None
    return sorted(str(item).strip() for item in value)


def ordered_list(value):
    if not isinstance(value, list):
        return None
    return [str(item).strip() for item in value]


def money(value):
    try:
        return round(float(value) + 1e-9, 2)
    except (TypeError, ValueError):
        return None


def dict_matches(answer, key, subset=None):
    value = answer.get(key)
    if not isinstance(value, dict):
        return False
    expected = EXPECTED[key]
    ids = subset or expected.keys()
    return all(value.get(exception_id) == expected[exception_id] for exception_id in ids)


def money_dict_matches(answer, key):
    value = answer.get(key)
    if not isinstance(value, dict):
        return False
    expected = EXPECTED[key]
    return all(money(value.get(exception_id)) == amount for exception_id, amount in expected.items())


POINTS = [
    ("close_readiness", 1, lambda a: a.get("close_readiness") == EXPECTED["close_readiness"]),
    ("exception_ids", 2, lambda a: norm_list(a.get("exception_ids")) == EXPECTED["exception_ids"]),
    ("exception_type_by_id", 2, lambda a: dict_matches(a, "exception_type_by_id")),
    ("materiality_by_exception", 2, lambda a: dict_matches(a, "materiality_by_exception")),
    ("owner_queue_by_exception", 2, lambda a: dict_matches(a, "owner_queue_by_exception")),
    (
        "top_priority_exception_ids",
        2,
        lambda a: ordered_list(a.get("top_priority_exception_ids")) == EXPECTED["top_priority_exception_ids"],
    ),
    ("close_impact_by_exception", 3, lambda a: money_dict_matches(a, "close_impact_by_exception")),
    ("impact_direction_by_exception", 3, lambda a: dict_matches(a, "impact_direction_by_exception")),
    (
        "net_close_impact_total",
        3,
        lambda a: money(a.get("net_close_impact_total")) == EXPECTED["net_close_impact_total"],
    ),
    (
        "reimbursement_exception_detail",
        1,
        lambda a: (
            dict_matches(a, "exception_type_by_id", ["CLM-2025-0085", "CLM-2025-OPS-017"])
            and dict_matches(a, "materiality_by_exception", ["CLM-2025-0085", "CLM-2025-OPS-017"])
            and dict_matches(a, "owner_queue_by_exception", ["CLM-2025-0085", "CLM-2025-OPS-017"])
        ),
    ),
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
        raw_total = sum(weight for _, weight, _ in POINTS)
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
