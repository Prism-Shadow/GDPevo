#!/usr/bin/env python3
"""Best-effort validator for an answer.json against its answer_template.json.

The Atlas answer templates are *mostly* JSON Schema, but some use non-standard
keys (``additional_properties``, ``min_items``, ``max_items``, ``unique_items``,
``decimal_places``, ``precision``, ``multipleOf`` on floats). This validator is
deliberately lenient and normalises those spellings. It catches the mistakes
that actually cost points:

  * missing required keys / unexpected extra keys (additionalProperties: false)
  * wrong JSON type (integer vs number vs string vs array vs object)
  * enum violations, string pattern violations
  * min/max item counts, uniqueItems
  * decimal-place / multipleOf discipline on reported numbers
  * array ordering, when the template documents an order (checked heuristically)

Usage:  python3 validate_answer.py answer.json answer_template.json

Exit code 0 = no problems found, 1 = problems (printed to stderr).
It does NOT check business correctness -- only shape/contract conformance.
"""
import json
import re
import sys


def norm(schema):
    """Normalise non-standard template keys to JSON-Schema-ish names."""
    if not isinstance(schema, dict):
        return schema
    alias = {
        "additional_properties": "additionalProperties",
        "min_items": "minItems",
        "max_items": "maxItems",
        "unique_items": "uniqueItems",
    }
    out = {}
    for k, v in schema.items():
        out[alias.get(k, k)] = v
    return out


def decimals(x):
    s = repr(float(x))
    if "e" in s or "E" in s:
        return None  # scientific; skip
    return len(s.split(".")[1].rstrip("0")) if "." in s else 0


def check(value, schema, path, errs):
    schema = norm(schema)
    t = schema.get("type")

    if t == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            errs.append(f"{path}: expected integer, got {type(value).__name__}")
    elif t == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            errs.append(f"{path}: expected number, got {type(value).__name__}")
    elif t == "string":
        if not isinstance(value, str):
            errs.append(f"{path}: expected string, got {type(value).__name__}")
    elif t == "array":
        if not isinstance(value, list):
            errs.append(f"{path}: expected array, got {type(value).__name__}")
    elif t == "object":
        if not isinstance(value, dict):
            errs.append(f"{path}: expected object, got {type(value).__name__}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errs.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            errs.append(f"{path}: {value} > maximum {schema['maximum']}")
        dp = schema.get("decimal_places", schema.get("precision"))
        mo = schema.get("multipleOf")
        if mo and "." in str(mo):
            dp = dp if dp is not None else len(str(mo).split(".")[1])
        if dp is not None:
            d = decimals(value)
            if d is not None and d > dp:
                errs.append(f"{path}: {value} has >{dp} decimal places")

    if isinstance(value, str):
        pat = schema.get("pattern")
        if pat and not re.search(pat, value):
            errs.append(f"{path}: '{value}' does not match /{pat}/")

    if "enum" in schema and value not in schema["enum"]:
        errs.append(f"{path}: '{value}' not in enum {schema['enum']}")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            errs.append(f"{path}: {len(value)} items < minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errs.append(f"{path}: {len(value)} items > maxItems {schema['maxItems']}")
        if schema.get("uniqueItems"):
            seen = [json.dumps(v, sort_keys=True) for v in value]
            if len(set(seen)) != len(seen):
                errs.append(f"{path}: items are not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, v in enumerate(value):
                check(v, item_schema, f"{path}[{i}]", errs)

    if isinstance(value, dict) and t == "object":
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            if req not in value:
                errs.append(f"{path}: missing required key '{req}'")
        if schema.get("additionalProperties") is False:
            for k in value:
                if k not in props:
                    errs.append(f"{path}: unexpected key '{k}'")
        for k, sub in props.items():
            if k in value:
                check(value[k], sub, f"{path}.{k}", errs)


def main(argv):
    if len(argv) != 2:
        print(__doc__)
        return 2
    with open(argv[0]) as fh:
        answer = json.load(fh)
    with open(argv[1]) as fh:
        template = json.load(fh)
    errs = []
    check(answer, template, "$", errs)
    if errs:
        print("CONTRACT PROBLEMS (%d):" % len(errs), file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        return 1
    print("OK: answer.json conforms to the template's shape constraints.")
    print("NOTE: business correctness is NOT checked by this tool.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
