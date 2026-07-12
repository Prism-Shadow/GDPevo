#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {
        "goal": "Correct duplicate consolidation decision.",
        "id": "SP001",
        "paths": ["duplicate_consolidation"],
        "weight": 3,
    },
    {
        "goal": "Correct contact queue with recipient, fax, and reason codes.",
        "id": "SP002",
        "paths": ["contact_queue"],
        "weight": 3,
    },
    {"goal": "Correct chart update decisions.", "id": "SP003", "paths": ["chart_updates"], "weight": 2},
    {"goal": "Correct records request list.", "id": "SP004", "paths": ["records_requests"], "weight": 2},
    {"goal": "Correct tier assignments.", "id": "SP005", "paths": ["tier_assignments"], "weight": 3},
    {"goal": "Correct insurance anomaly.", "id": "SP006", "paths": ["insurance_anomaly"], "weight": 2},
    {
        "goal": "Correct reschedule administrative handling.",
        "id": "SP007",
        "paths": ["reschedule_admin_referral_ids"],
        "weight": 1,
    },
    {"goal": "Correct summary counts.", "id": "SP008", "paths": ["summary_counts"], "weight": 1},
    {"goal": "Correct final queue status.", "id": "SP009", "paths": ["queue_ready_status"], "weight": 2},
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
