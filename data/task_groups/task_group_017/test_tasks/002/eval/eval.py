#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXPECTED_RECORDS = {
    "RC-2020-LAB": {
        "record_classes": ["2020 emissions lab data"],
        "category_ids": ["B-01"],
        "timing_class": "pre_hold_policy",
        "severity": "medium",
        "quantity": 6,
        "event_date": "2023-01-27",
        "source_event_ids": ["CE-0019", "DE-0008", "RR-0011"],
        "primary_action": "no_action_policy_gap",
        "notice_required": False,
    },
    "RC-EMAIL-VAULTSEVEN": {
        "record_classes": ["executive email"],
        "category_ids": ["B-03"],
        "timing_class": "recoverable_archive",
        "severity": "low",
        "quantity": 9220,
        "event_date": "2025-01-14",
        "source_event_ids": ["CE-0021", "RR-0013"],
        "primary_action": "supplemental_collection",
        "notice_required": False,
    },
    "RC-TEAMS-PURGE": {
        "record_classes": ["Teams channels"],
        "category_ids": ["B-02"],
        "timing_class": "post_hold_spoliation",
        "severity": "critical",
        "quantity": 11,
        "event_date": "2025-02-05",
        "source_event_ids": ["CE-0020", "DE-0009", "RR-0012"],
        "primary_action": "regulator_notice",
        "notice_required": True,
    },
    "RC-TIDEWATER-AUDIT": {
        "record_classes": ["2024 Tidewater audit report"],
        "category_ids": ["B-04"],
        "timing_class": "retained_missing",
        "severity": "high",
        "quantity": 1,
        "event_date": "2025-01-22",
        "source_event_ids": ["CE-0022", "PL-0026", "RR-0014"],
        "primary_action": "vendor_retrieval",
        "notice_required": False,
    },
}

EXPECTED_DEFECTS = {
    "HD-OFFSITE-VENDOR": {
        "defect_type": "offsite_vendor_not_on_hold",
        "category_ids": ["B-05"],
        "affected_sources": ["off-site vendor boxes"],
        "severity": "high",
        "source_event_ids": ["CE-0023", "PL-0027"],
        "primary_action": "hold_refresh",
        "notice_required": False,
    },
    "HD-PERSONAL-DEVICE": {
        "defect_type": "personal_device_notice_omission",
        "category_ids": ["B-05"],
        "affected_sources": ["personal phone"],
        "severity": "high",
        "source_event_ids": ["CE-0023", "PL-0027"],
        "primary_action": "supplemental_collection",
        "notice_required": False,
    },
}

EXPECTED_SOURCES = {
    "RS-AUDIT-TIDEWATER": {
        "source_name": "Tidewater audit vendor copy",
        "record_class": "2024 Tidewater audit report",
        "category_ids": ["B-04"],
        "recovery_status": "retained_missing",
        "count": 1,
        "source_event_ids": ["CE-0022", "RR-0014"],
        "primary_action": "vendor_retrieval",
    },
    "RS-EMAIL-VAULTSEVEN": {
        "source_name": "VaultSeven executive archive",
        "record_class": "executive email",
        "category_ids": ["B-03"],
        "recovery_status": "available",
        "count": 9220,
        "source_event_ids": ["CE-0021", "RR-0013"],
        "primary_action": "supplemental_collection",
    },
    "RS-LAB-SUMMARY-EXPORTS": {
        "source_name": "summary exports",
        "record_class": "2020 emissions lab data",
        "category_ids": ["B-01"],
        "recovery_status": "partial",
        "count": 0,
        "source_event_ids": ["DE-0008"],
        "primary_action": "supplemental_collection",
    },
}

EXPECTED_REMEDIATION = [
    {
        "rank": 1,
        "action_id": "RA-REGULATOR-NOTICE",
        "action": "regulator_notice",
        "issue_ids": ["RC-TEAMS-PURGE"],
        "owner_queue": "legal",
    },
    {
        "rank": 2,
        "action_id": "RA-AUDIT-RETRIEVAL",
        "action": "vendor_retrieval",
        "issue_ids": ["RC-TIDEWATER-AUDIT"],
        "owner_queue": "records",
    },
    {
        "rank": 3,
        "action_id": "RA-HOLD-REFRESH",
        "action": "hold_refresh",
        "issue_ids": ["HD-OFFSITE-VENDOR", "HD-PERSONAL-DEVICE"],
        "owner_queue": "litigation_support",
    },
    {
        "rank": 4,
        "action_id": "RA-SUPPLEMENTAL-COLLECTION",
        "action": "supplemental_collection",
        "issue_ids": ["HD-OFFSITE-VENDOR", "HD-PERSONAL-DEVICE", "RC-EMAIL-VAULTSEVEN"],
        "owner_queue": "e_discovery",
    },
    {
        "rank": 5,
        "action_id": "RA-POLICY-GAP-LOG",
        "action": "no_action_policy_gap",
        "issue_ids": ["RC-2020-LAB"],
        "owner_queue": "records",
    },
]

EXPECTED_OVERALL = {
    "disclosure_required": True,
    "blocked_category_ids": ["B-02", "B-04", "B-05"],
    "policy_gap_category_ids": ["B-01"],
    "post_hold_spoliation_issue_ids": ["RC-TEAMS-PURGE"],
}


def load_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


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


def text_equiv(actual: Any, expected: str) -> bool:
    actual_text = as_string(actual).lower()
    expected_text = expected.lower()
    return actual_text == expected_text or actual_text in expected_text or expected_text in actual_text


def list_contains(actual: Any, expected: list[Any]) -> bool:
    if not isinstance(actual, list):
        return False
    actual_norm = set(norm_list(actual))
    return all(norm_scalar(item) in actual_norm for item in expected)


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
        if key in {"record_classes", "affected_sources", "source_event_ids"}:
            continue
        actual = row.get(key)
        if isinstance(exp_value, list):
            if key in {"record_classes", "affected_sources"}:
                actual_list = actual if isinstance(actual, list) else []
                if len(actual_list) != len(exp_value):
                    return False
                if not all(any(text_equiv(a, e) for a in actual_list) for e in exp_value):
                    return False
            elif norm_list(actual) != norm_list(exp_value):
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


def semantic_record(records: dict[str, dict[str, Any]], expected_id: str) -> dict[str, Any]:
    if expected_id in records:
        return records[expected_id]
    expected = EXPECTED_RECORDS[expected_id]
    for row in records.values():
        if not isinstance(row, dict):
            continue
        if (
            norm_list(row.get("category_ids")) == norm_list(expected["category_ids"])
            and row.get("timing_class") == expected["timing_class"]
            and row.get("primary_action") == expected["primary_action"]
        ):
            return row
    return {}


def semantic_defect(defects: dict[str, dict[str, Any]], expected_id: str) -> dict[str, Any]:
    if expected_id in defects:
        return defects[expected_id]
    expected = EXPECTED_DEFECTS[expected_id]
    for row in defects.values():
        if row.get("defect_type") == expected["defect_type"]:
            return row
    return {}


def semantic_source(sources: dict[str, dict[str, Any]], expected_id: str) -> dict[str, Any]:
    if expected_id in sources:
        return sources[expected_id]
    expected = EXPECTED_SOURCES[expected_id]
    for row in sources.values():
        if text_equiv(row.get("source_name"), expected["source_name"]):
            return row
    return {}


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
                "action": as_string(row.get("action")),
                "owner_queue": as_string(row.get("owner_queue")),
            }
        )
    return sorted(normalized, key=lambda item: int(item["rank"]) if str(item["rank"]).isdigit() else 999)


def remediation_expected() -> list[dict[str, Any]]:
    return [
        {
            "rank": row["rank"],
            "action": row["action"],
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
        candidate.get("matter_id") == "M-BAY-144"
        and candidate.get("hold_date") == "2024-12-06"
        and all(semantic_record(records, record_id) for record_id in EXPECTED_RECORDS)
        and all(semantic_defect(defects, defect_id) for defect_id in EXPECTED_DEFECTS)
        and all(semantic_source(sources, source_id) for source_id in EXPECTED_SOURCES),
        {
            "matter_id": "M-BAY-144",
            "hold_date": "2024-12-06",
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
        "pre_hold_2020_lab_policy_destruction",
        2,
        dict_subset_match(semantic_record(records, "RC-2020-LAB"), EXPECTED_RECORDS["RC-2020-LAB"]),
        EXPECTED_RECORDS["RC-2020-LAB"],
        semantic_record(records, "RC-2020-LAB"),
    )

    add_result(
        details,
        "post_hold_teams_purge_spoliation",
        3,
        dict_subset_match(semantic_record(records, "RC-TEAMS-PURGE"), EXPECTED_RECORDS["RC-TEAMS-PURGE"]),
        EXPECTED_RECORDS["RC-TEAMS-PURGE"],
        semantic_record(records, "RC-TEAMS-PURGE"),
    )

    archive_passed = dict_subset_match(
        semantic_record(records, "RC-EMAIL-VAULTSEVEN"), EXPECTED_RECORDS["RC-EMAIL-VAULTSEVEN"]
    ) and dict_subset_match(semantic_source(sources, "RS-EMAIL-VAULTSEVEN"), EXPECTED_SOURCES["RS-EMAIL-VAULTSEVEN"])
    add_result(
        details,
        "vaultseven_executive_email_archive",
        2,
        archive_passed,
        {
            "record": EXPECTED_RECORDS["RC-EMAIL-VAULTSEVEN"],
            "source": EXPECTED_SOURCES["RS-EMAIL-VAULTSEVEN"],
        },
        {
            "record": semantic_record(records, "RC-EMAIL-VAULTSEVEN"),
            "source": semantic_source(sources, "RS-EMAIL-VAULTSEVEN"),
        },
    )

    audit_passed = dict_subset_match(
        semantic_record(records, "RC-TIDEWATER-AUDIT"), EXPECTED_RECORDS["RC-TIDEWATER-AUDIT"]
    ) and dict_subset_match(semantic_source(sources, "RS-AUDIT-TIDEWATER"), EXPECTED_SOURCES["RS-AUDIT-TIDEWATER"])
    add_result(
        details,
        "missing_2024_tidewater_audit_retained_vendor_copy",
        2,
        audit_passed,
        {
            "record": EXPECTED_RECORDS["RC-TIDEWATER-AUDIT"],
            "source": EXPECTED_SOURCES["RS-AUDIT-TIDEWATER"],
        },
        {
            "record": semantic_record(records, "RC-TIDEWATER-AUDIT"),
            "source": semantic_source(sources, "RS-AUDIT-TIDEWATER"),
        },
    )

    add_result(
        details,
        "lab_summary_exports_partial_recovery_source",
        1,
        dict_subset_match(
            semantic_source(sources, "RS-LAB-SUMMARY-EXPORTS"), EXPECTED_SOURCES["RS-LAB-SUMMARY-EXPORTS"]
        ),
        EXPECTED_SOURCES["RS-LAB-SUMMARY-EXPORTS"],
        semantic_source(sources, "RS-LAB-SUMMARY-EXPORTS"),
    )

    defects_passed = all(
        dict_subset_match(semantic_defect(defects, defect_id), expected)
        for defect_id, expected in EXPECTED_DEFECTS.items()
    )
    add_result(
        details,
        "offsite_vendor_and_personal_device_hold_omissions",
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
        "post_hold_spoliation_issue_ids": [
            "RC-TEAMS-PURGE"
            for item in norm_list(overall.get("post_hold_spoliation_issue_ids"))
            if "TEAMS" in str(item).upper()
        ],
    }
    overall_expected = {
        "disclosure_required": EXPECTED_OVERALL["disclosure_required"],
        "blocked_category_ids": norm_list(EXPECTED_OVERALL["blocked_category_ids"]),
        "policy_gap_category_ids": norm_list(EXPECTED_OVERALL["policy_gap_category_ids"]),
        "post_hold_spoliation_issue_ids": norm_list(EXPECTED_OVERALL["post_hold_spoliation_issue_ids"]),
    }
    add_result(
        details,
        "overall_disclosure_and_category_status",
        2,
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
