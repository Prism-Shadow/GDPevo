#!/usr/bin/env python3
"""Lightweight top-level shape check for an EHR normalized JSON answer."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def required_top_level(template: dict[str, Any]) -> list[str]:
    for key in ("top_level_required_keys", "required_top_level_keys"):
        value = template.get(key)
        if isinstance(value, list):
            return [str(item) for item in value]
    schema = template.get("schema")
    if isinstance(schema, dict):
        return list(schema.keys())
    return []


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("usage: check_json_shape.py ANSWER_JSON ANSWER_TEMPLATE_JSON", file=sys.stderr)
        return 2

    answer = load_json(argv[1])
    template = load_json(argv[2])
    if not isinstance(answer, dict):
        print("FAIL: answer is not a JSON object")
        return 1
    if not isinstance(template, dict):
        print("FAIL: template is not a JSON object")
        return 1

    required = required_top_level(template)
    missing = [key for key in required if key not in answer]
    extra = [key for key in answer if required and key not in required]

    if missing:
        print("FAIL: missing top-level keys: " + ", ".join(missing))
        return 1
    print("PASS: answer is a JSON object and required top-level keys are present")
    if extra:
        print("NOTE: extra top-level keys not listed by template: " + ", ".join(extra))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
