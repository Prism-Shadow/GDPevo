#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path: Path):
    with path.open() as f:
        return json.load(f)


def get_path(data, path):
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def norm(value):
    if isinstance(value, list):
        return sorted(norm(v) for v in value)
    if isinstance(value, dict):
        return {k: norm(value[k]) for k in sorted(value)}
    if isinstance(value, float):
        return round(value, 4)
    return value


def main():
    if len(sys.argv) < 2:
        print(json.dumps({"score": 0.0, "error": "usage: eval.py PREDICTION_JSON"}))
        return 2

    eval_dir = Path(__file__).resolve().parent
    task_dir = eval_dir.parent
    expected = load_json(task_dir / "output" / "answer.json")
    rubric = load_json(eval_dir / "rubric.json")

    try:
        prediction = load_json(Path(sys.argv[1]))
    except Exception as exc:
        print(json.dumps({"score": 0.0, "error": f"invalid_json: {exc}"}))
        return 0

    total_weight = sum(point["weight"] for point in rubric["scoring_points"])
    earned = 0
    results = []
    for point in rubric["scoring_points"]:
        matched = True
        mismatches = []
        for field in point["fields"]:
            got = norm(get_path(prediction, field))
            want = norm(get_path(expected, field))
            if got != want:
                matched = False
                mismatches.append({"field": field, "expected": want, "actual": got})
        if matched:
            earned += point["weight"]
        results.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "matched": matched,
                "mismatches": mismatches,
            }
        )

    score = earned / total_weight if total_weight else 0.0
    print(
        json.dumps(
            {"score": round(score, 6), "earned_weight": earned, "total_weight": total_weight, "points": results},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
