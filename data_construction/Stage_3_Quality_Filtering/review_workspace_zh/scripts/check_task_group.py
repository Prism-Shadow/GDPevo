#!/usr/bin/env python3
"""Check task_group structural validity for quality review."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


REQUIRED_TOP_LEVEL_KEYS = {"task_group", "env", "train_tasks", "test_tasks"}
REQUIRED_TASK_GROUP_KEYS = {"task_group_id", "scenario_id", "source_examples", "domain", "description"}
REQUIRED_TASK_KEYS = {
    "task_id",
    "input",
    "prompt_txt",
    "payloads",
    "notes",
    "output",
    "answer_json",
    "eval",
}
REQUIRED_EVAL_KEYS = {"script", "files", "rubric"}


class Checker:
    def __init__(self, task_group_dir: Path, *, skip_eval: bool, timeout: int) -> None:
        self.root = task_group_dir.resolve()
        self.skip_eval = skip_eval
        self.timeout = timeout
        self.errors: list[str] = []
        self.task_group_id = self.root.name

    def fail(self, message: str) -> None:
        self.errors.append(message)

    def rel_path(self, value: Any, field_name: str) -> Path | None:
        if not isinstance(value, str) or not value.strip():
            self.fail(f"{field_name}: expected a non-empty relative path")
            return None
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            self.fail(f"{field_name}: path must stay inside task group: {value}")
            return None
        return self.root / path

    def require_path(self, value: Any, field_name: str, *, kind: str) -> Path | None:
        path = self.rel_path(value, field_name)
        if path is None:
            return None
        if kind == "file" and not path.is_file():
            self.fail(f"{field_name}: file not found: {value}")
        elif kind == "dir" and not path.is_dir():
            self.fail(f"{field_name}: directory not found: {value}")
        return path

    def load_task_group_yaml(self) -> dict[str, Any] | None:
        if not self.root.is_dir():
            self.fail(f"task group directory not found: {self.root}")
            return None

        task_group_yaml = self.root / "task_group.yaml"
        if not task_group_yaml.is_file():
            self.fail("missing task_group.yaml")
            return None

        try:
            data = yaml.safe_load(task_group_yaml.read_text(encoding="utf-8"))
        except Exception as exc:
            self.fail(f"task_group.yaml parse failed: {exc}")
            return None

        if not isinstance(data, dict):
            self.fail("task_group.yaml must contain a mapping at top level")
            return None

        missing = REQUIRED_TOP_LEVEL_KEYS - set(data)
        if missing:
            self.fail(f"task_group.yaml missing top-level keys: {sorted(missing)}")

        task_group = data.get("task_group")
        if isinstance(task_group, dict):
            missing_meta = REQUIRED_TASK_GROUP_KEYS - set(task_group)
            if missing_meta:
                self.fail(f"task_group missing keys: {sorted(missing_meta)}")
            task_group_id = task_group.get("task_group_id")
            if isinstance(task_group_id, str) and task_group_id.strip():
                self.task_group_id = task_group_id
                if self.root.name != task_group_id:
                    self.fail(f"task_group_id must match directory name: {task_group_id} != {self.root.name}")
            source_examples = task_group.get("source_examples")
            if not isinstance(source_examples, list) or not source_examples:
                self.fail("task_group.source_examples must be a non-empty list")
        else:
            self.fail("task_group must be a mapping")

        return data

    def check_env(self, data: dict[str, Any]) -> None:
        env = data.get("env")
        if not isinstance(env, dict):
            self.fail("env must be a mapping")
            return

        dockerfile = env.get("dockerfile")
        if dockerfile != "env/Dockerfile":
            self.fail("env.dockerfile must be exactly env/Dockerfile")
        self.require_path(dockerfile, "env.dockerfile", kind="file")
        setup_path = self.require_path(env.get("setup"), "env.setup", kind="file")
        if setup_path is not None and setup_path.is_file() and not os.access(setup_path, os.X_OK):
            self.fail("env.setup must be executable")

        state_mode = env.get("state_mode")
        if state_mode not in {"read_only", "mutable"}:
            self.fail("env.state_mode must be either read_only or mutable")

        files = env.get("files")
        if not isinstance(files, list) or not files:
            self.fail("env.files must be a non-empty list")
            return
        has_dockerfile = False
        has_judge_api = False
        for idx, item in enumerate(files):
            self.require_path(item, f"env.files[{idx}]", kind="file")
            if isinstance(item, str):
                parts = Path(item).parts
                has_dockerfile = has_dockerfile or parts == ("env", "Dockerfile")
                has_judge_api = has_judge_api or parts == ("env", "judge_api.py")
        if not has_dockerfile:
            self.fail("env.files must declare env/Dockerfile")
        if not has_judge_api:
            self.fail("env.files must declare env/judge_api.py")

    def check_task_list(self, data: dict[str, Any], split: str) -> None:
        tasks = data.get(split)
        if not isinstance(tasks, list):
            self.fail(f"{split} must be a list")
            return
        if len(tasks) != 5:
            self.fail(f"{split} must contain exactly 5 tasks, got {len(tasks)}")

        seen_task_ids: set[str] = set()
        for index, task in enumerate(tasks, start=1):
            self.check_task(split, index, task, seen_task_ids)

    def check_task(self, split: str, index: int, task: Any, seen_task_ids: set[str]) -> None:
        prefix = f"{split}[{index:03d}]"
        if not isinstance(task, dict):
            self.fail(f"{prefix}: task entry must be a mapping")
            return

        missing = REQUIRED_TASK_KEYS - set(task)
        if missing:
            self.fail(f"{prefix}: missing keys: {sorted(missing)}")

        task_id = task.get("task_id")
        if not isinstance(task_id, str) or not task_id.strip():
            self.fail(f"{prefix}.task_id must be a non-empty string")
        elif task_id in seen_task_ids:
            self.fail(f"{prefix}.task_id is duplicated: {task_id}")
        else:
            seen_task_ids.add(task_id)

        input_dir = self.require_path(task.get("input"), f"{prefix}.input", kind="dir")
        prompt_path = self.require_path(task.get("prompt_txt"), f"{prefix}.prompt_txt", kind="file")
        notes_path = self.require_path(task.get("notes"), f"{prefix}.notes", kind="file")
        self.require_path(task.get("output"), f"{prefix}.output", kind="dir")
        answer_path = self.require_path(task.get("answer_json"), f"{prefix}.answer_json", kind="file")

        if input_dir is not None:
            answer_template_path = input_dir / "payloads" / "answer_template.json"
            if not answer_template_path.is_file():
                self.fail(f"{prefix}: missing input/payloads/answer_template.json")

        self.check_prompt(prompt_path, prefix)
        self.check_notes(notes_path, prefix)
        self.check_payloads(task.get("payloads"), prefix)
        self.check_eval(task.get("eval"), answer_path, prefix)

    def check_prompt(self, prompt_path: Path | None, prefix: str) -> None:
        if prompt_path is None or not prompt_path.is_file():
            return
        text = prompt_path.read_text(encoding="utf-8", errors="ignore")
        if has_cjk(text):
            self.fail(f"{prefix}.prompt_txt contains Chinese text; Chinese should stay in notes/notes.md")

    def check_notes(self, notes_path: Path | None, prefix: str) -> None:
        if notes_path is None or not notes_path.is_file():
            return
        if notes_path.name != "notes.md":
            self.fail(f"{prefix}.notes should point to notes/notes.md")
        text = notes_path.read_text(encoding="utf-8", errors="ignore")
        if not has_cjk(text):
            self.fail(f"{prefix}.notes should be bilingual and include Chinese text")

    def check_payloads(self, payloads: Any, prefix: str) -> None:
        if not isinstance(payloads, list) or not payloads:
            self.fail(f"{prefix}.payloads must be a non-empty list")
            return

        has_answer_template = False
        for payload_idx, payload in enumerate(payloads):
            payload_path = self.require_path(payload, f"{prefix}.payloads[{payload_idx}]", kind="file")
            if isinstance(payload, str) and payload.endswith("input/payloads/answer_template.json"):
                has_answer_template = True
            if payload_path is not None and payload_path.name == "answer_template.json":
                has_answer_template = True

        if not has_answer_template:
            self.fail(f"{prefix}.payloads must declare input/payloads/answer_template.json")

    def check_eval(self, eval_data: Any, answer_path: Path | None, prefix: str) -> None:
        if not isinstance(eval_data, dict):
            self.fail(f"{prefix}.eval must be a mapping")
            return

        missing_eval = REQUIRED_EVAL_KEYS - set(eval_data)
        if missing_eval:
            self.fail(f"{prefix}.eval missing keys: {sorted(missing_eval)}")

        script_path = self.require_path(eval_data.get("script"), f"{prefix}.eval.script", kind="file")
        if script_path is not None and script_path.is_file() and not os.access(script_path, os.X_OK):
            self.fail(f"{prefix}.eval.script must be executable")

        eval_files = eval_data.get("files")
        if not isinstance(eval_files, list) or not eval_files:
            self.fail(f"{prefix}.eval.files must be a non-empty list")
        else:
            for file_idx, eval_file in enumerate(eval_files):
                self.require_path(eval_file, f"{prefix}.eval.files[{file_idx}]", kind="file")

        self.check_rubric(eval_data.get("rubric"), prefix)

        if (
            not self.skip_eval
            and script_path is not None
            and script_path.is_file()
            and answer_path is not None
            and answer_path.is_file()
        ):
            self.check_eval_on_answer(script_path, answer_path, prefix)

    def check_rubric(self, rubric: Any, prefix: str) -> None:
        if not isinstance(rubric, list) or not rubric:
            self.fail(f"{prefix}.eval.rubric must be a non-empty list")
            return

        if not 6 <= len(rubric) <= 10:
            self.fail(
                f"{prefix}.eval.rubric must contain 6-10 scoring points, "
                f"found {len(rubric)}"
            )

        for idx, item in enumerate(rubric):
            field = f"{prefix}.eval.rubric[{idx}]"
            if not isinstance(item, dict):
                self.fail(f"{field}: rubric item must be a mapping")
                continue
            if not isinstance(item.get("goal"), str) or not item["goal"].strip():
                self.fail(f"{field}.goal must be a non-empty string")
            weight = item.get("weight")
            if (
                not isinstance(weight, int)
                or isinstance(weight, bool)
                or weight not in {1, 2, 3}
            ):
                self.fail(f"{field}.weight must be an integer in {{1, 2, 3}}")

    def check_eval_on_answer(self, script_path: Path, answer_path: Path, prefix: str) -> None:
        self.run_eval_and_check(
            [str(script_path.resolve()), str(answer_path.resolve())],
            cwd=self.root,
            prefix=prefix,
            mode="explicit answer path",
        )

    def run_eval_and_check(self, command: list[str], *, cwd: Path, prefix: str, mode: str) -> None:
        try:
            result = subprocess.run(
                command,
                cwd=str(cwd),
                text=True,
                capture_output=True,
                timeout=self.timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            self.fail(f"{prefix}.eval {mode}: timed out after {self.timeout}s")
            return
        except Exception as exc:
            self.fail(f"{prefix}.eval {mode}: failed to run: {exc}")
            return

        if result.returncode != 0:
            output = summarize_output(result.stdout, result.stderr)
            self.fail(f"{prefix}.eval {mode}: failed: {output}")
            return

        try:
            data = json.loads(result.stdout)
        except Exception as exc:
            output = summarize_output(result.stdout, result.stderr)
            self.fail(f"{prefix}.eval {mode}: stdout is not JSON: {exc}; output={output}")
            return

        if not is_full_score(data):
            self.fail(f"{prefix}.eval {mode}: standard answer must receive full score")

    def check_parseable_files(self) -> None:
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or path.name == ".DS_Store":
                continue
            if path.suffix == ".json":
                try:
                    json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    self.fail(f"JSON parse failed: {path.relative_to(self.root)}: {exc}")
            elif path.suffix in {".yaml", ".yml"}:
                try:
                    yaml.safe_load(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    self.fail(f"YAML parse failed: {path.relative_to(self.root)}: {exc}")

    def check_cjk_placement(self) -> None:
        text_suffixes = {".json", ".md", ".py", ".sh", ".txt", ".yaml", ".yml"}
        for path in sorted(self.root.rglob("*")):
            if not path.is_file() or path.name == ".DS_Store":
                continue
            if path.suffix not in text_suffixes:
                continue
            if path.match("**/notes/notes.md"):
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if has_cjk(text):
                self.fail(f"Chinese text found outside notes/notes.md: {path.relative_to(self.root)}")

    def run(self) -> dict[str, Any]:
        data = self.load_task_group_yaml()
        if data is not None:
            self.check_env(data)
            self.check_task_list(data, "train_tasks")
            self.check_task_list(data, "test_tasks")
        self.check_parseable_files()
        self.check_cjk_placement()

        passed = not self.errors
        detail = "" if passed else "\n".join(f"- {error}" for error in self.errors)
        return {
            "task_group_id": self.task_group_id,
            "task_group_path": str(self.root),
            "script_check": {
                "pass": passed,
                "detail": detail,
            },
        }


def has_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def is_number(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float))


def is_full_score(data: Any) -> bool:
    if not isinstance(data, dict):
        return False

    if data.get("passed") is True:
        return True

    score_pairs = [
        ("score", "max_score"),
        ("raw_score", "raw_max_score"),
        ("raw_score", "max_raw_score"),
        ("earned_score", "max_score"),
        ("earned_weight", "total_weight"),
        ("earned", "total"),
    ]
    for earned_key, total_key in score_pairs:
        earned = data.get(earned_key)
        total = data.get(total_key)
        if is_number(earned) and is_number(total) and float(total) > 0:
            if abs(float(earned) - float(total)) <= 1e-6:
                return True

    for key in ("normalized_score", "score", "total_score"):
        value = data.get(key)
        if is_number(value) and abs(float(value) - 1.0) <= 1e-6:
            return True

    for key in ("points", "scoring_points", "details", "checks"):
        value = data.get(key)
        if isinstance(value, list) and value:
            if all(
                isinstance(item, dict) and (item.get("passed") is True or item.get("pass") is True) for item in value
            ):
                return True
        elif isinstance(value, dict) and value:
            if all(item is True for item in value.values()):
                return True

    return False


def summarize_output(stdout: str, stderr: str) -> str:
    output = "\n".join(part for part in [stdout, stderr] if part)
    output = output.strip().replace("\n", " | ")
    if len(output) > 800:
        output = output[:800] + "..."
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Check task_group structural validity for quality review.")
    parser.add_argument("task_group_dir", help="Path to task_group/<task_group_id>/")
    parser.add_argument("--skip-eval", action="store_true", help="Skip running evaluators on standard answers.")
    parser.add_argument("--timeout", type=int, default=30, help="Per-eval timeout in seconds. Default: 30.")
    args = parser.parse_args()

    checker = Checker(Path(args.task_group_dir), skip_eval=args.skip_eval, timeout=args.timeout)
    check_result = checker.run()

    print(yaml.safe_dump(check_result, allow_unicode=True, sort_keys=False).strip())
    return 0 if check_result["script_check"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
