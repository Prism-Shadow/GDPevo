#!/usr/bin/env python3
"""Validate a candidate answer against a task's answer_template.json.

Usage:
    python3 validate.py <answer.json> <answer_template.json>

Run this before finalizing. The answer is scored by exact field/value match to a gold
answer, so a value not in the template's enum is NOT automatically wrong — the gold is
built from the same hub data and may use the same literal (e.g. volume_unit="report" or
"files"). Treat non-enum values as deliberate (keep the hub literal, or map to an enum
member).

Handles both template styles:
  - "fields"/"enums" style (train_001, train_003, train_004, train_005)
  - "schema"/"enum_choices" style (train_002)

Errors (must fix): missing required top-level keys, list items missing item_required_keys,
missing metrics required_keys, integer fields that are not integers.
Warnings (review): values not in the template's enum for enum-typed fields.
"""
import json
import sys


def load(p):
    with open(p) as f:
        return json.load(f)


# field name -> enum key (the enum key may differ per template; checked at runtime)
FIELD_TO_ENUM = {
    "issue_type": "issue_type",
    "risk_level": "risk_level",
    "severity": "severity",
    "status": "risk_status",
    "finding_status": "finding_status",
    "issue_status": "issue_status",
    "source_status": "source_status",
    "production_impact": "production_impact",
    "volume_unit": "volume_unit",
    "recommended_action": "action_type",
    "action_type": "action_type",
    "correction_type": "privilege_correction_type",
    "privilege_status": "privilege_status",
    "readiness_status": "readiness_status",
    "current_coding": "coding",
    "produced_status": "produced_status",
    "corrected_disposition": "corrected_disposition",
    "owner": "owner",
    "priority": "priority",
    "availability_status": "availability_status",
    "active_system_issue": "active_system_issue",
    "archive_status": "archive_status",
    "gap_type": "gap_type",
    "source_type": "source_type",
}

# section -> enum key to use for a generic 'status' field (overrides risk_status default)
STATUS_OVERRIDE = {
    "category_coverage": "category_status",
    "category_statuses": "category_status",
    "retention_events": "retention_status",
    "communication_gaps": "retention_status",
    "readiness_statuses": "readiness_status",
}

INT_FIELDS = {
    "priority_rank", "rank", "due_days", "open_issue_count", "retention_years",
    "retention_period_months", "purge_window_days", "document_count", "withheld_count",
    "logged_count", "unlogged_count", "volume_count",
}


def main(answer_path, template_path):
    ans = load(answer_path)
    tmpl = load(template_path)
    enums = tmpl.get("enums") or tmpl.get("enum_choices") or {}
    fields = tmpl.get("fields", {})
    schema = tmpl.get("schema", {})
    errors = []
    warnings = []

    for k in tmpl.get("required_top_level_keys", []):
        if k not in ans:
            errors.append(f"missing top-level key: {k}")

    if "metrics" in fields and "metrics" in ans:
        for k in fields["metrics"].get("required_keys", []):
            if k not in ans["metrics"]:
                errors.append(f"missing metric: {k}")
    # schema-style metrics (train_002)
    if "metrics" in schema and "metrics" in ans and isinstance(schema["metrics"], dict):
        for k in schema["metrics"]:
            if k not in ans["metrics"]:
                errors.append(f"missing metric: {k}")

    def required_keys_for(section):
        f = fields.get(section)
        if isinstance(f, dict) and "item_required_keys" in f:
            return f["item_required_keys"]
        s = schema.get(section)
        if isinstance(s, list) and s and isinstance(s[0], dict):
            return list(s[0].keys())
        if isinstance(s, dict):
            return list(s.keys())
        return None

    sections = ("critical_findings", "category_statuses", "priority_actions", "top_risks",
                "category_coverage", "retained_or_available_sources", "action_plan",
                "retention_events", "communication_gaps", "available_archives",
                "recommended_actions", "readiness_statuses", "issue_ledger",
                "privilege_corrections")

    for section in sections:
        items = ans.get(section, [])
        if not isinstance(items, list):
            continue
        req = required_keys_for(section)
        for i, item in enumerate(items):
            if not isinstance(item, dict):
                errors.append(f"{section}[{i}] not an object")
                continue
            if req:
                for k in req:
                    if k not in item:
                        errors.append(f"{section}[{i}] missing {k}")
            for f, v in item.items():
                if v is None:
                    continue
                enum_name = FIELD_TO_ENUM.get(f)
                if f == "status":
                    enum_name = STATUS_OVERRIDE.get(section, "risk_status")
                if enum_name and enum_name in enums:
                    if isinstance(v, str) and v not in enums[enum_name]:
                        warnings.append(f"{section}[{i}].{f}='{v}' not in enum {enum_name} (keep hub literal if it came from the hub, else map to an enum member)")
                if f in INT_FIELDS or f.endswith("_count"):
                    if not isinstance(v, int):
                        errors.append(f"{section}[{i}].{f}={v!r} not int")

    if errors:
        print("INVALID — fix before submitting:")
        for e in errors:
            print("  " + e)
        if warnings:
            print("Warnings:")
            for w in warnings:
                print("  " + w)
        sys.exit(1)
    if warnings:
        print("VALID (structure) — review enum warnings:")
        for w in warnings:
            print("  " + w)
    else:
        print("VALID — all required keys, types, and enum values pass.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1], sys.argv[2])
