#!/usr/bin/env python3
"""Pre-flight sanity check for an Asteria Fleet DQ audit answer.

Usage:
    python3 validate_answer.py <answer.json> <answer_template.json>

Confirms `answer.json` is a single JSON object (no trailing prose / fences) and
structurally matches `answer_template.json`:

- JSON-Schema-style templates: required keys, no extra keys where
  `additionalProperties` is false, enum membership, regex patterns,
  minItems/maxItems, uniqueItems, and numeric bounds.
- Field-contract templates: required top-level keys, declared list lengths,
  item required keys, and enum membership (both real `enum` arrays and
  `enum: A | B | C` description strings).

This is a SANITY CHECK, not a full validator. It does NOT verify sort order or
numeric rounding — re-read answer_template.json and verify those manually.
Informational notes never cause a non-zero exit; only real violations do.
"""
import json
import re
import sys


def load(path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_enum_from_desc(desc):
    """Parse 'enum: A | B | C' from a field-contract description string."""
    if not isinstance(desc, str):
        return None
    m = re.search(r"enum:\s*([^\n;]+)$", desc)
    if not m:
        return None
    vals = [v.strip() for v in m.group(1).split("|")]
    return vals if all(vals) else None


def check_schema(value, schema, path, violations):
    """Recursively check `value` against a JSON-Schema-ish `schema`."""
    if not isinstance(schema, dict):
        return
    t = schema.get("type")
    if t == "object" and not isinstance(value, dict):
        violations.append(f"{path}: expected object")
    elif t == "array" and not isinstance(value, list):
        violations.append(f"{path}: expected array")
    elif t == "integer" and not (isinstance(value, int) and not isinstance(value, bool)):
        violations.append(f"{path}: expected integer, got {value!r}")
    elif t == "string" and not isinstance(value, str):
        violations.append(f"{path}: expected string, got {value!r}")
    if "enum" in schema and value not in schema["enum"]:
        violations.append(f"{path}: value {value!r} not in enum {schema['enum']}")
    if "pattern" in schema and isinstance(value, str) and not re.match(schema["pattern"], value):
        violations.append(f"{path}: {value!r} does not match pattern {schema['pattern']}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            violations.append(f"{path}: {value} < minimum {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            violations.append(f"{path}: {value} > maximum {schema['maximum']}")
    if isinstance(value, dict) and isinstance(schema.get("properties"), dict):
        props = schema["properties"]
        for req in schema.get("required", []):
            if req not in value:
                violations.append(f"{path}: missing required key {req!r}")
        if schema.get("additionalProperties") is False:
            for k in value:
                if k not in props:
                    violations.append(f"{path}: extra key {k!r} (additionalProperties is false)")
        for k, sub in props.items():
            if k in value:
                check_schema(value[k], sub, f"{path}.{k}", violations)
    if isinstance(value, list) and "items" in schema:
        if "minItems" in schema and len(value) < schema["minItems"]:
            violations.append(f"{path}: {len(value)} items < minItems {schema['minItems']}")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            violations.append(f"{path}: {len(value)} items > maxItems {schema['maxItems']}")
        if schema.get("uniqueItems"):
            seen = set()
            for item in value:
                key = json.dumps(item, sort_keys=True)
                if key in seen:
                    violations.append(f"{path}: duplicate item but uniqueItems is true")
                    break
                seen.add(key)
        for i, item in enumerate(value):
            check_schema(item, schema["items"], f"{path}[{i}]", violations)


def check_field_contract(answer, template, violations, notes):
    """Best-effort structural check for the field-contract template style."""
    top = template.get("required_top_level_keys", [])
    for k in top:
        if k not in answer:
            violations.append(f"<root>: missing required top-level key {k!r}")
    if template.get("additional_top_level_keys_allowed") is False:
        for k in answer:
            if k not in top:
                violations.append(f"<root>: extra top-level key {k!r}")
    fc = template.get("field_contract", {})
    for key, spec in fc.items():
        if key not in answer:
            continue
        val = answer[key]
        # Object-typed field: check required keys + real enums.
        if isinstance(val, dict):
            for rk in spec.get("required_keys", []):
                if rk not in val:
                    violations.append(f"{key}: missing required key {rk!r}")
            for fname, fspec in spec.get("fields", {}).items():
                if isinstance(fspec, dict) and "enum" in fspec and fname in val:
                    if val[fname] not in fspec["enum"]:
                        violations.append(f"{key}.{fname}: {val[fname]!r} not in enum {fspec['enum']}")
        # List-typed field: check length, item required keys, enums, allowed values.
        if isinstance(val, list):
            if "length" in spec and len(val) != spec["length"]:
                violations.append(f"{key}: {len(val)} items, expected length {spec['length']}")
            item_req = spec.get("item_required_keys", [])
            item_fields = spec.get("item_fields", {})
            allowed = spec.get("allowed_values")
            for i, item in enumerate(val):
                if isinstance(item, dict):
                    for rk in item_req:
                        if rk not in item:
                            violations.append(f"{key}[{i}]: missing required key {rk!r}")
                    for fname, fspec in item_fields.items():
                        if fname not in item:
                            continue
                        if isinstance(fspec, dict) and "enum" in fspec:
                            if item[fname] not in fspec["enum"]:
                                violations.append(f"{key}[{i}].{fname}: {item[fname]!r} not in enum {fspec['enum']}")
                        else:
                            enum_vals = parse_enum_from_desc(fspec)
                            if enum_vals is not None and item[fname] not in enum_vals:
                                violations.append(f"{key}[{i}].{fname}: {item[fname]!r} not in enum {enum_vals}")
                elif isinstance(item, str) and allowed is not None:
                    if item not in allowed:
                        violations.append(f"{key}[{i}]: {item!r} not in allowed_values")
            if spec.get("uniqueness"):
                seen = set()
                for item in val:
                    s = json.dumps(item, sort_keys=True)
                    if s in seen:
                        violations.append(f"{key}: duplicate items but uniqueness required")
                        break
                    seen.add(s)
    notes.append("field-contract template: sort order and numeric precision not auto-checked; verify manually.")


def main(argv):
    if len(argv) != 3:
        print("usage: validate_answer.py <answer.json> <answer_template.json>", file=sys.stderr)
        return 2
    answer_path, template_path = argv[1], argv[2]
    with open(answer_path, "r", encoding="utf-8") as f:
        raw = f.read()
    violations = []
    notes = []
    try:
        answer = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"FAIL: answer is not valid JSON ({e})")
        return 1
    if not isinstance(answer, dict):
        print("FAIL: answer is not a single JSON object")
        return 1
    stripped = raw.strip()
    if stripped.startswith("```"):
        violations.append("answer file appears to start with a Markdown fence")
    _, idx = json.JSONDecoder().raw_decode(stripped)
    tail = stripped[idx:].strip()
    if tail:
        violations.append(f"non-JSON trailing content after object: {tail[:80]!r}")
    template = load(template_path)
    if isinstance(template, dict) and "field_contract" in template:
        check_field_contract(answer, template, violations, notes)
    elif isinstance(template, dict) and ("properties" in template or "required" in template):
        check_schema(answer, template, "<root>", violations)
    else:
        notes.append("template format not recognized; skipping structural checks")
    if violations:
        print("FAIL -- fix the following:")
        for m in violations:
            print(f"  - {m}")
        for m in notes:
            print(f"  note: {m}")
        return 1
    print("PASS -- structural checks OK. Still verify ordering and numeric precision manually.")
    for m in notes:
        print(f"  note: {m}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
