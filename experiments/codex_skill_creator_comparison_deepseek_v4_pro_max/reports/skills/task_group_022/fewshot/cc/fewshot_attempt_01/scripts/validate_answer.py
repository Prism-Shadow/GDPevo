#!/usr/bin/env python3
"""Validate answer.json against an answer_template.json (JSON Schema subset).

Usage:
    python validate_answer.py answer.json answer_template.json
"""

import json
import sys
import re
import os


def log_issue(msg):
    print(f"  FAIL: {msg}")


def check_type(value, type_name):
    type_map = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }
    expected = type_map.get(type_name)
    if expected is None:
        return True
    if isinstance(expected, tuple):
        ok = isinstance(value, expected)
    else:
        ok = isinstance(value, expected)
    if not ok and type_name == "integer":
        ok = isinstance(value, int) and not isinstance(value, bool)
    return ok


def validate_value(value, schema, path="$"):
    issues = []
    t = schema.get("type")
    if t:
        if not check_type(value, t):
            issues.append(f"{path}: expected type {t}, got {type(value).__name__} (value={value!r})")
            return issues

    if t == "string":
        pat = schema.get("pattern")
        if pat and not re.search(pat, str(value)):
            issues.append(f"{path}: value {value!r} does not match pattern {pat}")

        enum_vals = schema.get("enum")
        if enum_vals and str(value) not in enum_vals:
            issues.append(f"{path}: value {value!r} not in enum {enum_vals}")

        if "minLength" in schema and len(str(value)) < schema["minLength"]:
            if schema["minLength"] > 0 and str(value).strip():
                issues.append(f"{path}: length {len(str(value))} < minLength {schema['minLength']}")

    if t == "integer" and isinstance(value, bool):
        issues.append(f"{path}: boolean {value} is not a valid integer")

    if (t == "integer" or t == "number") and "minimum" in schema and value < schema["minimum"]:
        issues.append(f"{path}: {value} < minimum {schema['minimum']}")

    if (t == "integer" or t == "number") and "maximum" in schema and value > schema["maximum"]:
        issues.append(f"{path}: {value} > maximum {schema['maximum']}")

    if t == "number" and "multipleOf" in schema:
        mo = schema["multipleOf"]
        remainder = abs(value / mo - round(value / mo))
        if remainder > 1e-9:
            issues.append(f"{path}: {value} is not a multiple of {mo}")

    if t == "array":
        arr = value
        if "minItems" in schema and len(arr) < schema["minItems"]:
            issues.append(f"{path}: array length {len(arr)} < minItems {schema['minItems']}")
        if "maxItems" in schema and len(arr) > schema["maxItems"]:
            issues.append(f"{path}: array length {len(arr)} > maxItems {schema['maxItems']}")
        if "uniqueItems" in schema and schema["uniqueItems"]:
            seen = set()
            for item in arr:
                key = json.dumps(item, sort_keys=True, default=str)
                if key in seen:
                    issues.append(f"{path}: duplicate item found in array")
                    break
                seen.add(key)
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(arr):
                issues.extend(validate_value(item, item_schema, f"{path}[{i}]"))

    if t == "object":
        obj = value
        if "required" in schema:
            for req in schema["required"]:
                if req not in obj:
                    issues.append(f"{path}: missing required field {req}")
        if "properties" in schema:
            for prop_name, prop_schema in schema["properties"].items():
                if prop_name in obj:
                    issues.extend(validate_value(obj[prop_name], prop_schema, f"{path}.{prop_name}"))
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            extra = set(obj.keys()) - allowed
            if extra:
                issues.append(f"{path}: extra fields not allowed: {extra}")

    return issues


def main():
    if len(sys.argv) != 3:
        print("Usage: python validate_answer.py answer.json answer_template.json")
        sys.exit(2)

    answer_path = sys.argv[1]
    template_path = sys.argv[2]

    if not os.path.exists(answer_path):
        print(f"ERROR: answer file not found: {answer_path}")
        sys.exit(1)
    if not os.path.exists(template_path):
        print(f"ERROR: template file not found: {template_path}")
        sys.exit(1)

    with open(answer_path) as f:
        answer = json.load(f)
    with open(template_path) as f:
        template = json.load(f)

    issues = validate_value(answer, template)

    if issues:
        print(f"Validation FAILED: {len(issues)} issue(s):")
        for issue in issues:
            print(f"  - {issue}")
        sys.exit(1)
    else:
        print("Validation PASSED")
        sys.exit(0)


if __name__ == "__main__":
    main()
