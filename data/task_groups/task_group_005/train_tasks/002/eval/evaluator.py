#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


EXPECTED = {
    "per_business": [
        {"business_id": "BUS-2025-0009", "decision": "escalate"},
        {"business_id": "BUS-2025-0017", "decision": "escalate"},
        {"business_id": "BUS-2025-0022", "decision": "escalate"},
        {"business_id": "BUS-2025-0033", "decision": "approve"},
        {"business_id": "BUS-2025-0036", "decision": "awaiting_information"},
    ],
    "reportable_ubo_counts": {
        "BUS-2025-0009": 1,
        "BUS-2025-0017": 0,
        "BUS-2025-0022": 2,
        "BUS-2025-0033": 2,
        "BUS-2025-0036": 1,
    },
    "hard_stop_flags": {
        "BUS-2025-0009": ["confirmed_pep", "expired_license", "vendor_on_hold"],
        "BUS-2025-0017": ["bank_name_mismatch", "confirmed_pep", "shell_company_suspected"],
        "BUS-2025-0022": ["bank_closed", "expired_license", "screening_not_run"],
        "BUS-2025-0033": [],
        "BUS-2025-0036": ["missing_required_documents", "screening_not_run"],
    },
    "follow_up_business_ids": [
        "BUS-2025-0009",
        "BUS-2025-0017",
        "BUS-2025-0022",
        "BUS-2025-0036",
    ],
    "overall_release_ready": False,
}

BUSINESS_IDS = [
    "BUS-2025-0009",
    "BUS-2025-0017",
    "BUS-2025-0022",
    "BUS-2025-0033",
    "BUS-2025-0036",
]


def load_prediction(path: Path):
    with path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def decisions_by_id(payload):
    rows = payload.get("per_business", [])
    if not isinstance(rows, list):
        return {}
    return {row.get("business_id"): row.get("decision") for row in rows if isinstance(row, dict)}


def normalize_counts(value):
    if not isinstance(value, dict):
        return {}
    normalized = {}
    for business_id in BUSINESS_IDS:
        item = value.get(business_id)
        if isinstance(item, bool):
            normalized[business_id] = item
        elif isinstance(item, int):
            normalized[business_id] = item
        elif isinstance(item, float) and item.is_integer():
            normalized[business_id] = int(item)
        else:
            normalized[business_id] = item
    return normalized


def normalize_flag_map(value):
    if not isinstance(value, dict):
        return {}
    normalized = {}
    for business_id in BUSINESS_IDS:
        flags = value.get(business_id)
        if isinstance(flags, list):
            normalized[business_id] = sorted(str(flag) for flag in flags)
        else:
            normalized[business_id] = flags
    return normalized


def normalize_id_list(value):
    if not isinstance(value, list):
        return value
    return sorted(str(item) for item in value)


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: evaluator.py <prediction_path>"}, indent=2))
        return 2

    try:
        prediction = load_prediction(Path(sys.argv[1]))
    except Exception as exc:
        print(json.dumps({"score": 0.0, "error": f"Could not load prediction: {exc}"}, indent=2))
        return 0

    pred_decisions = decisions_by_id(prediction)
    exp_decisions = decisions_by_id(EXPECTED)
    pred_counts = normalize_counts(prediction.get("reportable_ubo_counts"))
    exp_counts = normalize_counts(EXPECTED["reportable_ubo_counts"])
    pred_flags = normalize_flag_map(prediction.get("hard_stop_flags"))
    exp_flags = normalize_flag_map(EXPECTED["hard_stop_flags"])

    checks = [
        {
            "id": "SP1",
            "goal": "Correct release decisions for BUS-2025-0009, BUS-2025-0017, and BUS-2025-0022.",
            "weight": 3,
            "passed": all(
                pred_decisions.get(bid) == exp_decisions[bid]
                for bid in ["BUS-2025-0009", "BUS-2025-0017", "BUS-2025-0022"]
            ),
        },
        {
            "id": "SP2",
            "goal": "Correct release decisions for BUS-2025-0033 and BUS-2025-0036.",
            "weight": 2,
            "passed": all(pred_decisions.get(bid) == exp_decisions[bid] for bid in ["BUS-2025-0033", "BUS-2025-0036"]),
        },
        {
            "id": "SP3",
            "goal": "Correct reportable UBO counts for BUS-2025-0009, BUS-2025-0017, and BUS-2025-0022.",
            "weight": 2,
            "passed": all(
                pred_counts.get(bid) == exp_counts[bid] for bid in ["BUS-2025-0009", "BUS-2025-0017", "BUS-2025-0022"]
            ),
        },
        {
            "id": "SP4",
            "goal": "Correct reportable UBO counts for BUS-2025-0033 and BUS-2025-0036.",
            "weight": 1,
            "passed": all(pred_counts.get(bid) == exp_counts[bid] for bid in ["BUS-2025-0033", "BUS-2025-0036"]),
        },
        {
            "id": "SP5",
            "goal": "Correct hard-stop flags for BUS-2025-0009 and BUS-2025-0017.",
            "weight": 3,
            "passed": all(pred_flags.get(bid) == exp_flags[bid] for bid in ["BUS-2025-0009", "BUS-2025-0017"]),
        },
        {
            "id": "SP6",
            "goal": "Correct hard-stop flags for BUS-2025-0022, BUS-2025-0033, and BUS-2025-0036.",
            "weight": 3,
            "passed": all(
                pred_flags.get(bid) == exp_flags[bid] for bid in ["BUS-2025-0022", "BUS-2025-0033", "BUS-2025-0036"]
            ),
        },
        {
            "id": "SP7",
            "goal": "Correct follow-up business ID set.",
            "weight": 2,
            "passed": normalize_id_list(prediction.get("follow_up_business_ids"))
            == EXPECTED["follow_up_business_ids"],
        },
        {
            "id": "SP8",
            "goal": "Correct overall release-ready boolean.",
            "weight": 1,
            "passed": prediction.get("overall_release_ready") is EXPECTED["overall_release_ready"],
        },
    ]

    total_weight = sum(check["weight"] for check in checks)
    earned = sum(check["weight"] for check in checks if check["passed"])
    result = {
        "score": earned / total_weight,
        "earned_weight": earned,
        "total_weight": total_weight,
        "checks": checks,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
