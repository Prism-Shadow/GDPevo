#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {
        "goal": "Correct merge disposition, canonical target, and source patient.",
        "id": "SP001",
        "paths": ["merge_decision"],
        "weight": 3,
    },
    {
        "goal": "Correct active problem code set preserved after merge.",
        "id": "SP002",
        "paths": ["preserved_active_problem_codes"],
        "weight": 2,
    },
    {
        "goal": "Correct active medication ID set preserved after merge.",
        "id": "SP003",
        "paths": ["preserved_active_medication_ids"],
        "weight": 2,
    },
    {
        "goal": "Correct active allergy label set preserved after merge.",
        "id": "SP004",
        "paths": ["preserved_active_allergy_labels"],
        "weight": 2,
    },
    {
        "goal": "Correctly avoid excluding any true duplicate patient record.",
        "id": "SP005",
        "paths": ["excluded_patient_ids"],
        "weight": 1,
    },
    {"goal": "Correct audit event and merge audit status.", "id": "SP006", "paths": ["audit"], "weight": 2},
    {
        "goal": "Correctly determine no provider contact action is required.",
        "id": "SP007",
        "paths": ["contact_action"],
        "weight": 1,
    },
    {
        "goal": "Correct stable-MRN merge reason code.",
        "id": "SP008",
        "paths": ["merge_decision.reason_code"],
        "weight": 2,
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
