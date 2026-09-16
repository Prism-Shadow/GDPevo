#!/usr/bin/env python3
"""Validate a Crescent Finance Ops output JSON against its answer template.

Usage: python3 scripts/validate_template.py <output.json> <answer_template.json>
"""

import json, sys

def fail(msg):
    print(f"FAIL: {msg}")
    return False

def ok(msg):
    print(f"  OK: {msg}")
    return True

def main():
    if len(sys.argv) != 3:
        print("Usage: validate_template.py <output.json> <answer_template.json>")
        sys.exit(1)

    with open(sys.argv[1]) as f:
        output = json.load(f)
    with open(sys.argv[2]) as f:
        template = json.load(f)

    all_ok = True
    required_keys = template.get("required_top_level_keys", [])
    field_types = template.get("field_types", {})
    desc = template.get("description", "")

    print("Top-level keys:")
    for key in required_keys:
        if key not in output:
            all_ok = fail(f"Missing required key: {key}")
        else:
            ok(f"Present: {key}")

    extra_keys = set(output.keys()) - set(required_keys)
    for key in extra_keys:
        all_ok = fail(f"Extra key not in template: {key}")

    print("Field type checks:")
    def check_type(val, expected, path=""):
        nonlocal all_ok
        if isinstance(expected, dict):
            if not isinstance(val, dict):
                all_ok = fail(f"{path}: expected object, got {type(val).__name__}")
                return
            for k, v in expected.items():
                if k not in val:
                    all_ok = fail(f"{path}.{k}: missing field")
                else:
                    check_type(val[k], v, f"{path}.{k}")
        elif isinstance(expected, list):
            if not isinstance(val, list):
                all_ok = fail(f"{path}: expected list, got {type(val).__name__}")
                return
            if len(expected) > 0 and len(val) > 0:
                check_type(val[0], expected[0], f"{path}[0]")
        elif isinstance(expected, str):
            type_map = {
                "string": str,
                "integer": int,
                "currency": (int, float),
                "decimal percent": (int, float),
                "bool": bool,
            }
            if expected.startswith("enum:"):
                allowed = [s.strip() for s in expected[5:].split(",")]
                if val not in allowed:
                    all_ok = fail(f"{path}: value '{val}' not in enum {allowed}")
                else:
                    ok(f"{path}: {val} (valid enum)")
                return
            if expected.startswith("list of ") or expected.startswith("ordered list of "):
                if not isinstance(val, list):
                    all_ok = fail(f"{path}: expected list, got {type(val).__name__}")
                else:
                    ok(f"{path}: list of {len(val)} items")
                return
            if expected.startswith("sorted list using enum"):
                if not isinstance(val, list):
                    all_ok = fail(f"{path}: expected list")
                else:
                    ok(f"{path}: sorted list of {len(val)} items")
                return
            if expected.startswith("object mapping"):
                if not isinstance(val, dict):
                    all_ok = fail(f"{path}: expected object")
                else:
                    ok(f"{path}: object with keys {list(val.keys())}")
                return
            if expected.startswith("ascending list"):
                if not isinstance(val, list):
                    all_ok = fail(f"{path}: expected list")
                else:
                    ok(f"{path}: ascending list of {len(val)} items")
                return
            if expected in type_map:
                expected_type = type_map[expected]
                if not isinstance(val, expected_type):
                    all_ok = fail(f"{path}: expected {expected}, got {type(val).__name__}")
                else:
                    ok(f"{path}: {val} (type matches {expected})")
            else:
                ok(f"{path}: {val} (untyped but present)")

    for key, expected in field_types.items():
        if key in output:
            check_type(output[key], expected, key)

    print("Rounding checks:")
    def scan_currency(obj, path=""):
        nonlocal all_ok
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                if isinstance(v, float):
                    s = f"{v:.10f}"
                    if "." in s:
                        decimals = len(s.split(".")[1].rstrip("0"))
                        if decimals > 3 and abs(v - round(v, 2)) > 0.001:
                            all_ok = fail(f"{new_path}: {v} has >2 decimal places")
                scan_currency(v, new_path)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                scan_currency(item, f"{path}[{i}]")

    scan_currency(output)

    if all_ok:
        print("ALL CHECKS PASSED")
    else:
        print("SOME CHECKS FAILED")
    return 0 if all_ok else 1

if __name__ == "__main__":
    sys.exit(main())
