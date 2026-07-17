"""Isolated train-evaluator runner for the optional judge control surface."""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

NOTICE = "This endpoint is available for training tasks only."
ENV_ROOT = Path(__file__).resolve().parent
ASSET_ROOT = ENV_ROOT / "judge_assets"
SPEC_PATH = ENV_ROOT / "judge_specs.json"
ALLOWED_TASK_IDS = {f"train_{number:03d}" for number in range(1, 6)}
MAX_ANSWER_BYTES = 60_000
MAX_EVALUATOR_OUTPUT_BYTES = 2_000_000
EVALUATOR_TIMEOUT_SECONDS = 3.0


class JudgeRejected(Exception):
    """A request cannot be evaluated without exposing internal detail."""


def load_evaluators() -> dict[str, Path]:
    """Load the train-only allowlist from the environment-owned specification."""
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or set(raw) != ALLOWED_TASK_IDS:
        raise RuntimeError("judge specification has an invalid task allowlist")
    asset_root = ASSET_ROOT.resolve()
    evaluators: dict[str, Path] = {}
    for task_id, spec in raw.items():
        if not isinstance(spec, dict) or not isinstance(spec.get("evaluator"), str):
            raise RuntimeError("judge specification has an invalid evaluator entry")
        evaluator = (ENV_ROOT / spec["evaluator"]).resolve()
        if not evaluator.is_relative_to(asset_root) or not evaluator.is_file():
            raise RuntimeError("judge evaluator escapes the asset root or is missing")
        evaluators[task_id] = evaluator
    return evaluators


EVALUATORS = load_evaluators()


def rejection() -> dict[str, Any]:
    return {"score": 0.0, "correct": False, "notice": NOTICE}


def known_train_task(task_id: Any) -> bool:
    return isinstance(task_id, str) and task_id in EVALUATORS


def evaluate_answer(task_id: str, answer: Any) -> dict[str, Any]:
    """Run the exact task evaluator and retain only its normalized score."""
    evaluator = EVALUATORS.get(task_id)
    if evaluator is None or not evaluator.is_file() or not isinstance(answer, dict):
        raise JudgeRejected
    try:
        candidate_bytes = json.dumps(
            answer, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise JudgeRejected from exc
    if len(candidate_bytes) > MAX_ANSWER_BYTES:
        raise JudgeRejected

    try:
        with tempfile.TemporaryDirectory(prefix="observatory-judge-") as directory:
            temp_root = Path(directory)
            candidate_path = temp_root / "candidate.json"
            result_path = temp_root / "result.json"
            candidate_path.write_bytes(candidate_bytes)
            os.chmod(candidate_path, 0o600)
            with result_path.open("wb") as result_handle:
                completed = subprocess.run(
                    [sys.executable, "-I", str(evaluator), str(candidate_path)],
                    cwd=evaluator.parent,
                    stdin=subprocess.DEVNULL,
                    stdout=result_handle,
                    stderr=subprocess.DEVNULL,
                    timeout=EVALUATOR_TIMEOUT_SECONDS,
                    check=False,
                    close_fds=True,
                    env={"PYTHONIOENCODING": "utf-8", "PYTHONHASHSEED": "0"},
                )
            if completed.returncode != 0 or result_path.stat().st_size > MAX_EVALUATOR_OUTPUT_BYTES:
                raise JudgeRejected
            raw_result = result_path.read_bytes()
    except (OSError, subprocess.SubprocessError) as exc:
        raise JudgeRejected from exc

    try:
        parsed = json.loads(raw_result)
        raw_score = parsed["score"]
        if isinstance(raw_score, bool):
            raise ValueError
        score = float(raw_score)
        if not math.isfinite(score):
            raise ValueError
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise JudgeRejected from exc
    score = min(1.0, max(0.0, score))
    return {"score": score, "correct": score >= 1.0 - 1e-12, "notice": NOTICE}
