import json
from pathlib import Path

from flask import jsonify, request


NOTICE = "train-only judge; no gold answers or rubric details are returned"
VALID_TRAIN_TASK_IDS = {f"train_{idx:03d}" for idx in range(1, 6)}


def _load_judge_data(data_dir):
    path = Path(data_dir) / "train_judge_data.json"
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _path_value(obj, path):
    if isinstance(path, str):
        parts = [part for part in path.split(".") if part]
    else:
        parts = list(path)
    current = obj
    for part in parts:
        if isinstance(current, dict):
            if part not in current:
                raise KeyError(part)
            current = current[part]
        elif isinstance(current, list):
            current = current[int(part)]
        else:
            raise KeyError(part)
    return current


def _canonical(value):
    if isinstance(value, dict):
        return {key: _canonical(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    return value


def _compare(actual, expected, comparison, tolerance):
    if comparison == "number":
        try:
            return abs(float(actual) - float(expected)) <= float(tolerance or 0)
        except (TypeError, ValueError):
            return False
    if comparison == "bool":
        return isinstance(actual, bool) and isinstance(expected, bool) and actual == expected
    if comparison == "set_equals":
        if not isinstance(actual, list) or not isinstance(expected, list):
            return False
        return sorted(_canonical(actual), key=json.dumps) == sorted(_canonical(expected), key=json.dumps)
    if comparison == "contains_all":
        if not isinstance(actual, list) or not isinstance(expected, list):
            return False
        actual_items = {json.dumps(_canonical(item), sort_keys=True) for item in actual}
        return all(json.dumps(_canonical(item), sort_keys=True) in actual_items for item in expected)
    return _canonical(actual) == _canonical(expected)


def _point_matches(point, answer):
    checks = point.get("checks")
    if checks is None:
        checks = [point]
    if not isinstance(checks, list) or not checks:
        return False
    for check in checks:
        comparison = check.get("comparison", point.get("comparison", "exact"))
        tolerance = check.get("tolerance", point.get("tolerance", 0))
        try:
            actual = _path_value(answer, check["path"])
            if comparison == "filtered_set_equals":
                if not isinstance(actual, list):
                    return False
                allowed = set(check.get("allowed_values", []))
                actual = [item for item in actual if item in allowed]
                comparison = "set_equals"
            matched = _compare(actual, check.get("expected"), comparison, tolerance)
        except (KeyError, IndexError, TypeError, ValueError):
            matched = False
        if not matched:
            return False
    return True


def _score_points(task_spec, answer):
    if "points" not in task_spec:
        expected = task_spec.get("expected_answer", task_spec.get("answer"))
        return 1.0 if _canonical(answer) == _canonical(expected) else 0.0

    total_weight = 0.0
    earned_weight = 0.0
    for point in task_spec["points"]:
        weight = float(point.get("weight", 1))
        total_weight += weight
        matched = _point_matches(point, answer)
        if matched:
            earned_weight += weight
    if total_weight <= 0:
        return 0.0
    return max(0.0, min(1.0, earned_weight / total_weight))


def register_judge(app, data_dir):
    @app.post("/api/judge")
    def judge():
        body = request.get_json(silent=True) or {}
        task_id = body.get("task_id")
        answer = body.get("answer")

        if not isinstance(task_id, str):
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE}), 400
        if task_id.startswith("test_"):
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE}), 403
        if task_id not in VALID_TRAIN_TASK_IDS:
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE}), 404
        if answer is None:
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE}), 400

        judge_data = _load_judge_data(data_dir)
        if not judge_data or task_id not in judge_data:
            return (
                jsonify(
                    {
                        "score": 0.0,
                        "correct": False,
                        "notice": f"{NOTICE}; judge data is not populated",
                    }
                ),
                503,
            )

        score = round(_score_points(judge_data[task_id], answer), 6)
        return jsonify({"score": score, "correct": score >= 0.999999, "notice": NOTICE})
