#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {
        "goal": "Correct out-of-range ICD-10 referral IDs.",
        "id": "SP001",
        "paths": ["out_of_range_code_referral_ids"],
        "weight": 2,
    },
    {
        "goal": "Correct laterality mismatch IDs and corrections.",
        "id": "SP002",
        "paths": [
            "laterality_mismatch_referral_ids",
            "corrected_code_suggestions.REF-TE-0403",
            "corrected_code_suggestions.REF-TE-0407",
            "corrected_code_suggestions.REF-TE-0412",
        ],
        "weight": 3,
    },
    {
        "goal": "Correct narrative/code mismatch IDs and correction.",
        "id": "SP003",
        "paths": ["narrative_mismatch_referral_ids", "corrected_code_suggestions.REF-TE-0406"],
        "weight": 2,
    },
    {"goal": "Correct duplicate referral groups.", "id": "SP004", "paths": ["duplicate_groups"], "weight": 2},
    {
        "goal": "Correct unrelated-patient insurance anomaly.",
        "id": "SP005",
        "paths": ["insurance_anomalies"],
        "weight": 2,
    },
    {
        "goal": "Correct missing records, imaging, and authorization counts.",
        "id": "SP006",
        "paths": ["missing_counts"],
        "weight": 1,
    },
    {
        "goal": "Correct Tier 1 immediate queue.",
        "id": "SP007",
        "paths": ["priority_queues.tier1_immediate"],
        "weight": 3,
    },
    {
        "goal": "Correct Tier 2 follow-up queue.",
        "id": "SP008",
        "paths": ["priority_queues.tier2_short_term"],
        "weight": 2,
    },
    {
        "goal": "Correct administrative reschedule queue.",
        "id": "SP009",
        "paths": ["priority_queues.tier3_administrative"],
        "weight": 1,
    },
]


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_path(obj, path):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def norm(value):
    if isinstance(value, list):
        return sorted((norm(v) for v in value), key=lambda x: json.dumps(x, sort_keys=True))
    if isinstance(value, dict):
        return {str(k): norm(v) for k, v in sorted(value.items())}
    return value


def main():
    here = Path(__file__).resolve()
    expected_path = here.parents[1] / "output" / "answer.json"
    pred_path = Path(sys.argv[1]) if len(sys.argv) > 1 else expected_path
    expected = load_json(expected_path)
    prediction = load_json(pred_path)
    total = sum(p["weight"] for p in POINTS)
    earned = 0
    details = []
    for p in POINTS:
        ok = all(norm(get_path(prediction, path)) == norm(get_path(expected, path)) for path in p["paths"])
        if ok:
            earned += p["weight"]
        details.append({"id": p["id"], "goal": p["goal"], "weight": p["weight"], "passed": ok})
    score = earned / total if total else 0.0
    print(
        json.dumps(
            {"score": round(score, 6), "earned_weight": earned, "total_weight": total, "details": details},
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
