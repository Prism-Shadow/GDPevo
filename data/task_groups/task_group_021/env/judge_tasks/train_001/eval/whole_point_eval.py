#!/usr/bin/env python3
"""Convert a train-task granular evaluator result into exact whole-point scoring.

The legacy evaluators remain the source of deterministic business subchecks.
This adapter enforces two current benchmark requirements:

1. A candidate must preserve the complete required answer structure.
2. Every rubric point must pass all of its deterministic business subchecks.
3. Every rubric point earns either its full normalized weight or zero.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any


def same_scalar_type(candidate: Any, gold: Any) -> bool:
    if isinstance(gold, bool):
        return isinstance(candidate, bool)
    if isinstance(gold, int) and not isinstance(gold, bool):
        return isinstance(candidate, int) and not isinstance(candidate, bool)
    if isinstance(gold, float):
        return (
            isinstance(candidate, (int, float))
            and not isinstance(candidate, bool)
            and math.isfinite(float(candidate))
        )
    if gold is None:
        return candidate is None
    return isinstance(candidate, type(gold))


def validate_structure(candidate: Any, gold: Any, path: str = "$") -> list[str]:
    errors: list[str] = []
    if isinstance(gold, dict):
        if not isinstance(candidate, dict):
            return [f"{path}: expected object"]
        missing = sorted(set(gold) - set(candidate))
        extra = sorted(set(candidate) - set(gold))
        errors.extend(f"{path}: missing required key {key}" for key in missing)
        errors.extend(f"{path}: unexpected key {key}" for key in extra)
        for key in sorted(set(gold) & set(candidate)):
            errors.extend(validate_structure(candidate[key], gold[key], f"{path}.{key}"))
        return errors

    if isinstance(gold, list):
        if not isinstance(candidate, list):
            return [f"{path}: expected array"]
        if not gold:
            return errors
        for index, item in enumerate(candidate):
            exemplar = gold[index] if index < len(gold) else gold[-1]
            errors.extend(validate_structure(item, exemplar, f"{path}[{index}]"))
        return errors

    if not same_scalar_type(candidate, gold):
        errors.append(f"{path}: incompatible scalar type")
    return errors


def rubric_items(result: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("points", "rubric", "details", "scoring_points"):
        value = result.get(key)
        if isinstance(value, list):
            return value
    return []


def main() -> int:
    if len(sys.argv) != 4:
        print(
            "usage: whole_point_eval.py PREDICTION GOLD LEGACY_RESULT",
            file=sys.stderr,
        )
        return 2

    prediction_path = Path(sys.argv[1])
    gold_path = Path(sys.argv[2])
    legacy_result_path = Path(sys.argv[3])

    parse_error: str | None = None
    structure_errors: list[str] = []
    try:
        prediction = json.loads(prediction_path.read_text())
    except Exception as exc:
        prediction = None
        parse_error = str(exc)

    try:
        gold = json.loads(gold_path.read_text())
    except Exception as exc:
        print(json.dumps({"score": 0.0, "evaluator_error": f"gold: {exc}"}))
        return 1

    try:
        legacy = json.loads(legacy_result_path.read_text())
    except Exception as exc:
        legacy = {}
        if parse_error is None:
            parse_error = f"legacy evaluator output: {exc}"

    if parse_error is None:
        structure_errors = validate_structure(prediction, gold)

    items = rubric_items(legacy)
    total_weight = sum(int(item.get("raw_weight", 0)) for item in items)
    points: list[dict[str, Any]] = []
    structure_valid = parse_error is None and not structure_errors
    for item in items:
        point_id = item.get("point_id")
        raw_weight = int(item.get("raw_weight", 0))
        assigned_score = raw_weight / total_weight if total_weight else 0.0
        legacy_fraction = float(item.get("earned_fraction", 0.0))
        complete_goal_passed = abs(legacy_fraction - 1.0) <= 1e-12
        passed = structure_valid and complete_goal_passed
        points.append(
            {
                "point_id": point_id,
                "goal": item.get("goal"),
                "raw_weight": raw_weight,
                "assigned_score": assigned_score,
                "passed": passed,
                "earned_score": assigned_score if passed else 0.0,
                "details": {
                    "legacy_subchecks": item.get("subchecks"),
                    "exact_subcheck_fraction": legacy_fraction,
                    "complete_goal_passed": complete_goal_passed,
                },
            }
        )

    score = sum(point["earned_score"] for point in points)
    output = {
        "score": score,
        "correct": abs(score - 1.0) <= 1e-12,
        "valid_json": parse_error is None,
        "structure_valid": structure_valid,
        "structure_errors": structure_errors[:100],
        "parse_error": parse_error,
        "points": points,
    }
    print(json.dumps(output, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
