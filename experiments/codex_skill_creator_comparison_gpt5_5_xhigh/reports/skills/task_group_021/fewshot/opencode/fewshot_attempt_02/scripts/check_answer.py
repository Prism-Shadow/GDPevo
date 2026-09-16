#!/usr/bin/env python3
"""Validate an answer JSON against a task answer template."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def load_json(path: str):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def minimal_check(schema, value, path="$"):
    errors = []
    if isinstance(schema, dict):
        expected_type = schema.get("type")
        if expected_type == "object":
            if not isinstance(value, dict):
                return [f"{path}: expected object"]
            required = schema.get("required") or schema.get("required_top_level_keys") or []
            for key in required:
                if key not in value:
                    errors.append(f"{path}: missing required key {key}")
            if schema.get("additionalProperties") is False:
                allowed = set((schema.get("properties") or {}).keys())
                for key in value:
                    if key not in allowed:
                        errors.append(f"{path}: unexpected key {key}")
            for key, subschema in (schema.get("properties") or {}).items():
                if key in value:
                    errors.extend(minimal_check(subschema, value[key], f"{path}.{key}"))
        elif expected_type == "array":
            if not isinstance(value, list):
                return [f"{path}: expected array"]
            if "minItems" in schema and len(value) < schema["minItems"]:
                errors.append(f"{path}: expected at least {schema['minItems']} items")
            if "maxItems" in schema and len(value) > schema["maxItems"]:
                errors.append(f"{path}: expected at most {schema['maxItems']} items")
            if schema.get("uniqueItems"):
                seen = set()
                for item in value:
                    marker = json.dumps(item, sort_keys=True, ensure_ascii=False)
                    if marker in seen:
                        errors.append(f"{path}: duplicate item {marker}")
                    seen.add(marker)
            item_schema = schema.get("items")
            if item_schema:
                for index, item in enumerate(value):
                    errors.extend(minimal_check(item_schema, item, f"{path}[{index}]"))
        elif expected_type == "string":
            if not isinstance(value, str):
                errors.append(f"{path}: expected string")
        elif expected_type == "integer":
            if not isinstance(value, int) or isinstance(value, bool):
                errors.append(f"{path}: expected integer")
        elif expected_type == "number":
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                errors.append(f"{path}: expected number")
        if "enum" in schema and value not in schema["enum"]:
            errors.append(f"{path}: value {value!r} not in enum")
    return errors


def enum_values(spec):
    if isinstance(spec, dict) and "enum" in spec:
        return spec["enum"]
    if isinstance(spec, str) and "enum:" in spec:
        raw = spec.split("enum:", 1)[1]
        return [part.strip() for part in raw.split("|")]
    return None


def custom_contract_check(contract, answer):
    errors = []
    required = contract.get("required_top_level_keys", [])
    for key in required:
        if key not in answer:
            errors.append(f"$: missing required key {key}")
    if contract.get("additional_top_level_keys_allowed") is False:
        allowed = set(required)
        for key in answer:
            if key not in allowed:
                errors.append(f"$: unexpected key {key}")

    fields = contract.get("field_contract", {})
    for key, spec in fields.items():
        if key not in answer:
            continue
        value = answer[key]
        kind = spec.get("type")
        if kind == "object":
            if not isinstance(value, dict):
                errors.append(f"$.{key}: expected object")
                continue
            for req in spec.get("required_keys", []):
                if req not in value:
                    errors.append(f"$.{key}: missing required key {req}")
            for field_name, field_spec in spec.get("fields", {}).items():
                if field_name in value:
                    allowed = enum_values(field_spec)
                    if allowed and value[field_name] not in allowed:
                        errors.append(f"$.{key}.{field_name}: value {value[field_name]!r} not in enum")
        elif kind == "list<object>":
            if not isinstance(value, list):
                errors.append(f"$.{key}: expected list")
                continue
            if "length" in spec and len(value) != spec["length"]:
                errors.append(f"$.{key}: expected exactly {spec['length']} items")
            for index, item in enumerate(value):
                if not isinstance(item, dict):
                    errors.append(f"$.{key}[{index}]: expected object")
                    continue
                for req in spec.get("item_required_keys", []):
                    if req not in item:
                        errors.append(f"$.{key}[{index}]: missing required key {req}")
                for field_name, field_spec in spec.get("item_fields", {}).items():
                    if field_name in item:
                        allowed = enum_values(field_spec)
                        if allowed and item[field_name] not in allowed:
                            errors.append(
                                f"$.{key}[{index}].{field_name}: value {item[field_name]!r} not in enum"
                            )
        elif kind == "list<string>":
            if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
                errors.append(f"$.{key}: expected list of strings")
            if spec.get("uniqueness") and len(value) != len(set(value)):
                errors.append(f"$.{key}: duplicate string item")
            allowed = spec.get("allowed_values")
            if allowed:
                for item in value:
                    if item not in allowed:
                        errors.append(f"$.{key}: value {item!r} not allowed")

    if "no floating-point fields" in str(contract.get("numeric_precision", "")).lower():
        def walk(node, path="$"):
            if isinstance(node, float):
                errors.append(f"{path}: floating-point value is not permitted by contract")
            elif isinstance(node, dict):
                for child_key, child_value in node.items():
                    walk(child_value, f"{path}.{child_key}")
            elif isinstance(node, list):
                for index, child_value in enumerate(node):
                    walk(child_value, f"{path}[{index}]")

        walk(answer)
    return errors


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_answer.py answer_template.json answer.json", file=sys.stderr)
        return 2
    schema = load_json(sys.argv[1])
    answer = load_json(sys.argv[2])

    if "field_contract" in schema:
        errors = custom_contract_check(schema, answer)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("custom contract validation passed")
        return 0

    try:
        import jsonschema
    except Exception:
        errors = minimal_check(schema, answer)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        print("basic validation passed (jsonschema not installed)")
        return 0

    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(answer), key=lambda e: list(e.path))
    if errors:
        for error in errors:
            location = "$" + "".join(f"[{p!r}]" if isinstance(p, str) else f"[{p}]" for p in error.path)
            print(f"{location}: {error.message}", file=sys.stderr)
        return 1
    print("validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
