#!/usr/bin/env python3
"""Light structural checker for workbench JSON answers and loose templates."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


META_KEYS = {
    "allowed_enums",
    "instructions",
    "issue_object_fields",
    "possible_issue_ids",
    "required_output_shape",
    "required_top_level_fields",
    "schema_name",
    "schema_version",
    "summary_metrics_fields",
    "units",
    "version",
}

OPTIONAL_VARIANT_OBJECTS = {"draft_metric", "policy_metric", "delta"}


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def expected_answer_shape(template: Any) -> Any:
    if isinstance(template, dict):
        if isinstance(template.get("required_output_shape"), dict):
            return template["required_output_shape"]
        if isinstance(template.get("required_top_level_fields"), dict):
            shape: dict[str, Any] = {}
            for key, spec in template["required_top_level_fields"].items():
                if key == "issue_register" and isinstance(template.get("issue_object_fields"), dict):
                    shape[key] = [{field: descriptor_shape(value) for field, value in template["issue_object_fields"].items()}]
                elif key == "summary_metrics" and isinstance(template.get("summary_metrics_fields"), dict):
                    shape[key] = {field: descriptor_shape(value) for field, value in template["summary_metrics_fields"].items()}
                else:
                    shape[key] = descriptor_shape(spec)
            return shape
        answer_keys = [key for key in template if key not in META_KEYS]
        if answer_keys:
            return {key: template[key] for key in answer_keys}
    return template


def descriptor_shape(spec: Any) -> Any:
    if not isinstance(spec, str):
        return spec
    lowered = spec.lower()
    if "or null" in lowered:
        return None
    if "array" in lowered:
        return []
    if "object" in lowered:
        return {}
    if "boolean" in lowered:
        return True
    if "integer" in lowered or "number" in lowered or "percent" in lowered or "month" in lowered:
        return 0
    return "string"


def check_shape(expected: Any, actual: Any, path: str, issues: list[str]) -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            issues.append(f"{path}: expected object, got {type(actual).__name__}")
            return
        object_name = path.rsplit(".", 1)[-1].split("[", 1)[0]
        for key, child in expected.items():
            if key not in actual:
                if object_name not in OPTIONAL_VARIANT_OBJECTS:
                    issues.append(f"{path}.{key}: missing key")
                continue
            check_shape(child, actual[key], f"{path}.{key}", issues)
        return

    if isinstance(expected, list):
        if not isinstance(actual, list):
            issues.append(f"{path}: expected array, got {type(actual).__name__}")
            return
        if expected and actual:
            for index, item in enumerate(actual):
                check_shape(expected[0], item, f"{path}[{index}]", issues)
        return

    if isinstance(expected, bool) and not isinstance(actual, bool):
        issues.append(f"{path}: expected boolean-like value")
    elif isinstance(expected, (int, float)) and not isinstance(actual, (int, float)):
        issues.append(f"{path}: expected numeric value")
    elif isinstance(expected, str) and expected not in {"string", "YYYY-MM-DD"}:
        # Most string placeholders describe allowed values, so only require that
        # filled values are scalars or null; enum correctness needs human review.
        if isinstance(actual, (dict, list)):
            issues.append(f"{path}: expected scalar placeholder-compatible value")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("template", help="Path to input/payloads/answer_template.json")
    parser.add_argument("answer", help="Path to drafted answer JSON")
    args = parser.parse_args()

    template = load_json(args.template)
    answer = load_json(args.answer)
    expected = expected_answer_shape(template)

    issues: list[str] = []
    check_shape(expected, answer, "$", issues)

    if issues:
        print("Structural issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("JSON parses and matches the expected container/key shape.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
