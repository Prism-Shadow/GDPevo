#!/usr/bin/env python3
"""Validate an Atlas answer.json against its answer_template.json schema.

Usage:
    validate_answer.py answer.json input/payloads/answer_template.json

Uses `jsonschema` if available for full validation; otherwise falls back to a
lightweight structural check (required keys, additionalProperties, enums,
array item counts/uniqueness, string patterns, multipleOf). The templates use
either `additionalProperties`/`minItems`/`maxItems`/`uniqueItems` (Draft-style)
or the snake_case aliases `additional_properties`/`min_items`/`max_items`/
`unique_items`; both are handled by the fallback.

Exit code 0 = valid, 1 = problems found, 2 = usage/IO error.
"""
import json
import re
import sys


def load(path):
    with open(path) as f:
        return json.load(f)


def alias(schema, *names, default=None):
    for n in names:
        if n in schema:
            return schema[n]
    return default


def check(instance, schema, path, errors):
    t = schema.get("type")
    if t == "object" and isinstance(instance, dict):
        props = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required key '{key}'")
        if alias(schema, "additionalProperties", "additional_properties", default=True) is False:
            for key in instance:
                if key not in props:
                    errors.append(f"{path}: unexpected key '{key}' (additionalProperties=false)")
        for key, subschema in props.items():
            if key in instance:
                check(instance[key], subschema, f"{path}.{key}", errors)
    elif t == "array" and isinstance(instance, list):
        mn = alias(schema, "minItems", "min_items")
        mx = alias(schema, "maxItems", "max_items")
        if mn is not None and len(instance) < mn:
            errors.append(f"{path}: array shorter than minItems {mn} (len {len(instance)})")
        if mx is not None and len(instance) > mx:
            errors.append(f"{path}: array longer than maxItems {mx} (len {len(instance)})")
        if alias(schema, "uniqueItems", "unique_items", default=False):
            seen = [json.dumps(x, sort_keys=True) for x in instance]
            if len(set(seen)) != len(seen):
                errors.append(f"{path}: array items not unique")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for i, item in enumerate(instance):
                check(item, item_schema, f"{path}[{i}]", errors)
    elif t == "string":
        if not isinstance(instance, str):
            errors.append(f"{path}: expected string, got {type(instance).__name__}")
        else:
            pat = schema.get("pattern")
            if pat and not re.match(pat, instance):
                errors.append(f"{path}: '{instance}' does not match pattern {pat}")
            enum = schema.get("enum")
            if enum and instance not in enum:
                errors.append(f"{path}: '{instance}' not in enum {enum}")
    elif t == "integer":
        if not isinstance(instance, int) or isinstance(instance, bool):
            errors.append(f"{path}: expected integer")
    elif t == "number":
        if not isinstance(instance, (int, float)) or isinstance(instance, bool):
            errors.append(f"{path}: expected number")
    # numeric bounds / multipleOf (apply to number & integer)
    if t in ("number", "integer") and isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append(f"{path}: {instance} < minimum {schema['minimum']}")
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append(f"{path}: {instance} > maximum {schema['maximum']}")
        mo = schema.get("multipleOf")
        if mo:
            q = round(instance / mo)
            if abs(q * mo - instance) > 1e-9:
                errors.append(f"{path}: {instance} not a multiple of {mo} (precision)")


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    answer = load(sys.argv[1])
    schema = load(sys.argv[2])

    try:
        import jsonschema  # type: ignore
        try:
            jsonschema.validate(answer, schema)
            print("VALID (jsonschema)")
            return 0
        except jsonschema.ValidationError as e:
            print("INVALID (jsonschema):")
            print(f"  {list(e.absolute_path)}: {e.message}")
            return 1
    except ImportError:
        errors = []
        check(answer, schema, "$", errors)
        if errors:
            print("INVALID (fallback checker):")
            for e in errors:
                print(f"  {e}")
            return 1
        print("VALID (fallback checker; install jsonschema for full validation)")
        return 0


if __name__ == "__main__":
    sys.exit(main())
