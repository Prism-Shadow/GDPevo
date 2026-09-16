#!/usr/bin/env python3
"""Smoke-test a Cedar Ridge answer JSON against the staged answer template."""

import argparse
import json
import sys


TEMPLATE_META_KEYS = {
    "description",
    "type",
    "top_level_type",
    "required_top_level_keys",
    "fields",
    "field_definitions",
    "normalization_notes",
}


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def top_level_required(template):
    if isinstance(template.get("required_top_level_keys"), list):
        return list(template["required_top_level_keys"])
    if isinstance(template.get("top_level"), dict):
        return list(template["top_level"].keys())
    return [
        key for key, value in template.items()
        if key not in TEMPLATE_META_KEYS and isinstance(value, dict)
    ]


def top_level_specs(template):
    specs = {}
    if isinstance(template.get("top_level"), dict):
        specs.update(template["top_level"])
    if isinstance(template.get("fields"), dict):
        specs.update(template["fields"])
    if isinstance(template.get("field_definitions"), dict):
        specs.update(template["field_definitions"])
    for key, value in template.items():
        if key not in TEMPLATE_META_KEYS and isinstance(value, dict):
            specs.setdefault(key, value)
    return specs


def constant_for(spec):
    if not isinstance(spec, dict):
        return False, None
    for key in ("required_value", "expected_value", "constant"):
        if key in spec:
            return True, spec[key]
    return False, None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", help="Path to input/payloads/answer_template.json")
    parser.add_argument("answer", help="Path to proposed answer JSON")
    args = parser.parse_args()

    errors = []
    template = load_json(args.template)
    answer = load_json(args.answer)
    if not isinstance(answer, dict):
        errors.append("answer top level must be a JSON object")
    else:
        required = top_level_required(template)
        missing = [key for key in required if key not in answer]
        if missing:
            errors.append("missing top-level keys: " + ", ".join(missing))

        specs = top_level_specs(template)
        for key, spec in specs.items():
            has_constant, expected = constant_for(spec)
            if has_constant and answer.get(key) != expected:
                errors.append(f"{key} expected {expected!r}, got {answer.get(key)!r}")

    if errors:
        for error in errors:
            print(f"[ERROR] {error}", file=sys.stderr)
        sys.exit(1)

    print("JSON shape smoke test passed")


if __name__ == "__main__":
    main()
