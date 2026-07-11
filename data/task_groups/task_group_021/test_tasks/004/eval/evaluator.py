#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
ANSWER_PATH = SCRIPT_DIR.parent / "output" / "answer.json"

SEGMENT_KEYS = [
    "enterprise_renewal",
    "strategic_renewal",
    "smb_churn_risk",
    "partner",
    "ops_lead",
    "unknown",
]
CATEGORY_KEYS = ["fuel", "maintenance", "freight", "accessorial", "claim", "tax_fee", "unknown"]
TIER_KEYS = ["platinum", "gold", "silver", "bronze", "unknown"]
REASON_KEYS = [
    "duplicate",
    "invalid_amount",
    "invalid_unit",
    "missing_contact_channel",
    "suppressed_contact",
    "ambiguous_alias",
    "superseded",
    "source_conflict",
]
QUALITY_KEYS = [
    "raw_roster_row_count",
    "crm_source_row_count",
    "canonical_partner_person_count",
    "qualified_partner_contact_count",
    "blocked_or_suppressed_roster_rows",
    "manual_review_roster_rows",
    "duplicate_person_groups",
    "company_name_variation_groups",
    "stale_reference_rows",
    "ambiguous_alias_rows",
    "missing_channel_rows",
]


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def int_object(obj, keys):
    if not isinstance(obj, dict):
        return None
    normalized = {}
    for key in keys:
        value = obj.get(key)
        if isinstance(value, bool) or not isinstance(value, int):
            return None
        normalized[key] = value
    return normalized


def sorted_str_list(value):
    if not isinstance(value, list):
        return None
    return sorted(str(item) for item in value)


def contact_by_person(answer):
    contacts = answer.get("canonical_partner_contacts")
    if not isinstance(contacts, list):
        return {}
    return {
        row.get("person_key"): normalize_contact(row)
        for row in contacts
        if isinstance(row, dict) and isinstance(row.get("person_key"), str)
    }


def decision_audit(answer):
    value = answer.get("decision_audit")
    if not isinstance(value, dict):
        return None
    return {
        "precedence_override_person_keys": sorted_str_list(value.get("precedence_override_person_keys")),
        "suppressed_reachable_row_ids": sorted_str_list(value.get("suppressed_reachable_row_ids")),
        "normalization_changed_row_ids": sorted_str_list(value.get("normalization_changed_row_ids")),
    }


def source_lineage_audit(answer):
    value = answer.get("source_lineage_audit")
    if not isinstance(value, list):
        return None
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return None
        rows.append(
            {
                "person_key": item.get("person_key"),
                "selected_partner_contact_id": item.get("selected_partner_contact_id"),
                "selected_contact_row_id": item.get("selected_contact_row_id"),
                "roster_row_ids": sorted_str_list(item.get("roster_row_ids")),
                "noncanonical_contact_row_ids": sorted_str_list(item.get("noncanonical_contact_row_ids")),
                "lineage_decision": item.get("lineage_decision"),
            }
        )
    return sorted(rows, key=lambda row: row["person_key"] or "")


def category_alias_audit(answer):
    value = answer.get("category_alias_audit")
    if not isinstance(value, list):
        return None
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return None
        rows.append(
            {
                "partner_contact_id": item.get("partner_contact_id"),
                "raw_partner_category": item.get("raw_partner_category"),
                "selected_alias": item.get("selected_alias"),
                "canonical_category": item.get("canonical_category"),
                "matched_aliases": sorted_str_list(item.get("matched_aliases")),
                "audit_reasons": sorted_str_list(item.get("audit_reasons")),
            }
        )
    return sorted(rows, key=lambda row: row["partner_contact_id"] or "")


def audit_field(answer, key):
    audit = decision_audit(answer)
    if not isinstance(audit, dict):
        return None
    return audit.get(key)


def normalize_contact(row):
    if not isinstance(row, dict):
        return None
    reasons = row.get("review_reasons")
    if isinstance(reasons, list):
        reasons = list(reasons)
    return {
        "person_key": row.get("person_key"),
        "partner_contact_id": row.get("partner_contact_id"),
        "canonical_contact_row_id": row.get("canonical_contact_row_id"),
        "email": row.get("email"),
        "phone_digits": row.get("phone_digits"),
        "company_canonical": row.get("company_canonical"),
        "partner_tier": row.get("partner_tier"),
        "canonical_segment": row.get("canonical_segment"),
        "canonical_category": row.get("canonical_category"),
        "analytics_status": row.get("analytics_status"),
        "review_reasons": reasons,
    }


def contacts_match(actual, expected, person_keys):
    actual_contacts = contact_by_person(actual)
    expected_contacts = contact_by_person(expected)
    return all(actual_contacts.get(key) == expected_contacts.get(key) for key in person_keys)


def main() -> int:
    prediction_arg = sys.argv[1] if len(sys.argv) > 1 else ""
    prediction_path = Path(prediction_arg) if prediction_arg else ANSWER_PATH

    try:
        expected = load_json(ANSWER_PATH)
        actual = load_json(prediction_path)
    except Exception as exc:
        print(json.dumps({
            "score": 0,
            "max_score": 16,
            "normalized_score": 0.0,
            "error": f"Could not load prediction JSON: {exc}",
            "points": []
        }, indent=2, sort_keys=True))
        return 0

    points = [
        {
            "id": "SP001_target_and_qualified_count",
            "weight": 3,
            "goal": "Correct roster/batch identifiers and unique qualified partner-contact count.",
            "passed": actual.get("roster_id") == expected["roster_id"]
            and actual.get("batch_id") == expected["batch_id"]
            and actual.get("qualified_partner_contact_count") == expected["qualified_partner_contact_count"]
            and audit_field(actual, "normalization_changed_row_ids")
            == audit_field(expected, "normalization_changed_row_ids"),
        },
        {
            "id": "SP002_blocked_or_suppressed_ids",
            "weight": 1,
            "goal": "Correct source roster rows blocked by suppression, do-not-contact, or revoked consent.",
            "passed": sorted_str_list(actual.get("blocked_or_suppressed_ids"))
            == sorted_str_list(expected["blocked_or_suppressed_ids"])
            and audit_field(actual, "suppressed_reachable_row_ids")
            == audit_field(expected, "suppressed_reachable_row_ids"),
        },
        {
            "id": "SP003_manual_review_ids",
            "weight": 3,
            "goal": "Correct source roster rows requiring manual review and lineage evidence.",
            "passed": sorted_str_list(actual.get("needs_manual_review_ids"))
            == sorted_str_list(expected["needs_manual_review_ids"])
            and source_lineage_audit(actual) == source_lineage_audit(expected),
        },
        {
            "id": "SP004_qualified_canonical_partner_contacts",
            "weight": 1,
            "goal": "Correct canonical qualified partner-contact rows, normalized CRM fields, and lineage evidence.",
            "passed": contacts_match(actual, expected, ["P_POW_001", "P_POW_004", "P_POW_006", "P_POW_007"])
            and audit_field(actual, "precedence_override_person_keys")
            == audit_field(expected, "precedence_override_person_keys")
            and source_lineage_audit(actual) == source_lineage_audit(expected),
        },
        {
            "id": "SP005_nonqualified_canonical_partner_contacts",
            "weight": 1,
            "goal": "Correct canonical manual-review and blocked partner-contact rows.",
            "passed": contacts_match(actual, expected, ["P_POW_003", "P_POW_005", "P_POW_008", "P_POW_009"]),
        },
        {
            "id": "SP006_segment_category_and_tier_counts",
            "weight": 1,
            "goal": "Correct normalized segment, category, partner-tier counts, and category alias audit rows.",
            "passed": int_object(actual.get("segment_counts"), SEGMENT_KEYS) == expected["segment_counts"]
            and int_object(actual.get("category_counts"), CATEGORY_KEYS) == expected["category_counts"]
            and int_object(actual.get("partner_tier_counts"), TIER_KEYS) == expected["partner_tier_counts"]
            and category_alias_audit(actual) == category_alias_audit(expected),
        },
        {
            "id": "SP007_duplicate_person_keys",
            "weight": 1,
            "goal": "Correct duplicate partner person keys across roster/contact source rows.",
            "passed": sorted_str_list(actual.get("duplicate_person_keys"))
            == sorted_str_list(expected["duplicate_person_keys"]),
        },
        {
            "id": "SP008_review_reasons_and_quality_flags",
            "weight": 1,
            "goal": "Correct review reason counts and audit quality flags.",
            "passed": int_object(actual.get("review_reason_counts"), REASON_KEYS) == expected["review_reason_counts"]
            and int_object(actual.get("quality_flags"), QUALITY_KEYS) == expected["quality_flags"]
            and decision_audit(actual) == decision_audit(expected),
        },
        {
            "id": "SP009_source_lineage_audit",
            "weight": 3,
            "goal": "Correct person-level roster and CRM lineage audit rows.",
            "passed": source_lineage_audit(actual) == source_lineage_audit(expected),
        },
        {
            "id": "SP010_category_alias_audit",
            "weight": 1,
            "goal": "Correct row-level category alias audit evidence.",
            "passed": category_alias_audit(actual) == category_alias_audit(expected),
        },
    ]

    score = sum(point["weight"] for point in points if point["passed"])
    max_score = sum(point["weight"] for point in points)
    print(json.dumps({
        "score": score,
        "max_score": max_score,
        "normalized_score": round(score / max_score, 6),
        "points": points,
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
