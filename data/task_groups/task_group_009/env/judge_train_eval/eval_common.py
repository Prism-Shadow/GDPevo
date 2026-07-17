#!/usr/bin/env python3
import json
import sys
from pathlib import Path


MISSING = object()


def load_json(path):
    with Path(path).open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def value_at(obj, path):
    cur = obj
    for key in path:
        if isinstance(cur, dict) and key in cur:
            cur = cur[key]
        elif isinstance(cur, list) and isinstance(key, int) and 0 <= key < len(cur):
            cur = cur[key]
        else:
            return MISSING
    return cur


def normalize(value):
    if isinstance(value, float):
        return round(value, 10)
    if isinstance(value, list):
        return [normalize(v) for v in value]
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in sorted(value.items())}
    return value


def main():
    if len(sys.argv) != 4:
        print("Usage: eval_common.py EXPECTED_JSON CONFIG_JSON PREDICTION_JSON", file=sys.stderr)
        return 2

    expected = load_json(sys.argv[1])
    config = load_json(sys.argv[2])
    try:
        prediction = load_json(sys.argv[3])
    except Exception as exc:
        points = [
            {
                "id": point["id"],
                "weight": point["weight"],
                "matched": False,
                "reason": f"prediction JSON could not be parsed: {exc}",
            }
            for point in config["points"]
        ]
        total_weight = sum(p["weight"] for p in points)
        print(json.dumps({"score": 0.0, "total_weight": total_weight, "points": points}, indent=2))
        return 0

    total_weight = sum(point["weight"] for point in config["points"])
    earned = 0
    results = []
    for point in config["points"]:
        matched = True
        mismatches = []
        for path in point["paths"]:
            exp = value_at(expected, path)
            got = value_at(prediction, path)
            if got is MISSING or normalize(got) != normalize(exp):
                matched = False
                mismatches.append({"path": path, "expected": exp, "actual": None if got is MISSING else got})
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
    print(json.dumps({"score": round(score, 6), "total_weight": total_weight, "points": results}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
