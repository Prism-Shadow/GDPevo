#!/usr/bin/env python3
"""Reusable exact-match evaluator template for task_group_003 task builders.

Copy this file into a task's eval/eval.py and place a task-specific
scoring.json next to it. The script expects a prediction JSON path as the
first argument and compares configured fields against ../output/answer.json.
"""

from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path


MISSING = object()


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def resolve_path(obj, path: str):
    cur = obj
    for part in path.split("."):
        if "[" in part and part.endswith("]"):
            key, idx_text = part[:-1].split("[", 1)
            if key:
                if not isinstance(cur, dict) or key not in cur:
                    return MISSING
                cur = cur[key]
            try:
                idx = int(idx_text)
            except ValueError:
                return MISSING
            if not isinstance(cur, list) or idx >= len(cur):
                return MISSING
            cur = cur[idx]
        else:
            if not isinstance(cur, dict) or part not in cur:
                return MISSING
            cur = cur[part]
    return cur


def normalize(value, spec):
    if value is MISSING:
        return MISSING
    if spec.get("sort_list"):
        if not isinstance(value, list):
            return value
        sort_key = spec.get("sort_by")
        if sort_key:
            return sorted(value, key=lambda item: item.get(sort_key, ""))
        return sorted(value)
    precision = spec.get("precision")
    if precision is not None and isinstance(value, (int, float)) and not isinstance(value, bool):
        return round(float(value), int(precision))
    return value


def values_equal(expected, actual):
    if expected is MISSING or actual is MISSING:
        return False
    if isinstance(expected, float) or isinstance(actual, float):
        try:
            return math.isclose(float(expected), float(actual), rel_tol=0, abs_tol=1e-9)
        except (TypeError, ValueError):
            return False
    return expected == actual


def contains_all_terms(actual, terms):
    if actual is MISSING or not isinstance(actual, str):
        return False
    normalized = re.sub(r"[^a-z0-9]+", " ", actual.lower())
    words = set(normalized.split())
    return all(term.lower() in words for term in terms)


def main() -> int:
    eval_dir = Path(__file__).resolve().parent
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else eval_dir.parent / "output" / "answer.json"
    answer_path = eval_dir.parent / "output" / "answer.json"
    scoring_path = eval_dir / "scoring.json"

    expected = load_json(answer_path)
    try:
        prediction = load_json(prediction_path)
    except Exception as exc:
        print(
            json.dumps(
                {"score": 0.0, "max_score": 1.0, "error": f"Could not parse prediction JSON: {exc}", "points": []},
                indent=2,
            )
        )
        return 0

    scoring = load_json(scoring_path)
    total_weight = sum(point["weight"] for point in scoring["points"])
    earned = 0
    point_reports = []

    for point in scoring["points"]:
        checks = point["checks"]
        passed_checks = []
        for check in checks:
            path = check["path"]
            if "contains_all" in check:
                got = resolve_path(prediction, path)
                passed_checks.append(contains_all_terms(got, check["contains_all"]))
                continue
            exp = normalize(resolve_path(expected, path), check)
            got = normalize(resolve_path(prediction, path), check)
            passed_checks.append(values_equal(exp, got))
        passed = all(passed_checks)
        if passed:
            earned += point["weight"]
        point_reports.append({"id": point["id"], "goal": point["goal"], "weight": point["weight"], "passed": passed})

    score = earned / total_weight if total_weight else 0.0
    print(
        json.dumps(
            {"score": round(score, 6), "earned_weight": earned, "total_weight": total_weight, "points": point_reports},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
