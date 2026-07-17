"""Isolated adapter for the task group's packaged train evaluators."""

from __future__ import annotations

import hashlib
import json
import math
import os
import signal
import subprocess
import tempfile
from pathlib import Path
from typing import Any


NOTICE = "This endpoint is for train tasks only."
EVALUATOR_TIMEOUT_SECONDS = 10
MAX_EVALUATOR_OUTPUT_BYTES = 5_000_000


class JudgeError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status
        self.message = message


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class TrainJudge:
    """Runs an exact packaged evaluator and retains only its normalized score."""

    def __init__(self, specs_path: str | Path) -> None:
        self._base_dir = Path(specs_path).resolve().parent
        self._judge_root = (self._base_dir / "judge_tasks").resolve()
        try:
            parsed = json.loads(Path(specs_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError("judge configuration is unavailable") from exc
        if (
            not isinstance(parsed, dict)
            or parsed.get("status") != "configured"
            or not isinstance(parsed.get("tasks"), dict)
        ):
            raise RuntimeError("judge configuration is invalid")
        tasks: dict[str, Path] = {}
        for task_id, spec in parsed["tasks"].items():
            if not isinstance(task_id, str) or not task_id.startswith("train_") or not isinstance(spec, dict):
                raise RuntimeError("judge configuration is invalid")
            evaluator = self._validated_file(spec.get("evaluator"), spec.get("evaluator_sha256"))
            if evaluator.name != "eval.sh" or evaluator.parent.name != "eval":
                raise RuntimeError("judge configuration is invalid")
            gold_files = spec.get("gold_files", [])
            if not isinstance(gold_files, list):
                raise RuntimeError("judge configuration is invalid")
            for gold in gold_files:
                if not isinstance(gold, dict):
                    raise RuntimeError("judge configuration is invalid")
                self._validated_file(gold.get("path"), gold.get("sha256"))
            tasks[task_id] = evaluator
        if set(tasks) != {f"train_{index:03d}" for index in range(1, 6)}:
            raise RuntimeError("judge configuration is incomplete")
        self._tasks = tasks

    def _validated_file(self, relative: Any, expected_hash: Any) -> Path:
        if not isinstance(relative, str) or not isinstance(expected_hash, str):
            raise RuntimeError("judge configuration is invalid")
        candidate = (self._base_dir / relative).resolve()
        try:
            candidate.relative_to(self._judge_root)
        except ValueError as exc:
            raise RuntimeError("judge configuration is invalid") from exc
        if not candidate.is_file() or candidate.is_symlink() or _sha256(candidate) != expected_hash:
            raise RuntimeError("judge package integrity check failed")
        return candidate

    @staticmethod
    def _run_evaluator(evaluator: Path, answer: dict[str, Any]) -> float:
        try:
            serialized = json.dumps(
                answer,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise JudgeError(400, "invalid request") from exc
        environment = {
            "HOME": "/nonexistent",
            "LANG": "C.UTF-8",
            "LC_ALL": "C.UTF-8",
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "PYTHONHASHSEED": "0",
        }
        with tempfile.TemporaryDirectory(prefix="asteria-judge-") as temp_dir:
            prediction_path = Path(temp_dir) / "prediction.json"
            prediction_path.write_text(serialized, encoding="utf-8")
            try:
                process = subprocess.Popen(
                    ["/bin/bash", str(evaluator), str(prediction_path)],
                    cwd=evaluator.parent,
                    env=environment,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    start_new_session=True,
                )
            except OSError as exc:
                raise JudgeError(503, "judge unavailable") from exc
            try:
                stdout, _stderr = process.communicate(timeout=EVALUATOR_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired as exc:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.communicate()
                raise JudgeError(503, "judge unavailable") from exc
            if process.returncode != 0 or len(stdout.encode("utf-8")) > MAX_EVALUATOR_OUTPUT_BYTES:
                raise JudgeError(503, "judge unavailable")
            try:
                evaluator_result = json.loads(stdout)
                score = evaluator_result["score"]
            except (json.JSONDecodeError, KeyError, TypeError) as exc:
                raise JudgeError(503, "judge unavailable") from exc
            if (
                isinstance(score, bool)
                or not isinstance(score, (int, float))
                or not math.isfinite(float(score))
                or not 0.0 <= float(score) <= 1.0
            ):
                raise JudgeError(503, "judge unavailable")
            return float(score)

    def evaluate(self, payload: Any) -> tuple[int, dict[str, Any]]:
        if not isinstance(payload, dict) or set(payload) != {"task_id", "answer"}:
            raise JudgeError(400, "invalid request")
        task_id = payload.get("task_id")
        answer = payload.get("answer")
        if not isinstance(task_id, str) or not isinstance(answer, dict):
            raise JudgeError(400, "invalid request")
        if task_id.startswith("test_"):
            raise JudgeError(403, "test tasks are not accepted")
        evaluator = self._tasks.get(task_id)
        if evaluator is None:
            raise JudgeError(404, "unknown train task")
        score = self._run_evaluator(evaluator, answer)
        return 200, {
            "score": score,
            "correct": math.isclose(score, 1.0, rel_tol=0.0, abs_tol=1e-9),
            "notice": NOTICE,
        }


def error_response(exc: JudgeError) -> tuple[int, dict[str, str]]:
    return exc.status, {"error": exc.message, "notice": NOTICE}
