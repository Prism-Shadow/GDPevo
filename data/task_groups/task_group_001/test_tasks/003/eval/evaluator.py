#!/usr/bin/env python3
"""Evaluator for test_003."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_CONTACT_IDS = ["q1_002", "q1_003", "q1_004", "q1_008"]
EXPECTED_NORMALIZED_CONTACTS = {
    "q1_002": {"email": "hana.park@riverbendchem.example", "phone": "7135550138"},
    "q1_003": {"email": "pia.norberg@lakehealthrobotics.example", "phone": "358405550190"},
    "q1_004": {"email": "", "phone": "12165550180"},
    "q1_008": {"email": "miles.chen@cascadiasteel.example", "phone": "15035550114"},
}
EXPECTED_DUPLICATES = {
    "duplicate_removed_count": 2,
    "duplicate_keys": [
        {
            "key": "email:hana.park@riverbendchem.example",
            "winner_row_id": "q1_002",
            "removed_row_ids": ["q1_001"],
        },
        {
            "key": "email:miles.chen@cascadiasteel.example",
            "winner_row_id": "q1_008",
            "removed_row_ids": ["q1_007"],
        },
    ],
}
EXPECTED_REMOVALS = {
    "unusable_removed_count": 1,
    "suppressed_removed_count": 1,
    "removed_rows": [
        {"row_id": "q1_005", "reason": "missing_contact"},
        {"row_id": "q1_006", "reason": "suppressed"},
    ],
}
EXPECTED_ACTION_TOTALS = {
    "create_account": 2,
    "update_existing": 2,
    "no_import": 3,
    "suppress": 1,
}
EXPECTED_CAMPAIGN_MEMBER_IMPORT = {
    "count": 4,
    "source_label": "partner_and_manual_upload",
}

POINTS = [
    ("SP001", "Correct surviving cleaned contact IDs in order.", 3),
    ("SP002", "Correct normalized email and phone values for key contacts.", 3),
    ("SP003", "Correct duplicate resolution winners.", 2),
    ("SP004", "Correct suppression and unusable removal counts.", 2),
    ("SP005", "Correct create/update/no-import counts.", 2),
    ("SP006", "Correct campaign member count and source label.", 1),
]


def load_json(path: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - report parse/read errors as score JSON.
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "Top-level JSON value must be an object."
    return data, None


def clean_contacts(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = data.get("clean_contacts", [])
    return rows if isinstance(rows, list) else []


def contact_id(row: dict[str, Any]) -> str:
    return str(row.get("clean_contact_id") or row.get("source_row_id") or "")


def normalized_contact_map(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for row in clean_contacts(data):
        if not isinstance(row, dict):
            continue
        result[contact_id(row)] = {
            "email": "" if row.get("email") is None else str(row.get("email")),
            "phone": "" if row.get("phone") is None else str(row.get("phone")),
        }
    return result


def norm_duplicate_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    keys = value.get("duplicate_keys", [])
    normalized = []
    if isinstance(keys, list):
        for item in keys:
            if not isinstance(item, dict):
                continue
            removed = item.get("removed_row_ids", [])
            normalized.append(
                {
                    "key": str(item.get("key", "")),
                    "winner_row_id": str(item.get("winner_row_id", "")),
                    "removed_row_ids": sorted(str(row_id) for row_id in removed) if isinstance(removed, list) else [],
                }
            )
    return {
        "duplicate_removed_count": value.get("duplicate_removed_count"),
        "duplicate_keys": sorted(normalized, key=lambda item: item["key"]),
    }


def norm_removal_summary(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    rows = value.get("removed_rows", [])
    relevant_reasons = {"missing_contact", "suppressed"}
    normalized = []
    if isinstance(rows, list):
        for item in rows:
            if not isinstance(item, dict):
                continue
            reason = str(item.get("reason", ""))
            if reason in relevant_reasons:
                normalized.append({"row_id": str(item.get("row_id", "")), "reason": reason})
    return {
        "unusable_removed_count": value.get("unusable_removed_count"),
        "suppressed_removed_count": value.get("suppressed_removed_count"),
        "removed_rows": sorted(normalized, key=lambda item: item["row_id"]),
    }


def int_totals(value: Any, keys: list[str]) -> dict[str, int | None]:
    if not isinstance(value, dict):
        return dict.fromkeys(keys)
    result: dict[str, int | None] = {}
    for key in keys:
        try:
            result[key] = int(value.get(key))
        except (TypeError, ValueError):
            result[key] = None
    return result


def norm_campaign_member_import(data: dict[str, Any]) -> dict[str, Any]:
    value = data.get("campaign_member_import")
    if isinstance(value, dict):
        try:
            count: int | None = int(value.get("count"))
        except (TypeError, ValueError):
            count = None
        return {
            "count": count,
            "source_label": str(value.get("source_label", "")),
        }
    try:
        legacy_count: int | None = int(data.get("campaign_member_import_count"))
    except (TypeError, ValueError):
        legacy_count = None
    return {
        "count": legacy_count,
        "source_label": str(data.get("campaign_member_source_label", "")),
    }


def evaluate(data: dict[str, Any]) -> list[dict[str, Any]]:
    contact_ids = [contact_id(row) for row in clean_contacts(data) if isinstance(row, dict)]
    checks = {
        "SP001": contact_ids == EXPECTED_CONTACT_IDS,
        "SP002": normalized_contact_map(data) == EXPECTED_NORMALIZED_CONTACTS,
        "SP003": norm_duplicate_summary(data.get("duplicate_summary")) == EXPECTED_DUPLICATES,
        "SP004": norm_removal_summary(data.get("removal_summary")) == EXPECTED_REMOVALS,
        "SP005": int_totals(data.get("import_action_totals"), list(EXPECTED_ACTION_TOTALS)) == EXPECTED_ACTION_TOTALS,
        "SP006": norm_campaign_member_import(data) == EXPECTED_CAMPAIGN_MEMBER_IMPORT,
    }

    results = []
    for point_id, label, weight in POINTS:
        passed = bool(checks[point_id])
        results.append(
            {
                "id": point_id,
                "label": label,
                "weight": weight,
                "passed": passed,
                "score": weight if passed else 0,
            }
        )
    return results


def failure_result(error: str | None) -> dict[str, Any]:
    total_weight = sum(weight for _, _, weight in POINTS)
    return {
        "total_score": 0.0,
        "earned_points": 0,
        "total_points": total_weight,
        "error": error,
        "points": [
            {"id": point_id, "label": label, "weight": weight, "passed": False, "score": 0}
            for point_id, label, weight in POINTS
        ],
    }


def main() -> int:
    if len(sys.argv) != 2:
        print(json.dumps({"error": "Usage: eval.sh <prediction_json>"}, indent=2))
        return 2

    data, error = load_json(sys.argv[1])
    if error is not None or data is None:
        print(json.dumps(failure_result(error), indent=2, sort_keys=True))
        return 0

    results = evaluate(data)
    earned = sum(item["score"] for item in results)
    total = sum(item["weight"] for item in results)
    print(
        json.dumps(
            {
                "total_score": round(earned / total, 6),
                "earned_points": earned,
                "total_points": total,
                "points": results,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
