#!/usr/bin/env python3
"""Check that an answer is strict JSON and matches a template at top level."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_json(path: Path):
    text = path.read_text(encoding="utf-8")
    return json.loads(text), text


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate strict JSON answer shape.")
    parser.add_argument("template", help="Path to input/payloads/answer_template.json")
    parser.add_argument("answer", help="Path to candidate answer JSON")
    args = parser.parse_args()

    try:
        template, _ = load_json(Path(args.template))
        answer, raw = load_json(Path(args.answer))
    except json.JSONDecodeError as exc:
        print(f"JSON parse error: {exc}", file=sys.stderr)
        return 2

    if not isinstance(answer, dict):
        print("Answer must be one JSON object.", file=sys.stderr)
        return 2

    if raw.lstrip().startswith("```") or raw.rstrip().endswith("```"):
        print("Answer must not include Markdown fences.", file=sys.stderr)
        return 2

    if isinstance(template, dict):
        exact = True
        if isinstance(template.get("required_top_level_fields"), dict):
            expected_keys = list(template["required_top_level_fields"])
            exact = False
        elif isinstance(template.get("required_output_shape"), dict):
            expected_keys = list(template["required_output_shape"])
            exact = False
        else:
            expected_keys = list(template)

        missing = [key for key in expected_keys if key not in answer]
        extra = [key for key in answer if exact and key not in expected_keys]
        if missing:
            print("Missing top-level keys: " + ", ".join(missing), file=sys.stderr)
        if extra:
            print("Extra top-level keys: " + ", ".join(extra), file=sys.stderr)
        if missing or extra:
            return 1

    print("JSON parses and top-level keys match the template.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
