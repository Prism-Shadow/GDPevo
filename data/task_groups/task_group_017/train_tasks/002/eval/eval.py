#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_RECORDS = {
    "RC-2019-LAB": {
        "record_classes": ["2019 lab data boxes"],
        "category_ids": ["N-01"],
        "timing_class": "pre_hold_policy",
        "severity": "medium",
        "quantity": 4,
        "source_event_ids": ["CE-0003", "DE-0002", "RR-0001"],
        "primary_action": "no_action_policy_gap",
        "notice_required": False,
    },
    "RC-AUDIT-OCT2023": {
        "record_classes": ["environmental audit reports"],
        "category_ids": ["N-03"],
        "timing_class": "retained_missing",
        "severity": "high",
        "quantity": 1,
        "source_event_ids": ["CE-0007", "PL-0006", "RR-0006"],
        "primary_action": "vendor_retrieval",
        "notice_required": False,
    },
    "RC-EHS-BOX": {
        "record_classes": ["EHS correspondence boxes"],
        "category_ids": ["N-02", "N-05"],
        "timing_class": "post_hold_spoliation",
        "severity": "critical",
        "quantity": 2,
        "source_event_ids": ["CE-0004", "DE-0003", "RR-0002"],
        "primary_action": "regulator_notice",
        "notice_required": True,
    },
    "RC-EMAIL-ARCHIVE": {
        "record_classes": ["executive email archive"],
        "category_ids": ["N-02", "N-05"],
        "timing_class": "recoverable_archive",
        "severity": "low",
        "quantity": 11320,
        "source_event_ids": ["CE-0006", "RR-0005"],
        "primary_action": "supplemental_collection",
        "notice_required": False,
    },
    "RC-TEAMS-VOICE": {
        "record_classes": ["Teams chat", "voicemail"],
        "category_ids": ["N-02"],
        "timing_class": "uncollected_source",
        "severity": "high",
        "quantity": 1300,
        "source_event_ids": ["CE-0005", "PL-0005", "RR-0003", "RR-0004"],
        "primary_action": "supplemental_collection",
        "notice_required": True,
    },
}

EXPECTED_DEFECTS = {
    "HD-OFFSITE-VENDOR": {
        "defect_type": "offsite_vendor_not_on_hold",
        "category_ids": ["N-02", "N-05"],
        "affected_sources": ["Vendor EHS correspondence boxes"],
        "severity": "critical",
        "primary_action": "hold_refresh",
        "notice_required": True,
    },
    "HD-PERSONAL-DEVICE": {
        "defect_type": "personal_device_notice_omission",
        "category_ids": ["N-06"],
        "affected_sources": ["SMS", "personal phone"],
        "severity": "high",
        "primary_action": "supplemental_collection",
        "notice_required": False,
    },
}

EXPECTED_SOURCES = {
    "RS-AUDIT-VENDOR": {
        "source_name": "Audit vendor portal",
        "record_class": "environmental audit reports",
        "category_ids": ["N-03"],
        "recovery_status": "retained_missing",
        "count": 1,
        "source_event_ids": ["CE-0007", "RR-0006"],
        "primary_action": "vendor_retrieval",
    },
    "RS-EMAIL-IRONVAULT": {
        "source_name": "Ironvault seven-year archive",
        "record_class": "executive email archive",
        "category_ids": ["N-02", "N-05"],
        "recovery_status": "available",
        "count": 11320,
        "source_event_ids": ["CE-0006", "RR-0005"],
        "primary_action": "supplemental_collection",
    },
    "RS-LAB-SUMMARIES": {
        "source_name": "lab summaries",
        "record_class": "2019 lab data boxes",
        "category_ids": ["N-01"],
        "recovery_status": "partial",
        "count": 0,
        "source_event_ids": ["DE-0002"],
        "primary_action": "supplemental_collection",
    },
}

EXPECTED_REMEDIATION = [
    {
        "rank": 1,
        "action_id": "RA-REGULATOR-NOTICE",
        "action": "regulator_notice",
        "issue_ids": ["HD-OFFSITE-VENDOR", "RC-EHS-BOX"],
        "owner_queue": "legal",
    },
    {
        "rank": 2,
        "action_id": "RA-AUDIT-RETRIEVAL",
        "action": "vendor_retrieval",
        "issue_ids": ["RC-AUDIT-OCT2023"],
        "owner_queue": "records",
    },
    {
        "rank": 3,
        "action_id": "RA-SUPPLEMENTAL-COLLECTION",
        "action": "supplemental_collection",
        "issue_ids": ["HD-PERSONAL-DEVICE", "RC-EMAIL-ARCHIVE", "RC-TEAMS-VOICE"],
        "owner_queue": "e_discovery",
    },
    {
        "rank": 4,
        "action_id": "RA-HOLD-REFRESH",
        "action": "hold_refresh",
        "issue_ids": ["HD-OFFSITE-VENDOR", "HD-PERSONAL-DEVICE"],
        "owner_queue": "litigation_support",
    },
    {
        "rank": 5,
        "action_id": "RA-POLICY-GAP-LOG",
        "action": "no_action_policy_gap",
        "issue_ids": ["RC-2019-LAB"],
        "owner_queue": "records",
    },
]

EXPECTED_OVERALL = {
    "disclosure_required": True,
    "blocked_category_ids": ["N-02", "N-03", "N-05", "N-06"],
    "policy_gap_category_ids": ["N-01"],
    "post_hold_spoliation_issue_ids": ["RC-EHS-BOX"],
}


def load_json(path: str) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_string(value: Any) -> str:
    return "" if value is None else str(value).strip()


def norm_scalar(value: Any) -> Any:
    if isinstance(value, str):
        return value.strip()
    return value


def norm_list(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return []
    return sorted(norm_scalar(item) for item in value)


def int_equal(actual: Any, expected: int) -> bool:
    try:
        return int(actual) == expected
    except (TypeError, ValueError):
        return False


def bool_equal(actual: Any, expected: bool) -> bool:
    return isinstance(actual, bool) and actual is expected


def rows_by_id(candidate: Any, list_key: str, id_key: str) -> dict[str, dict[str, Any]]:
    rows = candidate.get(list_key, []) if isinstance(candidate, dict) else []
    if not isinstance(rows, list):
        return {}
    mapped: dict[str, dict[str, Any]] = {}
    for row in rows:
        if isinstance(row, dict):
            row_id = as_string(row.get(id_key))
            if row_id:
                mapped[row_id] = row
    return mapped


def dict_subset_match(row: dict[str, Any], expected: dict[str, Any]) -> bool:
    for key, exp_value in expected.items():
        actual = row.get(key)
        if isinstance(exp_value, list):
            if norm_list(actual) != norm_list(exp_value):
                return False
        elif isinstance(exp_value, bool):
            if not bool_equal(actual, exp_value):
                return False
        elif isinstance(exp_value, int):
            if not int_equal(actual, exp_value):
                return False
        else:
            if norm_scalar(actual) != exp_value:
                return False
    return True


def remediation_observed(candidate: dict[str, Any]) -> list[dict[str, Any]]:
    rows = candidate.get("remediation_plan", [])
    if not isinstance(rows, list):
        return []
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        normalized.append(
            {
                "rank": row.get("rank"),
                "action_id": as_string(row.get("action_id")),
                "action": as_string(row.get("action")),
                "issue_ids": norm_list(row.get("issue_ids")),
                "owner_queue": as_string(row.get("owner_queue")),
            }
        )
    return sorted(normalized, key=lambda item: int(item["rank"]) if str(item["rank"]).isdigit() else 999)


def remediation_expected() -> list[dict[str, Any]]:
    return [
        {
            "rank": row["rank"],
            "action_id": row["action_id"],
            "action": row["action"],
            "issue_ids": norm_list(row["issue_ids"]),
            "owner_queue": row["owner_queue"],
        }
        for row in EXPECTED_REMEDIATION
    ]


def add_result(
    details: list[dict[str, Any]],
    name: str,
    weight: int,
    passed: bool,
    expected: Any,
    observed: Any,
) -> None:
    details.append(
        {
            "name": name,
            "weight": weight,
            "earned": weight if passed else 0,
            "passed": passed,
            "expected": expected,
            "observed": observed,
        }
    )


def evaluate(candidate: dict[str, Any]) -> dict[str, Any]:
    details: list[dict[str, Any]] = []
    records = rows_by_id(candidate, "record_class_findings", "issue_id")
    defects = rows_by_id(candidate, "hold_defects", "defect_id")
    sources = rows_by_id(candidate, "recoverable_sources", "source_id")
    overall = candidate.get("overall", {}) if isinstance(candidate.get("overall"), dict) else {}

    add_result(
        details,
        "metadata_and_complete_issue_sets",
        1,
        candidate.get("matter_id") == "M-NVK-219"
        and candidate.get("hold_date") == "2024-11-25"
        and norm_list(list(records.keys())) == norm_list(list(EXPECTED_RECORDS.keys()))
        and norm_list(list(defects.keys())) == norm_list(list(EXPECTED_DEFECTS.keys()))
        and norm_list(list(sources.keys())) == norm_list(list(EXPECTED_SOURCES.keys())),
        {
            "matter_id": "M-NVK-219",
            "hold_date": "2024-11-25",
            "record_issue_ids": sorted(EXPECTED_RECORDS),
            "defect_ids": sorted(EXPECTED_DEFECTS),
            "source_ids": sorted(EXPECTED_SOURCES),
        },
        {
            "matter_id": candidate.get("matter_id"),
            "hold_date": candidate.get("hold_date"),
            "record_issue_ids": sorted(records),
            "defect_ids": sorted(defects),
            "source_ids": sorted(sources),
        },
    )

    add_result(
        details,
        "pre_hold_2019_lab_policy_destruction",
        2,
        dict_subset_match(records.get("RC-2019-LAB", {}), EXPECTED_RECORDS["RC-2019-LAB"]),
        EXPECTED_RECORDS["RC-2019-LAB"],
        records.get("RC-2019-LAB", {}),
    )

    add_result(
        details,
        "post_hold_ehs_box_spoliation",
        3,
        dict_subset_match(records.get("RC-EHS-BOX", {}), EXPECTED_RECORDS["RC-EHS-BOX"]),
        EXPECTED_RECORDS["RC-EHS-BOX"],
        records.get("RC-EHS-BOX", {}),
    )

    add_result(
        details,
        "voicemail_and_teams_source_gaps",
        2,
        dict_subset_match(records.get("RC-TEAMS-VOICE", {}), EXPECTED_RECORDS["RC-TEAMS-VOICE"]),
        EXPECTED_RECORDS["RC-TEAMS-VOICE"],
        records.get("RC-TEAMS-VOICE", {}),
    )

    archive_passed = dict_subset_match(
        records.get("RC-EMAIL-ARCHIVE", {}), EXPECTED_RECORDS["RC-EMAIL-ARCHIVE"]
    ) and dict_subset_match(sources.get("RS-EMAIL-IRONVAULT", {}), EXPECTED_SOURCES["RS-EMAIL-IRONVAULT"])
    add_result(
        details,
        "ironvault_seven_year_archive",
        2,
        archive_passed,
        {
            "record": EXPECTED_RECORDS["RC-EMAIL-ARCHIVE"],
            "source": EXPECTED_SOURCES["RS-EMAIL-IRONVAULT"],
        },
        {
            "record": records.get("RC-EMAIL-ARCHIVE", {}),
            "source": sources.get("RS-EMAIL-IRONVAULT", {}),
        },
    )

    audit_passed = dict_subset_match(
        records.get("RC-AUDIT-OCT2023", {}), EXPECTED_RECORDS["RC-AUDIT-OCT2023"]
    ) and dict_subset_match(sources.get("RS-AUDIT-VENDOR", {}), EXPECTED_SOURCES["RS-AUDIT-VENDOR"])
    add_result(
        details,
        "missing_october_2023_audit_retained",
        2,
        audit_passed,
        {
            "record": EXPECTED_RECORDS["RC-AUDIT-OCT2023"],
            "source": EXPECTED_SOURCES["RS-AUDIT-VENDOR"],
        },
        {
            "record": records.get("RC-AUDIT-OCT2023", {}),
            "source": sources.get("RS-AUDIT-VENDOR", {}),
        },
    )

    defects_passed = all(
        dict_subset_match(defects.get(defect_id, {}), expected) for defect_id, expected in EXPECTED_DEFECTS.items()
    )
    add_result(
        details,
        "personal_device_and_offsite_hold_defects",
        3,
        defects_passed,
        EXPECTED_DEFECTS,
        defects,
    )

    observed_plan = remediation_observed(candidate)
    expected_plan = remediation_expected()
    add_result(
        details,
        "remediation_action_ranking",
        2,
        observed_plan == expected_plan,
        expected_plan,
        observed_plan,
    )

    overall_observed = {
        "disclosure_required": overall.get("disclosure_required"),
        "blocked_category_ids": norm_list(overall.get("blocked_category_ids")),
        "policy_gap_category_ids": norm_list(overall.get("policy_gap_category_ids")),
        "post_hold_spoliation_issue_ids": norm_list(overall.get("post_hold_spoliation_issue_ids")),
    }
    overall_expected = {
        "disclosure_required": True,
        "blocked_category_ids": norm_list(EXPECTED_OVERALL["blocked_category_ids"]),
        "policy_gap_category_ids": norm_list(EXPECTED_OVERALL["policy_gap_category_ids"]),
        "post_hold_spoliation_issue_ids": norm_list(EXPECTED_OVERALL["post_hold_spoliation_issue_ids"]),
    }
    add_result(
        details,
        "overall_disclosure_and_category_status",
        1,
        overall_observed == overall_expected,
        overall_expected,
        overall_observed,
    )

    earned = sum(item["earned"] for item in details)
    max_points = sum(item["weight"] for item in details)
    normalized = earned / max_points if max_points else 0.0
    return {
        "score": round(normalized, 6),
        "earned_points": earned,
        "max_points": max_points,
        "passed": earned == max_points,
        "details": details,
    }


def main() -> None:
    candidate_path = (
        sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    )
    try:
        candidate = load_json(candidate_path)
        if not isinstance(candidate, dict):
            raise ValueError("prediction root must be a JSON object")
        result = evaluate(candidate)
    except Exception as exc:
        result = {
            "score": 0.0,
            "earned_points": 0,
            "max_points": 18,
            "passed": False,
            "error": str(exc),
            "details": [],
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
