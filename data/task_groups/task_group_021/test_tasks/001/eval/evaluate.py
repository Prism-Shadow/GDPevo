#!/usr/bin/env python3
"""Evaluator for test_001 CRM contact import audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
EXPECTED_PATH = TASK_DIR / "output" / "answer.json"

POINTS = [
    (
        "transfer_train_001_train_004_retained_count",
        2,
        "Correct target batch and retained canonical contact count.",
    ),
    (
        "transfer_train_001_blocked_and_unreachable",
        2,
        "Correct unreachable canonical count and suppressed source-row IDs.",
    ),
    (
        "transfer_train_001_duplicate_group_count",
        3,
        "Correct duplicate person-key group count and source-lineage audit.",
    ),
    (
        "task_specific_source_conflict_person_keys",
        2,
        "Correct target-batch source-conflict person keys.",
    ),
    (
        "transfer_train_001_canonical_status_and_source",
        3,
        "Correct canonical person decisions, statuses, and sources.",
    ),
    (
        "transfer_train_001_canonical_normalized_channels",
        2,
        "Correct normalized canonical email, phone, city, and domain values.",
    ),
    (
        "transfer_train_004_task_specific_city_domain_counts",
        2,
        "Correct retained-contact city and domain counts.",
    ),
    (
        "mixed_quality_flag_counts",
        3,
        "Correct quality issue counts, including target-specific conflict counts.",
    ),
]

SOURCE_ENUMS = {"crm_verified", "event_import", "partner_roster", "steward_override"}
STATUS_ENUMS = {"retained", "dropped_unreachable", "suppressed", "manual_review"}
QUALITY_KEYS = [
    "raw_row_count",
    "canonical_person_count",
    "duplicate_person_groups",
    "duplicate_source_rows",
    "missing_channel_rows",
    "suppression_rows",
    "email_normalization_rows",
    "phone_normalization_rows",
    "stale_or_inactive_rows",
    "source_conflict_groups",
    "source_conflict_rows",
]


def load_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def as_int(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return value


def normalize_id_list(value):
    if not isinstance(value, list):
        return value
    return sorted(str(item).strip() for item in value)


def normalize_counts(value):
    if not isinstance(value, dict):
        return value
    return {str(key).strip(): as_int(val) for key, val in sorted(value.items())}


def normalize_quality_flags(value):
    if not isinstance(value, dict):
        return value
    return {key: as_int(value.get(key)) for key in QUALITY_KEYS}


def decision_audit(answer):
    value = answer.get("decision_audit")
    if not isinstance(value, dict):
        return None
    return {
        "precedence_override_person_keys": normalize_id_list(value.get("precedence_override_person_keys")),
        "suppressed_reachable_row_ids": normalize_id_list(value.get("suppressed_reachable_row_ids")),
        "normalization_changed_row_ids": normalize_id_list(value.get("normalization_changed_row_ids")),
    }


def audit_field(answer, key):
    audit = decision_audit(answer)
    if not isinstance(audit, dict):
        return None
    return audit.get(key)


def normalize_contacts(value):
    if not isinstance(value, list):
        return value
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return value
        source = str(item.get("canonical_source", "")).strip()
        status = str(item.get("contact_status", "")).strip()
        email = str(item.get("email", "")).strip().lower()
        email_domain = str(item.get("email_domain", "")).strip().lower()
        normalized.append(
            {
                "person_key": str(item.get("person_key", "")).strip(),
                "canonical_source": source,
                "email": email,
                "phone_digits": "".join(ch for ch in str(item.get("phone_digits", "")) if ch.isdigit()),
                "city": str(item.get("city", "")).strip(),
                "email_domain": email_domain,
                "contact_status": status,
                "_valid_enums": source in SOURCE_ENUMS and status in STATUS_ENUMS,
            }
        )
    return sorted(normalized, key=lambda row: row["person_key"])


def normalize_source_lineage(value):
    if not isinstance(value, list):
        return value
    rows = []
    for item in value:
        if not isinstance(item, dict):
            return value
        rows.append(
            {
                "person_key": str(item.get("person_key", "")).strip(),
                "source_row_ids": normalize_id_list(item.get("source_row_ids")),
                "selected_row_id": str(item.get("selected_row_id", "")).strip(),
                "noncanonical_source_row_ids": normalize_id_list(item.get("noncanonical_source_row_ids")),
                "lineage_decision": str(item.get("lineage_decision", "")).strip(),
            }
        )
    return sorted(rows, key=lambda row: row["person_key"])


def contact_status_source_map(answer):
    contacts = normalize_contacts(answer.get("canonical_contacts"))
    if not isinstance(contacts, list):
        return contacts
    return {
        row["person_key"]: {
            "canonical_source": row["canonical_source"],
            "contact_status": row["contact_status"],
            "_valid_enums": row["_valid_enums"],
        }
        for row in contacts
    }


def contact_channel_map(answer):
    contacts = normalize_contacts(answer.get("canonical_contacts"))
    if not isinstance(contacts, list):
        return contacts
    return {
        row["person_key"]: {
            "email": row["email"],
            "phone_digits": row["phone_digits"],
            "city": row["city"],
            "email_domain": row["email_domain"],
        }
        for row in contacts
    }


def score_prediction(predicted, expected):
    checks = {
        "transfer_train_001_train_004_retained_count": (
            str(predicted.get("batch_id", "")).strip() == expected.get("batch_id")
            and as_int(predicted.get("retained_contact_count")) == expected.get("retained_contact_count")
            and audit_field(predicted, "normalization_changed_row_ids")
            == audit_field(expected, "normalization_changed_row_ids")
        ),
        "transfer_train_001_blocked_and_unreachable": (
            as_int(predicted.get("dropped_unreachable_count")) == expected.get("dropped_unreachable_count")
            and normalize_id_list(predicted.get("suppressed_contact_ids"))
            == normalize_id_list(expected.get("suppressed_contact_ids"))
            and audit_field(predicted, "suppressed_reachable_row_ids")
            == audit_field(expected, "suppressed_reachable_row_ids")
        ),
        "transfer_train_001_duplicate_group_count": as_int(predicted.get("duplicate_group_count"))
        == expected.get("duplicate_group_count")
        and normalize_source_lineage(predicted.get("source_lineage_audit"))
        == normalize_source_lineage(expected.get("source_lineage_audit")),
        "task_specific_source_conflict_person_keys": normalize_id_list(predicted.get("source_conflict_person_keys"))
        == normalize_id_list(expected.get("source_conflict_person_keys"))
        and normalize_source_lineage(predicted.get("source_lineage_audit"))
        == normalize_source_lineage(expected.get("source_lineage_audit")),
        "transfer_train_001_canonical_status_and_source": contact_status_source_map(predicted)
        == contact_status_source_map(expected)
        and audit_field(predicted, "precedence_override_person_keys")
        == audit_field(expected, "precedence_override_person_keys"),
        "transfer_train_001_canonical_normalized_channels": contact_channel_map(predicted)
        == contact_channel_map(expected),
        "transfer_train_004_task_specific_city_domain_counts": (
            normalize_counts(predicted.get("city_retained_counts")) == normalize_counts(expected.get("city_retained_counts"))
            and normalize_counts(predicted.get("domain_retained_counts"))
            == normalize_counts(expected.get("domain_retained_counts"))
        ),
        "mixed_quality_flag_counts": normalize_quality_flags(predicted.get("quality_flags"))
        == normalize_quality_flags(expected.get("quality_flags"))
        and decision_audit(predicted) == decision_audit(expected)
        and normalize_source_lineage(predicted.get("source_lineage_audit"))
        == normalize_source_lineage(expected.get("source_lineage_audit")),
    }

    total_weight = sum(weight for _, weight, _ in POINTS)
    earned = sum(weight for name, weight, _ in POINTS if checks.get(name))
    return {
        "score": earned,
        "max_score": total_weight,
        "normalized_score": round(earned / total_weight, 6),
        "points": [
            {
                "id": name,
                "goal": goal,
                "weight": weight,
                "matched": bool(checks.get(name)),
                "earned": weight if checks.get(name) else 0,
            }
            for name, weight, goal in POINTS
        ],
    }


def main():
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1] else EXPECTED_PATH
    expected = load_json(EXPECTED_PATH)
    try:
        predicted = load_json(prediction_path)
        if not isinstance(predicted, dict):
            raise ValueError("Prediction JSON must be an object.")
        result = score_prediction(predicted, expected)
    except Exception as exc:  # noqa: BLE001
        total_weight = sum(weight for _, weight, _ in POINTS)
        result = {
            "score": 0,
            "max_score": total_weight,
            "normalized_score": 0.0,
            "error": str(exc),
            "points": [
                {"id": name, "goal": goal, "weight": weight, "matched": False, "earned": 0}
                for name, weight, goal in POINTS
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
