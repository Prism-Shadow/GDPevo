import json
import os
import subprocess
import tempfile
from pathlib import Path

from flask import Blueprint, jsonify, request


TRAIN_TASKS = {f"train_{idx:03d}" for idx in range(1, 6)}


def create_judge_blueprint():
    blueprint = Blueprint("judge_api", __name__)

    @blueprint.post("/api/judge")
    def judge():
        payload = request.get_json(silent=True) or {}
        task_id = str(payload.get("task_id", "")).strip()
        answer = payload.get("answer")

        if task_id.startswith("test_"):
            return jsonify({"error": "test task ids are not accepted", "notice": "train-only judge"}), 403
        if task_id not in TRAIN_TASKS:
            return jsonify({"error": "unknown train task id", "notice": "train-only judge"}), 404
        if answer is None:
            return jsonify({"error": "missing answer", "notice": "train-only judge"}), 400

        task_group_root = Path(os.environ.get("TASK_GROUP_ROOT", "/task_group")).resolve()
        eval_script = task_group_root / "train_tasks" / task_id.removeprefix("train_") / "eval" / "eval.sh"
        if not eval_script.exists():
            return jsonify({"error": "train evaluator unavailable", "notice": "train-only judge"}), 503

        with tempfile.TemporaryDirectory(prefix="judge_answer_") as tmpdir:
            answer_path = Path(tmpdir) / "answer.json"
            answer_path.write_text(json.dumps(answer, indent=2, sort_keys=True), encoding="utf-8")
            proc = subprocess.run(
                [str(eval_script), str(answer_path)],
                cwd=str(eval_script.parent),
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )

        score = _extract_score(proc.stdout)
        if score is None:
            score = 1.0 if proc.returncode == 0 else 0.0
        score = max(0.0, min(1.0, float(score)))
        return jsonify({"score": score, "correct": score >= 0.999, "notice": "train-only judge"})

    return blueprint


def _extract_score(stdout):
    text = (stdout or "").strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(parsed, dict) and isinstance(parsed.get("score"), (int, float)):
        return parsed["score"]
    return None
