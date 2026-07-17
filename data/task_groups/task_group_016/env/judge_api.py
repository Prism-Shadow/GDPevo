"""Train-only aggregate judge for task_group_016.

The service is built from env/ only, so exact copies of the train evaluator
entry modules live under env/judge_evaluators/. The HTTP response intentionally
keeps only the aggregate score, correctness flag, and train-only notice.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


NOTICE = "train-only judge"
BASE_DIR = Path(__file__).resolve().parent
EVALUATORS = {
    "train_001": BASE_DIR / "judge_evaluators" / "train_001_eval.py",
    "train_002": BASE_DIR / "judge_evaluators" / "train_002_eval.py",
    "train_003": BASE_DIR / "judge_evaluators" / "train_003_eval.py",
    "train_004": BASE_DIR / "judge_evaluators" / "train_004_eval.py",
    "train_005": BASE_DIR / "judge_evaluators" / "train_005_eval.py",
}


def _run_evaluator(task_id: str, answer: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    evaluator = EVALUATORS[task_id]
    if not evaluator.exists():
        return 500, {"error": "train evaluator unavailable", "notice": NOTICE}

    with tempfile.NamedTemporaryFile("w", suffix=".json", encoding="utf-8", delete=False) as handle:
        json.dump(answer, handle)
        candidate_path = Path(handle.name)

    try:
        proc = subprocess.run(
            [sys.executable, str(evaluator), str(candidate_path)],
            cwd=str(BASE_DIR),
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        candidate_path.unlink(missing_ok=True)
        return 500, {"error": "train evaluator timed out", "notice": NOTICE}
    finally:
        candidate_path.unlink(missing_ok=True)

    if proc.returncode != 0:
        return 500, {"error": "train evaluator failed", "notice": NOTICE}
    try:
        result = json.loads(proc.stdout)
        score = float(result.get("score", 0.0))
    except (TypeError, ValueError, json.JSONDecodeError):
        return 500, {"error": "train evaluator returned invalid output", "notice": NOTICE}

    score = max(0.0, min(1.0, score))
    return 200, {"score": score, "correct": score >= 0.999999, "notice": NOTICE}


def handle_judge_request(payload: Any) -> tuple[int, dict[str, Any]]:
    if not isinstance(payload, dict):
        return 400, {"error": "invalid request", "notice": NOTICE}
    task_id = payload.get("task_id")
    if not isinstance(task_id, str):
        return 400, {"error": "invalid task_id", "notice": NOTICE}
    if task_id.startswith("test_"):
        return 403, {"error": "test task ids are not accepted", "notice": NOTICE}
    if task_id not in EVALUATORS:
        return 404, {"error": "unknown train task id", "notice": NOTICE}
    answer = payload.get("answer")
    if not isinstance(answer, dict):
        return 400, {"error": "answer must be an object", "notice": NOTICE}
    return _run_evaluator(task_id, answer)
