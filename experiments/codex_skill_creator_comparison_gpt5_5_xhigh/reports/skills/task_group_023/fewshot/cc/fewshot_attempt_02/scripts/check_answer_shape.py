#!/usr/bin/env python3
"""Basic JSON answer/template shape checks for PHO audit outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def top_keys_from_template(template: Any) -> list[str] | None:
    if isinstance(template, dict):
        direct = template.get("required_top_level_keys")
        if isinstance(direct, list):
            return [str(x) for x in direct]

        submission = template.get("submission")
        if isinstance(submission, dict) and isinstance(
            submission.get("required_top_level_keys"), list
        ):
            return [str(x) for x in submission["required_top_level_keys"]]

        required_output = template.get("required_output")
        if isinstance(required_output, dict):
            return list(required_output.keys())

        response = template.get("response")
        if isinstance(response, dict):
            return list(response.keys())

        fields = template.get("fields")
        if isinstance(fields, dict):
            return list(fields.keys())
    return None


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: check_answer_shape.py <answer_template.json> <answer.json>", file=sys.stderr)
        return 2

    template = load_json(argv[1])
    answer = load_json(argv[2])
    if not isinstance(answer, dict):
        print("answer must be a JSON object", file=sys.stderr)
        return 1

    required = top_keys_from_template(template)
    if required is None:
        print("warning: could not infer top-level keys from template")
        return 0

    answer_keys = list(answer.keys())
    missing = [key for key in required if key not in answer]
    extra = [key for key in answer_keys if key not in required]
    order_matches = answer_keys == required

    report = {
        "required_top_level_keys": required,
        "answer_top_level_keys": answer_keys,
        "missing": missing,
        "extra": extra,
        "order_matches": order_matches,
    }
    print(json.dumps(report, indent=2))

    return 1 if missing or extra or not order_matches else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
