#!/usr/bin/env python3
import argparse
import json
import math
import sys


def read_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def normalize(value):
    if isinstance(value, str):
        return " ".join(value.strip().split())
    if isinstance(value, list):
        return sorted(normalize(v) for v in value)
    if isinstance(value, dict):
        return {k: normalize(v) for k, v in value.items()}
    return value


def value_at(obj, path):
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def fields_match(prediction, fields):
    for field, expected in fields.items():
        actual = value_at(prediction, field)
        if isinstance(expected, (int, float)) and not isinstance(expected, bool):
            try:
                if not math.isclose(float(actual), float(expected), abs_tol=0.000001):
                    return False
            except (TypeError, ValueError):
                return False
        elif normalize(actual) != normalize(expected):
            return False
    return True


def points_from_rubric(rubric, explicit_gold):
    if "points" in rubric:
        points = []
        for item in rubric["points"]:
            if "fields" in item:
                fields = item["fields"]
            else:
                path = item["path"]
                fields = {path: value_at(explicit_gold, path)}
            points.append(
                {
                    "id": item.get("id", item.get("goal", "point")),
                    "goal": item.get("goal", item.get("description", item.get("id", ""))),
                    "weight": int(item.get("weight", 1)),
                    "fields": fields,
                }
            )
        return points
    if "checks" in rubric:
        gold = rubric.get("gold", explicit_gold)
        return [
            {
                "id": item.get("name", "check"),
                "goal": item.get("description", item.get("name", "")),
                "weight": int(item.get("weight", item.get("points", 1))),
                "fields": {field: value_at(gold, field) for field in item["fields"]},
            }
            for item in rubric["checks"]
        ]
    if "criteria" in rubric:
        points = []
        for item in rubric["criteria"]:
            if "fields" in item:
                fields = {field: value_at(explicit_gold, field) for field in item["fields"]}
            else:
                fields = {item["field"]: value_at(explicit_gold, item["field"])}
            points.append(
                {
                    "id": item.get("id", item.get("field", "criterion")),
                    "goal": item.get("description", item.get("id", "")),
                    "weight": int(item.get("weight", 1)),
                    "fields": fields,
                }
            )
        return points
    raise ValueError("rubric must contain points, checks, or criteria")


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--answer")
    parser.add_argument("--rubric")
    parser.add_argument("--gold")
    args = parser.parse_args()
    if args.answer and args.rubric:
        return args.rubric, args.answer, args.gold
    if len(args.paths) == 2:
        return args.paths[0], args.paths[1], None
    if len(args.paths) == 3:
        return args.paths[2], args.paths[0], args.paths[1]
    parser.error("expected <rubric> <prediction>, --answer/--rubric, or <prediction> <gold> <rubric>")


def main():
    rubric_path, prediction_path, gold_path = parse_args()
    rubric = read_json(rubric_path)
    prediction = read_json(prediction_path)
    explicit_gold = read_json(gold_path) if gold_path else None
    points = points_from_rubric(rubric, explicit_gold)
    total = sum(point["weight"] for point in points)
    earned = 0
    details = []
    for point in points:
        passed = fields_match(prediction, point["fields"])
        if passed:
            earned += point["weight"]
        details.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "passed": passed,
            }
        )
    score = earned / total if total else 0.0
    print(
        json.dumps(
            {
                "score": round(score, 6),
                "earned_weight": earned,
                "total_weight": total,
                "details": details,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if math.isclose(score, 1.0) else 1


if __name__ == "__main__":
    sys.exit(main())
