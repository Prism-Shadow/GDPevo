#!/usr/bin/env python3
"""Lightweight JSON and top-level template shape checker."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


PLACEHOLDER_RE = re.compile(
    r"\b(one of:|stable .* id|stable .* name|integer or null|number or null|YYYY-MM-DD| \| )",
    re.IGNORECASE,
)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def expected_top_level(template: Any) -> set[str]:
    if not isinstance(template, dict):
        return set()
    if isinstance(template.get("required_output_shape"), dict):
        return set(template["required_output_shape"].keys())
    if isinstance(template.get("required_top_level_fields"), dict):
        return set(template["required_top_level_fields"].keys())
    return set(template.keys())


def walk_placeholders(value: Any, path: str = "$") -> list[str]:
    found: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            found.extend(walk_placeholders(child, f"{path}.{key}"))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(walk_placeholders(child, f"{path}[{index}]"))
    elif isinstance(value, str) and PLACEHOLDER_RE.search(value):
        found.append(path)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", type=Path)
    parser.add_argument("answer", type=Path)
    args = parser.parse_args()

    try:
        template = load_json(args.template)
        answer = load_json(args.answer)
    except json.JSONDecodeError as exc:
        print(f"Invalid JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(answer, dict):
        print("Answer must be a JSON object", file=sys.stderr)
        return 1

    expected = expected_top_level(template)
    missing = sorted(expected - set(answer.keys()))
    extra = sorted(set(answer.keys()) - expected) if expected else []
    unresolved = walk_placeholders(answer)

    if missing:
        print("Missing top-level keys: " + ", ".join(missing), file=sys.stderr)
    if extra and "required_output_shape" in template:
        print("Unexpected top-level keys: " + ", ".join(extra), file=sys.stderr)
    if unresolved:
        print("Possible unresolved placeholder values at: " + ", ".join(unresolved), file=sys.stderr)

    if missing or unresolved:
        return 1

    print("JSON parsed and required top-level keys are present")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
