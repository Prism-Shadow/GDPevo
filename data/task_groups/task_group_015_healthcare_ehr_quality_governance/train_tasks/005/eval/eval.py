#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {
        "goal": "Correct severe iodinated contrast allergy update.",
        "id": "SP001",
        "paths": ["allergy_update"],
        "weight": 3,
    },
    {"goal": "Correct heart-failure diagnosis update.", "id": "SP002", "paths": ["diagnosis_update"], "weight": 3},
    {"goal": "Correct recent encounter evidence set.", "id": "SP003", "paths": ["recent_encounter_ids"], "weight": 2},
    {
        "goal": "Correct referral target provider and specialty.",
        "id": "SP004",
        "paths": ["referral_target"],
        "weight": 1,
    },
    {"goal": "Correct unresolved issue set.", "id": "SP005", "paths": ["unresolved_quality_issues"], "weight": 2},
    {"goal": "Correct send-ready status.", "id": "SP006", "paths": ["send_ready"], "weight": 2},
    {"goal": "Correct required letter merge fields.", "id": "SP007", "paths": ["letter_merge_fields"], "weight": 1},
    {"goal": "Correct safety flag for contrast allergy.", "id": "SP008", "paths": ["safety_flags"], "weight": 1},
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
