#!/usr/bin/env python3
"""Validate a candidate answer against a JSON-Schema answer template.

Dependency-free structural validator covering the subset of draft 2020-12 used by
the portfolio-env answer templates: required, type, const, enum, additionalProperties,
minItems/maxItems, minimum/maximum, and pattern. If the `jsonschema` package is
installed, it is used instead for full coverage.

Usage:
    python3 validate_answer.py <answer.json> <answer_template.json>
Exit code 0 = valid; 1 = violations found; 2 = usage/IO error.
"""
import json
import re
import sys


def load(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def fmt_path(path):
    return "$" + "".join(f"[{p!r}]" if isinstance(p, int) else f".{p}" for p in path)


def check(instance, schema, path, errors):
    if not isinstance(schema, dict):
        return

    # type
    t = schema.get("type")
    if t is not None:
        types = t if isinstance(t, list) else [t]
        py_to_json = {
            "object": dict, "array": list, "string": str,
            "integer": int, "number": (int, float), "boolean": bool, "null": type(None),
        }
        ok = False
        for tt in types:
            py = py_to_json.get(tt)
            if py is None:
                continue
            if tt == "integer" and isinstance(instance, bool):
                continue
            if tt == "number" and isinstance(instance, bool):
                continue
            if isinstance(instance, py):
                ok = True
                break
        if not ok:
            errors.append(f"{fmt_path(path)}: expected type {t}, got {type(instance).__name__}")
            return

    # const
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{fmt_path(path)}: expected const {schema['const']!r}, got {instance!r}")

    # enum
    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{fmt_path(path)}: value {instance!r} not in enum {schema['enum']}")

    # numeric bounds
    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{fmt_path(path)}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{fmt_path(path)}: {instance} > maximum {schema['maximum']}")

    # string pattern
    if isinstance(instance, str) and "pattern" in schema:
        if not re.search(schema["pattern"], instance):
            errors.append(f"{fmt_path(path)}: {instance!r} does not match pattern {schema['pattern']!r}")

    # array
    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{fmt_path(path)}: {len(instance)} items < minItems {schema['minItems']}")
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append(f"{fmt_path(path)}: {len(instance)} items > maxItems {schema['maxItems']}")
        items = schema.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(instance):
                check(item, items, path + (i,), errors)

    # object
    if isinstance(instance, dict):
        required = schema.get("required", [])
        for r in required:
            if r not in instance:
                errors.append(f"{fmt_path(path)}: missing required property {r!r}")
        props = schema.get("properties", {})
        addl = schema.get("additionalProperties")
        for k, v in instance.items():
            if k in props:
                check(v, props[k], path + (k,), errors)
            elif addl is False:
                errors.append(f"{fmt_path(path)}: additional property {k!r} not allowed")
            elif isinstance(addl, dict):
                check(v, addl, path + (k,), errors)


def main():
    if len(sys.argv) != 3:
        print("usage: validate_answer.py <answer.json> <answer_template.json>", file=sys.stderr)
        return 2
    try:
        answer = load(sys.argv[1])
        schema = load(sys.argv[2])
    except (OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    # Prefer jsonschema for full draft-2020-12 coverage if available.
    try:
        import jsonschema  # type: ignore
        from jsonschema import Draft202012Validator
        validator = Draft202012Validator(schema)
        errs = sorted(validator.iter_errors(answer), key=lambda e: list(e.path))
        if not errs:
            print("OK: answer validates against template (jsonschema).")
            return 0
        for e in errs:
            loc = "$" + "".join(f"[{p}]" if isinstance(p, int) else f".{p}" for p in e.path)
            print(f"VIOLATION at {loc}: {e.message}", file=sys.stderr)
        return 1
    except ImportError:
        pass

    errors = []
    check(answer, schema, (), errors)
    if not errors:
        print("OK: answer validates against template (built-in checks).")
        return 0
    for e in errors:
        print(f"VIOLATION: {e}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
