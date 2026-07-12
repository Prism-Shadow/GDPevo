#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {"goal": "Correct active problem code set.", "id": "SP001", "paths": ["active_problem_codes"], "weight": 3},
    {
        "goal": "Correct active medication and allergy coverage.",
        "id": "SP002",
        "paths": ["active_medication_ids", "active_allergy_labels"],
        "weight": 2,
    },
    {"goal": "Correct four most recent encounter IDs.", "id": "SP003", "paths": ["recent_encounter_ids"], "weight": 2},
    {
        "goal": "Correct most recent immunization.",
        "id": "SP004",
        "paths": ["most_recent_immunization_id"],
        "weight": 1,
    },
    {"goal": "Correct missing packet section.", "id": "SP005", "paths": ["missing_packet_sections"], "weight": 2},
    {"goal": "Correct disclosure status.", "id": "SP006", "paths": ["disclosure_status"], "weight": 2},
    {"goal": "Correct handoff readiness.", "id": "SP007", "paths": ["readiness"], "weight": 2},
    {"goal": "Correct packet risk flags.", "id": "SP008", "paths": ["risk_flags"], "weight": 1},
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
