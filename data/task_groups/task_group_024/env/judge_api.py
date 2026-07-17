#!/usr/bin/env python3
"""Train-task answer judging helper for shared task-group environments."""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
TRAIN_TASKS = ROOT / "judge_tasks"
JUDGE_TIMEOUT = int(os.environ.get("JUDGE_TIMEOUT", "30"))
MAX_ANSWER_BYTES = 100_000
JUDGE_SCOPE = "train_only"
JUDGE_NOTICE = (
    "This judge API is only valid for train-task feedback during reflect skill "
    "generation/training. It is not a test-time tool and must not be used for "
    "test tasks or test solving."
)


def _response(status: int, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
    return status, {**payload, "scope": JUDGE_SCOPE, "notice": JUDGE_NOTICE}


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _score_from_evaluator(payload: Any) -> float | None:
    if not isinstance(payload, dict):
        return None

    for key in ("normalized_score", "total_score"):
        value = _number(payload.get(key))
        if value is not None and 0.0 <= value <= 1.0:
            return value

    for earned_key, total_key in (
        ("earned_score", "max_score"),
        ("earned_weight", "total_weight"),
        ("earned_points", "total_points"),
        ("earned", "total"),
        ("raw_score", "raw_total"),
        ("score", "max_score"),
    ):
        earned = _number(payload.get(earned_key))
        total = _number(payload.get(total_key))
        if earned is not None and total is not None and total > 0:
            return max(0.0, min(1.0, earned / total))

    value = _number(payload.get("score"))
    if value is not None and 0.0 <= value <= 1.0:
        return value

    return None


def _task_dir(task_id: Any) -> tuple[Path | None, str | None]:
    raw = str(task_id or "").strip()
    if raw.startswith("test_"):
        return None, "judge_api only scores train tasks during reflect training"
    if raw.startswith("train_"):
        suffix = raw.removeprefix("train_")
    else:
        suffix = raw
    if not suffix.isdigit():
        return None, "task_id must be train_001..train_005 or 001..005"
    task_num = f"{int(suffix):03d}"
    task_dir = TRAIN_TASKS / task_num
    if not task_dir.is_dir():
        return None, f"unknown train task: train_{task_num}"
    return task_dir, None


def _candidate_from_request(body: dict[str, Any]) -> tuple[Any, str | None]:
    for key in ("answer", "answer_json", "candidate", "prediction"):
        if key in body:
            return body[key], None
    return None, "request body must include an answer object"


def judge_answer_request(raw_body: bytes) -> tuple[int, dict[str, Any]]:
    """Judge a candidate answer for a train task.

    Expected JSON body:
      {"task_id": "train_001", "answer": {...}}

    The endpoint intentionally rejects test task ids. It returns normalized score,
    correctness, and a train-only usage notice; evaluator internals and gold
    answers remain hidden.
    """

    try:
        body = json.loads(raw_body.decode("utf-8") if raw_body else "{}")
    except ValueError as exc:
        return _response(400, {"ok": False, "error": "invalid_json", "message": str(exc)})
    if not isinstance(body, dict):
        return _response(
            400, {"ok": False, "error": "invalid_request", "message": "request body must be a JSON object"}
        )

    task_dir, error = _task_dir(body.get("task_id"))
    if error:
        return _response(400, {"ok": False, "error": "invalid_task", "message": error})

    candidate, error = _candidate_from_request(body)
    if error:
        return _response(400, {"ok": False, "error": "invalid_request", "message": error})

    evaluator = task_dir / "eval" / "evaluate.py"
    if not evaluator.is_file():
        return _response(500, {"ok": False, "error": "missing_evaluator", "message": "train evaluator not found"})

    candidate_path: Path | None = None
    try:
        serialized = json.dumps(candidate, ensure_ascii=False, allow_nan=False).encode("utf-8")
        if len(serialized) > MAX_ANSWER_BYTES:
            return _response(
                413, {"ok": False, "error": "answer_too_large", "message": "answer exceeds size limit"}
            )
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as handle:
            candidate_path = Path(handle.name)
            handle.write(serialized.decode("utf-8"))

        result = subprocess.run(
            [sys.executable, "-I", str(evaluator.resolve()), str(candidate_path)],
            cwd=str(evaluator.parent),
            text=True,
            capture_output=True,
            timeout=JUDGE_TIMEOUT,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _response(
            504, {"ok": False, "error": "judge_timeout", "message": f"evaluator exceeded {JUDGE_TIMEOUT}s"}
        )
    except (TypeError, ValueError) as exc:
        return _response(
            400, {"ok": False, "error": "invalid_answer", "message": f"answer is not JSON serializable: {exc}"}
        )
    except OSError:
        return _response(500, {"ok": False, "error": "judge_error", "message": "failed to run evaluator"})
    finally:
        if candidate_path is not None:
            candidate_path.unlink(missing_ok=True)

    try:
        evaluator_payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return _response(
            500,
            {
                "ok": False,
                "error": "judge_parse_error",
                "message": "evaluator did not return JSON",
            },
        )

    score = _score_from_evaluator(evaluator_payload)
    if score is None:
        return _response(
            500,
            {
                "ok": False,
                "error": "judge_score_error",
                "message": "evaluator output did not contain a normalized score",
            },
        )

    normalized = round(score, 6)
    task_id = f"train_{task_dir.name}"
    return _response(
        200,
        {
            "ok": True,
            "task_id": task_id,
            "score": normalized,
            "correct": math.isclose(normalized, 1.0, abs_tol=1e-6),
        },
    )
