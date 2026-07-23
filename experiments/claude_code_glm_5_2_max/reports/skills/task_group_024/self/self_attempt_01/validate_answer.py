#!/usr/bin/env python3
"""Validate an answer JSON against an answer_template.json (JSON Schema draft 2020-12).

Usage:
    python3 validate_answer.py <template.json> <answer.json>

Exits 0 if the answer matches the template, 1 otherwise, printing each violation.

Tries the `jsonschema` library first. If it is unavailable, falls back to a focused
manual check covering the constraints these templates use: required,
additionalProperties, const, enum, type, minItems, maxItems, pattern, minimum.

Generic and value-free: takes the template and answer as arguments, holds no
task-specific data.
"""
import json
import re
import sys


def main():
    if len(sys.argv) != 3:
        print("usage: validate_answer.py <template.json> <answer.json>", file=sys.stderr)
        return 2
    template_path, answer_path = sys.argv[1], sys.argv[2]
    with open(template_path) as fh:
        schema = json.load(fh)
    with open(answer_path) as fh:
        answer = json.load(fh)

    errors = []
    try:
        import jsonschema  # type: ignore
        validator = jsonschema.Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(answer), key=lambda e: list(e.path)):
            loc = ".".join(str(p) for p in err.path) or "<root>"
            errors.append(f"{loc}: {err.message}")
    except ImportError:
        _manual(schema, answer, "<root>", errors)

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        print(f"\n{len(errors)} violation(s): answer does not match template.",
              file=sys.stderr)
        return 1
    print("OK: answer matches template.")
    return 0


def _manual(schema, value, loc, errors):
    if not isinstance(schema, dict):
        return
    t = schema.get("type")
    if t == "object" and not isinstance(value, dict):
        errors.append(f"{loc}: expected object, got {type(value).__name__}")
        return
    if t == "array" and not isinstance(value, list):
        errors.append(f"{loc}: expected array, got {type(value).__name__}")
        return
    if t == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
        errors.append(f"{loc}: expected integer, got {value!r}")
        return
    if t == "number" and not isinstance(value, (int, float)):
        errors.append(f"{loc}: expected number, got {value!r}")
        return
    if t == "string" and not isinstance(value, str):
        errors.append(f"{loc}: expected string, got {value!r}")
        return
    if "const" in schema and value != schema["const"]:
        errors.append(f"{loc}: expected const {schema['const']!r}, got {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{loc}: {value!r} not in enum {schema['enum']}")
    if "pattern" in schema and isinstance(value, str) \
            and not re.match(schema["pattern"], value):
        errors.append(f"{loc}: {value!r} does not match pattern {schema['pattern']!r}")
    if "minimum" in schema and isinstance(value, (int, float)) and value < schema["minimum"]:
        errors.append(f"{loc}: {value} < minimum {schema['minimum']}")

    if isinstance(value, dict):
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}))
            for k in value:
                if k not in allowed:
                    errors.append(f"{loc}: additional property {k!r} not allowed")
        for r in schema.get("required", []):
            if r not in value:
                errors.append(f"{loc}: missing required property {r!r}")
        for k, sub in schema.get("properties", {}).items():
            if k in value:
                _manual(sub, value[k], f"{loc}.{k}", errors)

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errors.append(f"{loc}: {len(value)} items < minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{loc}: {len(value)} items > maxItems {schema['maxItems']}")
        for i, item in enumerate(value):
            _manual(schema.get("items", {}), item, f"{loc}[{i}]", errors)


if __name__ == "__main__":
    sys.exit(main())
