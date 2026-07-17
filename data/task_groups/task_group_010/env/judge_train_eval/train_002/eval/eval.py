#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    {
        "id": "SP001",
        "goal": "Correct review window and nine-index universe.",
        "weight": 1,
        "paths": [["review_window"], ["index_set"]],
    },
    {
        "id": "SP002",
        "goal": "Correct highest positive correlation pair and rounded value.",
        "weight": 3,
        "path": ["extreme_pairs", "highest_positive"],
    },
    {
        "id": "SP003",
        "goal": "Correct lowest correlation pair and rounded value.",
        "weight": 3,
        "path": ["extreme_pairs", "lowest"],
    },
    {
        "id": "SP004",
        "goal": "Correct China and Asia dependence concentration flag.",
        "weight": 2,
        "path": ["concentration"],
    },
    {
        "id": "SP005",
        "goal": "Correct diversification candidate set.",
        "weight": 2,
        "path": ["diversification_candidates"],
    },
    {
        "id": "SP006",
        "goal": "Correct two sleeve actions.",
        "weight": 2,
        "path": ["sleeve_actions"],
    },
]


def load_json(path):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def get_path(obj, path):
    cur = obj
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def get_point_value(obj, point):
    if "paths" in point:
        return {"/".join(path): get_path(obj, path) for path in point["paths"]}
    return get_path(obj, point["path"])


def normalize(value):
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, list):
        return [normalize(item) for item in value]
    if isinstance(value, dict):
        return {key: normalize(value[key]) for key in sorted(value)}
    return value


def main():
    if len(sys.argv) != 2:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(point["weight"] for point in POINTS),
                    "normalized_score": 0,
                    "error": "Usage: eval.py <prediction_json_path>",
                    "points": [],
                },
                indent=2,
            )
        )
        return 2

    answer_path = Path(__file__).resolve().parent.parent / "output" / "answer.json"
    try:
        expected = load_json(answer_path)
        predicted = load_json(sys.argv[1])
    except Exception as exc:
        print(
            json.dumps(
                {
                    "score": 0,
                    "max_score": sum(point["weight"] for point in POINTS),
                    "normalized_score": 0,
                    "error": str(exc),
                    "points": [],
                },
                indent=2,
            )
        )
        return 1

    details = []
    score = 0
    for point in POINTS:
        exp = normalize(get_point_value(expected, point))
        pred = normalize(get_point_value(predicted, point))
        matched = pred == exp
        earned = point["weight"] if matched else 0
        score += earned
        details.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "earned": earned,
                "matched": matched,
                "expected": exp,
                "predicted": pred,
            }
        )

    max_score = sum(point["weight"] for point in POINTS)
    print(
        json.dumps(
            {
                "score": score,
                "max_score": max_score,
                "normalized_score": round(score / max_score, 6),
                "points": details,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
