#!/usr/bin/env python3
"""Validate a committee answer JSON against its answer template.

Usage:
    python3 validate_answer.py answer.json answer_template.json

Checks:
    - All required top-level keys are present
    - All required nested keys are present
    - Values match their declared types
    - Enum values are within allowed choices
    - Numeric precision matches declared precision (structural check)

Does NOT verify:
    - Correctness of derived values
    - Business rule compliance
    - Ordering correctness beyond basic structural checks
"""

import json
import sys
import os
import re


def load_json(path):
    with open(path) as f:
        return json.load(f)


def check_key(obj, key, required, path):
    errors = []
    if key not in obj:
        if required:
            errors.append(f"Missing required key: {path}.{key}")
        return errors
    return []


def check_type(value, expected_type, path):
    errors = []
    if expected_type == "string" and not isinstance(value, str):
        errors.append(f"Type mismatch at {path}: expected string, got {type(value).__name__}")
    elif expected_type == "integer" and not isinstance(value, int):
        errors.append(f"Type mismatch at {path}: expected integer, got {type(value).__name__}")
    elif expected_type == "number" and not isinstance(value, (int, float)):
        errors.append(f"Type mismatch at {path}: expected number, got {type(value).__name__}")
    elif expected_type == "boolean" and not isinstance(value, bool):
        errors.append(f"Type mismatch at {path}: expected boolean, got {type(value).__name__}")
    elif expected_type == "list" and not isinstance(value, list):
        errors.append(f"Type mismatch at {path}: expected list, got {type(value).__name__}")
    elif expected_type == "object" and not isinstance(value, dict):
        errors.append(f"Type mismatch at {path}: expected object, got {type(value).__name__}")
    elif expected_type == "enum":
        if not isinstance(value, str):
            errors.append(f"Type mismatch at {path}: expected string for enum, got {type(value).__name__}")
    return errors


def check_enum(value, allowed_values, path):
    if allowed_values and isinstance(value, str):
        if value not in allowed_values:
            errors = [f"Invalid enum value at {path}: '{value}' not in {allowed_values}"]
            return errors
    return []


def check_precision(value, precision_str, path):
    errors = []
    if not isinstance(value, (int, float)):
        return errors
    match = re.search(r'(\d+)', str(precision_str))
    if match:
        precision = int(match.group(1))
        # Check that the value doesn't carry more decimal places than allowed
        # by comparing against the correctly rounded version
        rounded = round(value, precision)
        diff = abs(value - rounded)
        if diff > 0:
            # Use a small epsilon to avoid floating-point artifacts
            if diff > 10 ** (-precision - 2):
                errors.append(
                    f"Precision violation at {path}: {value} has more than {precision} decimal places"
                )
    return errors


def validate_object(obj, schema, path):
    errors = []

    if not isinstance(schema, dict):
        return errors

    if not isinstance(obj, dict):
        return [f"Expected object at {path}, got {type(obj).__name__}"]

    # Check required top-level keys
    required_keys = schema.get("required_keys") or schema.get("required_top_level_keys")
    if required_keys:
        for key in required_keys:
            errs = check_key(obj, key, True, path)
            errors.extend(errs)

    # Check fields
    fields = schema.get("fields") or schema.get("field_rules")
    if fields and isinstance(fields, dict):
        for key, field_schema in fields.items():
            field_path = f"{path}.{key}"
            if key not in obj:
                if field_schema.get("required") is True:
                    errors.append(f"Missing required field: {field_path}")
                continue

            value = obj[key]

            # Check type
            field_type = field_schema.get("type")
            if field_type:
                errors.extend(check_type(value, field_type, field_path))

            # Check enum (collect all possible enum field names from templates)
            allowed = (field_schema.get("choices")
                       or field_schema.get("allowed_values")
                       or field_schema.get("decision_enum")
                       or field_schema.get("conditions_enum")
                       or field_schema.get("handling_enum")
                       or field_schema.get("reason_code_enum")
                       or field_schema.get("owner_choices")
                       or field_schema.get("capacity_status_choices")
                       or field_schema.get("external_risk_status_choices")
                       or field_schema.get("risk_tolerance_choices")
                       or field_schema.get("committee_message_choices")
                       or field_schema.get("condition_choices"))
            if allowed and isinstance(value, str):
                errors.extend(check_enum(value, allowed, field_path))

            # Check precision
            precision = field_schema.get("precision") or field_schema.get("numeric_precision")
            if precision and isinstance(value, (int, float)):
                errors.extend(check_precision(value, str(precision), field_path))

            # Check list items for object-like fields
            if isinstance(value, list) and "item_required_keys" in field_schema:
                item_keys = field_schema["item_required_keys"]
                item_fields = field_schema.get("item_fields", {})
                for i, item in enumerate(value):
                    item_path = f"{field_path}[{i}]"
                    for rk in item_keys:
                        if rk not in item:
                            errors.append(f"Missing required key '{rk}' in {item_path}")
                    for ik, ischema in item_fields.items():
                        if ik in item:
                            iv = item[ik]
                            it = ischema.get("type")
                            if it:
                                errors.extend(check_type(iv, it, f"{item_path}.{ik}"))
                            ia = ischema.get("allowed_values") or ischema.get("choices")
                            if ia and isinstance(iv, str):
                                errors.extend(check_enum(iv, ia, f"{item_path}.{ik}"))

            # Check nested objects with their own required_keys
            if isinstance(value, dict) and "required_keys" in field_schema:
                for rk in field_schema["required_keys"]:
                    errs = check_key(value, rk, True, field_path)
                    errors.extend(errs)
                # Recursively validate nested object fields
                nested_fields = field_schema.get("fields")
                if nested_fields and isinstance(nested_fields, dict):
                    nested_schema = {"fields": nested_fields}
                    errs = validate_object(value, nested_schema, field_path)
                    errors.extend(errs)

    return errors


def main():
    if len(sys.argv) < 3:
        print("Usage: python3 validate_answer.py answer.json answer_template.json")
        sys.exit(1)

    answer_path = sys.argv[1]
    template_path = sys.argv[2]

    if not os.path.exists(answer_path):
        print(f"ERROR: answer file not found: {answer_path}")
        sys.exit(1)
    if not os.path.exists(template_path):
        print(f"ERROR: template file not found: {template_path}")
        sys.exit(1)

    answer = load_json(answer_path)
    template = load_json(template_path)

    errors = validate_object(answer, template, "root")

    if errors:
        print(f"FAILED: {len(errors)} validation error(s):")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("PASSED: Answer structurally valid against template.")
        sys.exit(0)


if __name__ == "__main__":
    main()
