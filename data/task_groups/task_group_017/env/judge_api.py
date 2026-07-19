"""Train-only judge endpoint for Investigation Review Hub."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from flask import Blueprint, jsonify, request


NOTICE = "Train-only judge; no gold answer or rubric details are returned."


def _load_data(data_path: Path) -> dict[str, Any]:
    try:
        with data_path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"tasks": {}}
    if not isinstance(data, dict):
        return {"tasks": {}}
    tasks = data.get("tasks")
    if not isinstance(tasks, dict):
        return {"tasks": {}}
    return data


def _get_path(obj: Any, path: str) -> Any:
    current = obj
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(path)
            current = current[part]
        elif isinstance(current, list) and part.isdigit():
            idx = int(part)
            current = current[idx]
        else:
            raise KeyError(path)
    return current


def _norm_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return " ".join(value.strip().lower().split())
    return value


def _norm_set(value: Any) -> set[Any]:
    if value is None:
        return set()
    if isinstance(value, str):
        parts = [part.strip() for part in value.split(",")]
    elif isinstance(value, (list, tuple, set)):
        parts = list(value)
    else:
        parts = [value]
    return {_norm_scalar(part) for part in parts if part not in ("", None)}


def _compare(kind: str, actual: Any, expected: Any, point: dict[str, Any]) -> bool:
    if kind == "number":
        try:
            actual_num = float(actual)
            expected_num = float(expected)
        except (TypeError, ValueError):
            return False
        tolerance = float(point.get("tolerance", 0))
        return math.isclose(actual_num, expected_num, rel_tol=0, abs_tol=tolerance)

    if kind == "boolean":
        if not isinstance(actual, bool) or not isinstance(expected, bool):
            return False
        return actual is expected

    if kind == "set":
        return _norm_set(actual) == _norm_set(expected)

    if kind == "subset":
        return _norm_set(expected).issubset(_norm_set(actual))

    return _norm_scalar(actual) == _norm_scalar(expected)


def _check_passes(check: dict[str, Any], answer: dict[str, Any]) -> bool:
    kind = check.get("type", "exact")
    if kind == "list_has_object":
        field = check.get("field")
        key = check.get("key")
        key_value = check.get("key_value")
        if not isinstance(field, str) or not isinstance(key, str):
            return False
        try:
            items = _get_path(answer, field)
        except KeyError:
            return False
        if not isinstance(items, list):
            return False
        target = None
        for item in items:
            if isinstance(item, dict) and _norm_scalar(item.get(key)) == _norm_scalar(key_value):
                target = item
                break
        if target is None:
            return False
        object_checks = check.get("checks", [])
        if not isinstance(object_checks, list) or not object_checks:
            return True
        for object_check in object_checks:
            if not isinstance(object_check, dict):
                return False
            path = object_check.get("path")
            if not isinstance(path, str) or not path:
                return False
            try:
                actual = _get_path(target, path)
            except KeyError:
                return False
            expected = object_check.get("expected")
            check_kind = object_check.get("type", "exact")
            if not _compare(check_kind, actual, expected, object_check):
                return False
        return True

    field = check.get("field")
    if not isinstance(field, str) or not field:
        return False
    try:
        actual = _get_path(answer, field)
    except KeyError:
        return False
    expected = check.get("expected")
    return _compare(kind, actual, expected, check)


def _point_passes(point: dict[str, Any], answer: dict[str, Any]) -> bool:
    checks = point.get("checks")
    if isinstance(checks, list) and checks:
        return all(isinstance(check, dict) and _check_passes(check, answer) for check in checks)
    return _check_passes(point, answer)


def _score_answer(task_spec: dict[str, Any], answer: Any) -> tuple[float, bool]:
    if not isinstance(answer, dict):
        return 0.0, False
    points = task_spec.get("points", [])
    if not isinstance(points, list) or not points:
        return 0.0, False
    weighted_total = 0.0
    earned = 0.0
    for point in points:
        if not isinstance(point, dict):
            continue
        weight = point.get("weight", 1)
        try:
            weight_value = float(weight)
        except (TypeError, ValueError):
            weight_value = 1.0
        if weight_value <= 0:
            continue
        weighted_total += weight_value
        if _point_passes(point, answer):
            earned += weight_value
    if weighted_total <= 0:
        return 0.0, False
    score = max(0.0, min(1.0, earned / weighted_total))
    return score, score >= 0.999999


def create_judge_blueprint(data_path: str | Path) -> Blueprint:
    data_path = Path(data_path)
    blueprint = Blueprint("judge_api", __name__)

    @blueprint.post("/api/judge")
    def judge():
        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE}), 400

        task_id = payload.get("task_id")
        if not isinstance(task_id, str):
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE}), 400
        if task_id.startswith("test_"):
            return jsonify({"notice": "Train-only judge; test task ids are not supported."}), 403
        if not task_id.startswith("train_"):
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE}), 404

        data = _load_data(data_path)
        task_spec = data.get("tasks", {}).get(task_id)
        if not isinstance(task_spec, dict):
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE}), 404

        score, correct = _score_answer(task_spec, payload.get("answer"))
        return jsonify({"score": round(score, 6), "correct": correct, "notice": NOTICE})

    return blueprint


def register_judge(app, data_path: str | Path) -> None:
    app.register_blueprint(create_judge_blueprint(data_path))
