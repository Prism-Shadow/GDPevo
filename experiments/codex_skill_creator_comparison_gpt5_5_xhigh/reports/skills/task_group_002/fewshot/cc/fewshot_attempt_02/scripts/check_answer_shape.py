#!/usr/bin/env python3
"""Compare a candidate answer JSON shape against a task answer template."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def compare_shape(template: Any, answer: Any, path: str = "$") -> list[str]:
    errors: list[str] = []

    if isinstance(template, dict):
        if not isinstance(answer, dict):
            return [f"{path}: expected object, got {type(answer).__name__}"]
        template_keys = set(template)
        answer_keys = set(answer)
        for key in sorted(template_keys - answer_keys):
            errors.append(f"{path}: missing key {key!r}")
        for key in sorted(answer_keys - template_keys):
            errors.append(f"{path}: unexpected key {key!r}")
        for key in sorted(template_keys & answer_keys):
            errors.extend(compare_shape(template[key], answer[key], f"{path}.{key}"))
        return errors

    if isinstance(template, list):
        if not isinstance(answer, list):
            return [f"{path}: expected array, got {type(answer).__name__}"]
        if template and answer:
            exemplar = template[0]
            for index, item in enumerate(answer):
                errors.extend(compare_shape(exemplar, item, f"{path}[{index}]"))
        return errors

    return errors


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: check_answer_shape.py TEMPLATE_JSON ANSWER_JSON", file=sys.stderr)
        return 2

    template = load_json(argv[1])
    answer = load_json(argv[2])
    errors = compare_shape(template, answer)
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("shape ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
