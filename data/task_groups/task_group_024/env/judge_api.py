import json
import subprocess
import sys
import tempfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
EVALUATOR_DIR = BASE_DIR / "judge_evaluators"
TRAIN_EVALUATORS = {
    "train_001": EVALUATOR_DIR / "train_001.py",
    "train_002": EVALUATOR_DIR / "train_002.py",
    "train_003": EVALUATOR_DIR / "train_003.py",
    "train_004": EVALUATOR_DIR / "train_004.py",
    "train_005": EVALUATOR_DIR / "train_005.py",
}


def judge_enabled(environ):
    return environ.get("TASK_ENV_ENABLE_JUDGE") == "1"


def normalized_score(result):
    raw_score = result.get("score", 0)
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return 0.0
    if 0.0 <= score <= 1.0:
        return round(score, 6)
    max_score = result.get("max_score", result.get("max_raw"))
    try:
        denominator = float(max_score)
    except (TypeError, ValueError):
        return 0.0
    if denominator <= 0:
        return 0.0
    return round(max(0.0, min(1.0, score / denominator)), 6)


def run_train_evaluator(task_id, answer):
    evaluator = TRAIN_EVALUATORS.get(task_id)
    if evaluator is None or not evaluator.exists():
        return 404, {
            "error": "unsupported",
            "train_only": True,
            "notice": "No train evaluator is registered for this task id.",
        }

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
        json.dump(answer, handle, separators=(",", ":"), sort_keys=True)
        candidate_path = Path(handle.name)

    try:
        completed = subprocess.run(
            [sys.executable, str(evaluator), str(candidate_path)],
            check=False,
            capture_output=True,
            text=True,
            timeout=20,
        )
        if completed.returncode != 0:
            return 200, {
                "score": 0.0,
                "correct": False,
                "train_only": True,
                "notice": "This endpoint evaluates train task answers only and does not reveal gold answers or rubric details.",
            }
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError:
            result = {}
        score = normalized_score(result)
        return 200, {
            "score": score,
            "correct": score >= 0.999999,
            "train_only": True,
            "notice": "This endpoint evaluates train task answers only and does not reveal gold answers or rubric details.",
        }
    finally:
        try:
            candidate_path.unlink()
        except OSError:
            pass


def handle_judge_request(payload):
    task_id = payload.get("task_id") if isinstance(payload, dict) else None
    if not isinstance(task_id, str) or not task_id:
        return 400, {
            "error": "task_id is required",
            "train_only": True,
            "notice": "This endpoint is for train task answer checks only.",
        }
    if task_id.startswith("test_"):
        return 403, {
            "error": "test task ids are not supported",
            "train_only": True,
            "notice": "This endpoint never evaluates or reveals hidden test answers.",
        }
    if not task_id.startswith("train_"):
        return 400, {
            "error": "unsupported task id",
            "train_only": True,
            "notice": "Only train task ids can be considered by this endpoint.",
        }
    answer = payload.get("answer") if isinstance(payload, dict) else None
    if not isinstance(answer, dict):
        return 400, {
            "error": "answer object is required",
            "train_only": True,
            "notice": "This endpoint evaluates train task answers only.",
        }
    return run_train_evaluator(task_id, answer)
