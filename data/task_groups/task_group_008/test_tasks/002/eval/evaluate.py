from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_path(obj, path):
    cur = obj
    for part in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(part)]
        else:
            cur = cur[part]
    return cur


def equal(a, b):
    if isinstance(b, float):
        try:
            return round(float(a), 2) == round(b, 2)
        except Exception:
            return False
    if isinstance(b, int) and not isinstance(b, bool):
        try:
            return int(a) == b
        except Exception:
            return False
    if isinstance(b, list):
        return sorted(a) == sorted(b)
    return a == b


def main():
    if len(sys.argv) != 2:
        print("Usage: evaluate.py prediction.json", file=sys.stderr)
        return 2
    here = Path(__file__).resolve().parent
    answer = load_json(here.parent / "output" / "answer.json")
    rubric = load_json(here / "rubric.json")
    try:
        pred = load_json(sys.argv[1])
    except Exception as exc:
        result = {
            "score": 0.0,
            "max_score": 1.0,
            "error": f"Could not parse prediction JSON: {exc}",
            "points": [],
        }
        print(json.dumps(result, indent=2))
        return 0

    total = sum(p["weight"] for p in rubric["points"])
    earned = 0
    details = []
    for point in rubric["points"]:
        ok = True
        mismatches = []
        for path in point["paths"]:
            try:
                expected = get_path(answer, path)
                actual = get_path(pred, path)
                if not equal(actual, expected):
                    ok = False
                    mismatches.append({"path": path, "expected": expected, "actual": actual})
            except Exception as exc:
                ok = False
                mismatches.append({"path": path, "error": str(exc)})
        if ok:
            earned += point["weight"]
        details.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "passed": ok,
                "mismatches": mismatches,
            }
        )
    result = {
        "score": round(earned / total, 6),
        "raw_earned": earned,
        "raw_total": total,
        "points": details,
    }
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
