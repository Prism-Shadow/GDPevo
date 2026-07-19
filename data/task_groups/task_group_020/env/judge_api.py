import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request


TRAIN_TASKS = {f"train_{idx:03d}" for idx in range(1, 6)}
NOTICE = "Train-only judge. Test task ids are rejected."


def create_judge_blueprint():
    blueprint = Blueprint("judge_api", __name__)

    @blueprint.post("/api/judge")
    def judge():
        payload = request.get_json(silent=True) or {}
        task_id = str(payload.get("task_id", "")).strip()
        answer = payload.get("answer")

        if task_id.startswith("test_"):
            return jsonify(
                {"score": 0.0, "correct": False, "notice": NOTICE, "error": "test task ids are rejected"}
            ), 403
        if task_id not in TRAIN_TASKS:
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE, "error": "unknown train task id"}), 404
        if answer is None:
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE, "error": "missing answer"}), 400

        evaluator = find_evaluator(task_id)
        if evaluator is None:
            return jsonify(
                {"score": 0.0, "correct": False, "notice": NOTICE, "error": "train evaluator unavailable"}
            ), 503

        try:
            score = run_evaluator(evaluator, answer)
        except Exception:
            return jsonify({"score": 0.0, "correct": False, "notice": NOTICE, "error": "train evaluator failed"}), 500

        score = max(0.0, min(1.0, float(score)))
        return jsonify({"score": score, "correct": score >= 0.999, "notice": NOTICE})

    return blueprint


def task_group_root():
    configured = os.environ.get("TASK_GROUP_ROOT")
    if configured:
        return Path(configured).resolve()
    return Path(__file__).resolve().parent.parent


def find_evaluator(task_id):
    root = task_group_root()
    suffix = task_id.removeprefix("train_")
    candidates = [
        root / "train_tasks" / suffix / "eval" / "eval.sh",
        root / "train_tasks" / task_id / "eval" / "eval.sh",
        root / "train_tasks" / suffix / "evaluator.py",
        root / "train_tasks" / task_id / "evaluator.py",
        root / "tasks" / task_id / "evaluator.py",
        root / "train" / task_id / "evaluator.py",
        root / "evaluators" / f"{task_id}.py",
        root / "evaluators" / task_id / "evaluator.py",
    ]
    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    if root.exists():
        for candidate in root.rglob("*"):
            if not candidate.is_file():
                continue
            name = candidate.name.lower()
            path_text = str(candidate).lower()
            if task_id in path_text and (name in {"eval.sh", "evaluator.py"} or name.startswith("eval_")):
                return candidate
    return None


def run_evaluator(evaluator, answer):
    with tempfile.TemporaryDirectory(prefix="judge_answer_") as tmpdir:
        answer_path = Path(tmpdir) / "candidate_answer.json"
        answer_path.write_text(json.dumps(answer, indent=2, sort_keys=True), encoding="utf-8")
        if evaluator.suffix == ".py":
            cmd = [sys.executable, str(evaluator), str(answer_path)]
        else:
            cmd = [str(evaluator), str(answer_path)]
        proc = subprocess.run(
            cmd,
            cwd=str(evaluator.parent),
            text=True,
            capture_output=True,
            timeout=30,
            check=False,
        )
    parsed = extract_score(proc.stdout)
    if parsed is not None:
        return parsed
    return 1.0 if proc.returncode == 0 else 0.0


def extract_score(stdout):
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, dict) and isinstance(parsed.get("score"), (int, float)):
        return float(parsed["score"])
    match = re.search(r"\bscore\b\s*[:=]\s*([01](?:\.\d+)?)", text, flags=re.IGNORECASE)
    if match:
        return float(match.group(1))
    return None
