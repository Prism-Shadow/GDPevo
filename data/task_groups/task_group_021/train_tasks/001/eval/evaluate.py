#!/usr/bin/env python3
"""Evaluator for train_001 CRM contact import audit."""

from __future__ import annotations

import json
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
TASK_DIR = SCRIPT_DIR.parent
EXPECTED_PATH = TASK_DIR / "output" / "answer.json"

POINTS = [
    ("batch_and_retained_count", 1),
    ("unreachable_drop_count", 2),
    ("duplicate_group_count", 3),
    ("suppressed_source_rows", 2),
    ("canonical_status_and_source", 3),
    ("canonical_normalized_channels", 2),
    ("retained_city_counts", 2),
    ("quality_flag_counts", 3),
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


def normalize_city_counts(value):
    if not isinstance(value, dict):
        return value
    return {str(key).strip(): as_int(val) for key, val in sorted(value.items())}


def normalize_quality_flags(value):
    if not isinstance(value, dict):
        return value
    return {key: as_int(value.get(key)) for key in QUALITY_KEYS}


def normalize_contacts(value):
    if not isinstance(value, list):
        return value
    normalized = []
    for item in value:
        if not isinstance(item, dict):
            return value
        person_key = str(item.get("person_key", "")).strip()
        source = str(item.get("canonical_source", "")).strip()
        status = str(item.get("contact_status", "")).strip()
        normalized.append(
            {
                "person_key": person_key,
                "canonical_source": source,
                "email": str(item.get("email", "")).strip().lower(),
                "phone_digits": "".join(ch for ch in str(item.get("phone_digits", "")) if ch.isdigit()),
                "city": str(item.get("city", "")).strip(),
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
        }
        for row in contacts
    }


def score_prediction(predicted, expected):
    checks = {
        "batch_and_retained_count": (
            str(predicted.get("batch_id", "")).strip() == expected.get("batch_id")
            and as_int(predicted.get("retained_contact_count")) == expected.get("retained_contact_count")
        ),
        "unreachable_drop_count": as_int(predicted.get("dropped_unreachable_count"))
        == expected.get("dropped_unreachable_count"),
        "duplicate_group_count": as_int(predicted.get("duplicate_group_count")) == expected.get("duplicate_group_count")
        and normalize_source_lineage(predicted.get("source_lineage_audit"))
        == normalize_source_lineage(expected.get("source_lineage_audit")),
        "suppressed_source_rows": normalize_id_list(predicted.get("suppressed_contact_ids"))
        == normalize_id_list(expected.get("suppressed_contact_ids")),
        "canonical_status_and_source": contact_status_source_map(predicted) == contact_status_source_map(expected),
        "canonical_normalized_channels": contact_channel_map(predicted) == contact_channel_map(expected),
        "retained_city_counts": normalize_city_counts(predicted.get("city_retained_counts"))
        == normalize_city_counts(expected.get("city_retained_counts")),
        "quality_flag_counts": normalize_quality_flags(predicted.get("quality_flags"))
        == normalize_quality_flags(expected.get("quality_flags"))
        and normalize_source_lineage(predicted.get("source_lineage_audit"))
        == normalize_source_lineage(expected.get("source_lineage_audit")),
    }

    total_weight = sum(weight for _, weight in POINTS)
    earned = sum(weight for name, weight in POINTS if checks.get(name))
    return {
        "score": earned,
        "max_score": total_weight,
        "normalized_score": round(earned / total_weight, 6),
        "points": [
            {
                "id": name,
                "weight": weight,
                "matched": bool(checks.get(name)),
                "earned": weight if checks.get(name) else 0,
            }
            for name, weight in POINTS
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
        total_weight = sum(weight for _, weight in POINTS)
        result = {
            "score": 0,
            "max_score": total_weight,
            "normalized_score": 0.0,
            "error": str(exc),
            "points": [
                {"id": name, "weight": weight, "matched": False, "earned": 0}
                for name, weight in POINTS
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
