"""Train-only judge integration for Atlas Commerce Operations."""

from __future__ import annotations

import json
import math
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any


TRAIN_TASK_IDS = frozenset(f"train_{index:03d}" for index in range(1, 6))


MISSING = object()


def _at_path(value: dict[str, Any], path: list[str]) -> Any:
    current: Any = value
    for part in path:
        if not isinstance(current, dict) or part not in current:
            return MISSING
        current = current[part]
    return current


def _strict_equivalent(actual: Any, expected: Any) -> bool:
    if actual is MISSING or type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return set(actual) == set(expected) and all(
            _strict_equivalent(actual[key], value) for key, value in expected.items()
        )
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(
            _strict_equivalent(left, right) for left, right in zip(actual, expected)
        )
    return actual == expected


def _number_equivalent(actual: Any, expected: Any) -> bool:
    return (
        type(actual) in (int, float)
        and type(expected) in (int, float)
        and math.isfinite(float(actual))
        and math.isfinite(float(expected))
        and float(actual) == float(expected)
    )


def _decimal_equivalent(actual: Any, expected: Any, places: str | None = None) -> bool:
    if type(actual) not in (int, float) or type(expected) not in (int, float):
        return False
    if isinstance(actual, float) and not math.isfinite(actual):
        return False
    try:
        left = Decimal(str(actual))
        right = Decimal(str(expected))
        if places is not None:
            quantum = Decimal(places)
            left = left.quantize(quantum, rounding=ROUND_HALF_UP)
            right = right.quantize(quantum, rounding=ROUND_HALF_UP)
        return left == right
    except (InvalidOperation, ValueError):
        return False


def _set_strings_equivalent(actual: Any, expected: Any) -> bool:
    return (
        isinstance(actual, list)
        and isinstance(expected, list)
        and all(type(item) is str for item in actual)
        and all(type(item) is str for item in expected)
        and len(actual) == len(set(actual))
        and set(actual) == set(expected)
    )


def _check(actual: Any, expected: Any, mode: str) -> bool:
    if mode == "strict":
        return _strict_equivalent(actual, expected)
    if mode == "number":
        return _number_equivalent(actual, expected)
    if mode == "decimal":
        return _decimal_equivalent(actual, expected)
    if mode == "money2":
        return _decimal_equivalent(actual, expected, "0.01")
    if mode == "set_strings":
        return _set_strings_equivalent(actual, expected)
    return False


def _score_spec(answer: dict[str, Any], spec: dict[str, Any], spec_path: Path) -> float:
    """Evaluate the same whole-point weighted checks used by train evaluators."""
    answer_file = spec.get("answer_file")
    if not isinstance(answer_file, str):
        return 0.0
    expected_path = spec_path.parent / answer_file
    try:
        expected = json.loads(expected_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return 0.0
    if not isinstance(expected, dict):
        return 0.0

    points = spec.get("points")
    if not isinstance(points, list) or not points:
        return 0.0
    earned = 0.0
    possible = 0.0
    for point in points:
        if not isinstance(point, dict):
            continue
        weight = float(point.get("weight", 1.0))
        if not math.isfinite(weight) or weight <= 0:
            continue
        checks = point.get("checks")
        if not isinstance(checks, list) or not checks:
            continue
        possible += weight
        passed = True
        for check in checks:
            if not isinstance(check, dict):
                passed = False
                break
            path = check.get("path")
            mode = check.get("mode", "strict")
            if (
                not isinstance(path, list)
                or not path
                or not all(isinstance(part, str) and part for part in path)
                or not isinstance(mode, str)
                or not _check(_at_path(answer, path), _at_path(expected, path), mode)
            ):
                passed = False
                break
        if passed:
            earned += weight
    return earned / possible if possible else 0.0


def evaluate_train_answer(task_id: str, answer: dict[str, Any], spec_path: Path) -> dict[str, object]:
    """Return the deliberately narrow public result for an allowed train ID."""
    score = 0.0
    if task_id in TRAIN_TASK_IDS:
        try:
            payload = json.loads(spec_path.read_text(encoding="utf-8"))
            spec = payload.get(task_id) if isinstance(payload, dict) else None
            if isinstance(spec, dict):
                score = max(0.0, min(1.0, _score_spec(answer, spec, spec_path)))
        except (OSError, ValueError, TypeError, OverflowError):
            score = 0.0
    score = round(score, 6)
    return {"score": score, "correct": score == 1.0, "notice": "train-only judge"}
