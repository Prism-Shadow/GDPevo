#!/usr/bin/env python3
"""Validate a Cedar Ridge output JSON against its answer template."""

import json
import sys
import os


def load_json(path):
    if not os.path.exists(path):
        print(f"ERROR: File not found: {path}")
        sys.exit(1)
    with open(path) as f:
        try:
            return json.load(f)
        except json.JSONDecodeError as e:
            print(f"ERROR: Invalid JSON in {path}: {e}")
            sys.exit(1)


def check_enum(value, allowed, context):
    if value not in allowed:
        print(f"FAIL: {context}: '{value}' not in {sorted(allowed)}")
        return False
    return True


def check_top_keys(template, output, errors):
    for k in template.get("required_top_level_keys", []):
        if k not in output:
            print(f"FAIL: Missing top-level key '{k}'")
            errors += 1
    return errors


def check_required_value(template, output, field, errors):
    spec = template.get("fields", {}).get(field, {})
    if "required_value" in spec and output.get(field) != spec["required_value"]:
        print(f"FAIL: {field} should be '{spec['required_value']}', got '{output.get(field)}'")
        errors += 1
    return errors


def validate_ids_ordered(patients, required_ids, id_key, label, errors):
    if len(patients) != len(required_ids):
        print(f"FAIL: {label}: expected {len(required_ids)}, got {len(patients)}")
        return errors + 1
    for i, pid in enumerate(required_ids):
        if patients[i].get(id_key) != pid:
            print(f"FAIL: {label}[{i}] should be {pid}, got {patients[i].get(id_key)}")
            errors += 1
    return errors


def validate_patient_access(template, output):
    errors = 0
    errors = check_top_keys(template, output, errors)
    fields = template.get("fields", {})

    for field in ["task_id", "roster_id", "service_line"]:
        errors = check_required_value(template, output, field, errors)

    pr_spec = fields.get("patient_results", {})
    required_ids = pr_spec.get("required_patient_ids", [])
    patient_results = output.get("patient_results", [])

    errors = validate_ids_ordered(patient_results, required_ids, "patient_id", "patient_results", errors)

    item_fields = pr_spec.get("item_fields", {})
    allowed_blocked = item_fields.get("blocked_reason_codes", {}).get("allowed_values", [])
    for pr in patient_results:
        pid = pr.get("patient_id", "?")
        for field, fspec in item_fields.items():
            if fspec.get("type") == "enum":
                errors += 0 if check_enum(pr.get(field), fspec.get("allowed_values", []), f"{pid}.{field}") else 1
        for code in pr.get("blocked_reason_codes", []):
            if code not in allowed_blocked:
                print(f"FAIL: {pid}.blocked_reason_codes: '{code}' not allowed")
                errors += 1

    cs = output.get("cohort_summary", {})
    if cs.get("total_patients") != len(patient_results):
        print(f"FAIL: total_patients mismatch")
        errors += 1

    for status in fields.get("cohort_summary", {}).get("count_keys", {}).get("counts_by_registration_status", []):
        actual = sum(1 for p in patient_results if p.get("registration_status") == status)
        if cs.get("counts_by_registration_status", {}).get(status, 0) != actual:
            print(f"FAIL: counts_by_registration_status.{status} mismatch")
            errors += 1

    for risk_name, field_name in [("counts_by_overall_risk", "overall_risk"), ("counts_by_lifestyle_risk", "lifestyle_risk")]:
        for level in fields.get("cohort_summary", {}).get("count_keys", {}).get(risk_name, []):
            actual = sum(1 for p in patient_results if p.get(field_name) == level)
            if cs.get(risk_name, {}).get(level, 0) != actual:
                print(f"FAIL: {risk_name}.{level} mismatch")
                errors += 1

    return errors


def main():
    if len(sys.argv) != 3:
        print("Usage: python validate_output.py <template_path> <output_path>")
        sys.exit(1)

    template = load_json(sys.argv[1])
    output = load_json(sys.argv[2])

    errors = 0
    if "fields" in template and "roster_id" in str(template.get("fields", {})):
        errors = validate_patient_access(template, output)
    elif "top_level" in template:
        errors = check_top_keys(template.get("top_level", {}), output, errors)
        reviews = output.get("referral_reviews", [])
        rids = [r["referral_id"] for r in reviews]
        if rids != sorted(rids):
            print("FAIL: referral_reviews not ascending")
            errors += 1
        summary = output.get("summary", {})
        if summary.get("total_referrals") != len(reviews):
            print("FAIL: total_referrals mismatch")
            errors += 1
    elif "patients" in template and isinstance(template.get("patients"), dict):
        errors = check_required_value(template, output, "batch_id", errors)
        patients = output.get("patients", [])
        cs = output.get("cohort_summary", {})
        if cs.get("total_transfers") != len(patients):
            print("FAIL: total_transfers mismatch")
            errors += 1
    else:
        errors = check_top_keys(template, output, errors)
        rbr = output.get("readiness_by_referral", [])
        rids = [r["referral_id"] for r in rbr]
        if rids != sorted(rids):
            print("FAIL: readiness_by_referral not ascending")
            errors += 1

    if errors == 0:
        print("OK: All validations passed.")
    else:
        print(f"\n{errors} validation error(s) found.")
        sys.exit(1)


if __name__ == "__main__":
    main()
