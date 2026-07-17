"""Train-only judge facade for Cedar Ridge task-group environments."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


TRAIN_IDS = {f"train_{idx:03d}" for idx in range(1, 6)}
ROOT = Path(__file__).resolve().parent
EVALUATORS = {task_id: ROOT / "judge_train_eval" / f"{task_id}_evaluator.py" for task_id in TRAIN_IDS}


class JudgeError(Exception):
    """Raised for invalid judge requests."""

    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def score_train_answer(task_id: str, answer: Any) -> dict[str, Any]:
    """Run the matching train evaluator and return only redacted score fields."""
    if not isinstance(task_id, str) or not task_id:
        raise JudgeError(400, "task_id is required")
    if task_id.startswith("test_"):
        raise JudgeError(403, "judge is train-only")
    if task_id not in TRAIN_IDS:
        raise JudgeError(404, "unknown train task")
    if not isinstance(answer, dict):
        raise JudgeError(400, "answer must be a JSON object")

    evaluator = EVALUATORS[task_id]
    if not evaluator.exists():
        raise JudgeError(500, "train evaluator is unavailable")

    with tempfile.TemporaryDirectory(prefix="cedar_judge_") as tmp:
        candidate = Path(tmp) / "answer.json"
        candidate.write_text(json.dumps(answer), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(evaluator), str(candidate)],
            check=False,
            capture_output=True,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
            text=True,
            timeout=15,
        )
    if proc.returncode != 0:
        raise JudgeError(400, "candidate answer could not be evaluated")
    try:
        result = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise JudgeError(500, "train evaluator returned invalid JSON") from exc

    score = float(result.get("score", 0.0))
    correct = bool(result.get("correct", score == 1.0))
    return {"score": score, "correct": correct, "notice": "train-only judge"}
