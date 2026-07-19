#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


RUBRIC = [
    {
        "id": "P01_matter_and_event_coverage",
        "weight": 1,
        "goal": "Identifies the Portola matter and the complete target retention-event set.",
    },
    {
        "id": "P02_trade_blotter_pre_hold_policy_classification",
        "weight": 2,
        "goal": "Correctly classifies the 2018 trade blotter destruction as low-risk pre-hold policy destruction under the 72-month schedule.",
    },
    {
        "id": "P03_chat_export_post_hold_loss",
        "weight": 3,
        "goal": "Correctly treats the deleted deal-chat exports as a high-risk post-hold loss with the right volume, categories, communication-gap entry, and disclosure action.",
    },
    {
        "id": "P04_voice_auto_purge_gap",
        "weight": 2,
        "goal": "Correctly identifies trader voicemail as a 120-day auto-purge communication gap affecting category PE-D.",
    },
    {
        "id": "P05_energycomms_archive_exception",
        "weight": 2,
        "goal": "Correctly identifies the EnergyComms chat archive as an available archive for chat attachments affecting PE-D and PE-E.",
    },
    {
        "id": "P06_missing_surveillance_report",
        "weight": 3,
        "goal": "Correctly treats the 2024 surveillance report as a required missing record with the right retention period, categories, and locate action.",
    },
    {
        "id": "P07_metrics",
        "weight": 2,
        "goal": "Reports the required numeric counts and affected-category sets.",
    },
    {
        "id": "P08_action_ranking",
        "weight": 3,
        "goal": "Ranks the preservation disclosure, missing-report search, archive collection, voicemail documentation, and pre-hold policy-loss disposition in the correct operational order.",
    },
]

EXPECTED_EVENT_IDS = {
    "RET-PORT-AUDIT-MISSING",
    "RET-PORT-CHAT-POST",
    "RET-PORT-TRADE-2018",
    "RET-PORT-VOICE",
}


def load_json(path: str):
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def as_str(value):
    if value is None:
        return ""
    return str(value).strip()


def norm_id(value):
    return as_str(value).upper()


def norm_enum(value):
    return as_str(value).lower()


def norm_set(values):
    if not isinstance(values, list):
        return set()
    return {norm_id(value) for value in values if as_str(value)}


def int_value(value):
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip().replace(",", "")
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
    return None


def list_by_id(answer, list_name, id_key):
    rows = answer.get(list_name, [])
    if not isinstance(rows, list):
        return {}
    indexed = {}
    for row in rows:
        if isinstance(row, dict):
            key = norm_id(row.get(id_key))
            if key:
                indexed[key] = row
    return indexed


def event(answer, event_id):
    return list_by_id(answer, "retention_events", "event_id").get(event_id)


def gap(answer, event_id):
    return list_by_id(answer, "communication_gaps", "event_id").get(event_id)


def archive(answer, source_id):
    return list_by_id(answer, "available_archives", "source_id").get(source_id)


def action_by_target(answer):
    return list_by_id(answer, "recommended_actions", "target_id")


def has_action(
    answer,
    target_id,
    action_type=None,
    owner=None,
    categories=None,
    priority_rank=None,
    max_priority=None,
    risk_level=None,
):
    row = action_by_target(answer).get(target_id)
    if not isinstance(row, dict):
        return False
    if action_type is not None and norm_enum(row.get("action_type")) != action_type:
        return False
    if owner is not None and norm_enum(row.get("owner")) != owner:
        return False
    if categories is not None and norm_set(row.get("affected_categories")) != set(categories):
        return False
    if risk_level is not None and norm_enum(row.get("risk_level")) != risk_level:
        return False
    priority = int_value(row.get("priority_rank"))
    if priority_rank is not None and priority != priority_rank:
        return False
    if max_priority is not None and (priority is None or priority > max_priority):
        return False
    return True


def check_p01(answer):
    events = set(list_by_id(answer, "retention_events", "event_id").keys())
    passed = answer.get("matter_id") == "MTR-PORTOLA-GJ" and events == EXPECTED_EVENT_IDS
    return passed, {
        "matter_id": answer.get("matter_id"),
        "retention_event_ids": sorted(events),
        "expected_event_ids": sorted(EXPECTED_EVENT_IDS),
    }


def check_p02(answer):
    row = event(answer, "RET-PORT-TRADE-2018")
    passed = isinstance(row, dict) and all(
        [
            norm_enum(row.get("status")) == "policy_destroyed_pre_hold",
            norm_enum(row.get("risk_level")) == "low",
            norm_set(row.get("affected_categories")) == {"PE-B"},
            as_str(row.get("event_date")) == "2024-11-30",
            as_str(row.get("hold_date")) == "2025-01-09",
            as_str(row.get("policy_section")) == "2.7",
            int_value(row.get("retention_period_months")) == 72,
            int_value(row.get("volume_count")) == 12,
            norm_enum(row.get("volume_unit")) == "monthly_blotters",
        ]
    )
    return passed, {
        "event": row,
        "expected": {
            "status": "policy_destroyed_pre_hold",
            "risk_level": "low",
            "affected_categories": ["PE-B"],
            "event_date": "2024-11-30",
            "hold_date": "2025-01-09",
            "policy_section": "2.7",
            "retention_period_months": 72,
            "volume_count": 12,
            "volume_unit": "monthly_blotters",
        },
    }


def check_p03(answer):
    row = event(answer, "RET-PORT-CHAT-POST")
    comm_gap = gap(answer, "RET-PORT-CHAT-POST")
    event_ok = isinstance(row, dict) and all(
        [
            norm_enum(row.get("status")) == "post_hold_loss",
            norm_enum(row.get("risk_level")) == "high",
            norm_set(row.get("affected_categories")) == {"PE-D", "PE-E"},
            as_str(row.get("event_date")) == "2025-02-04",
            as_str(row.get("hold_date")) == "2025-01-09",
            as_str(row.get("policy_section")) == "6.2",
            int_value(row.get("retention_period_months")) == 60,
            int_value(row.get("volume_count")) == 18,
            norm_enum(row.get("volume_unit")) == "exports",
        ]
    )
    gap_ok = isinstance(comm_gap, dict) and all(
        [
            norm_enum(comm_gap.get("gap_type")) == "post_hold_deleted_export",
            norm_enum(comm_gap.get("status")) == "post_hold_loss",
            norm_enum(comm_gap.get("risk_level")) == "high",
            norm_set(comm_gap.get("affected_categories")) == {"PE-D", "PE-E"},
            int_value(comm_gap.get("volume_count")) == 18,
            norm_enum(comm_gap.get("volume_unit")) == "exports",
            norm_id(comm_gap.get("archive_exception_source_id")) == "SRC-PORT-ENERGYCOMMS",
        ]
    )
    action_ok = has_action(
        answer,
        "RET-PORT-CHAT-POST",
        action_type="disclose_preservation_issue",
        owner="litigation_counsel",
        categories={"PE-D", "PE-E"},
        risk_level="high",
    )
    return event_ok and gap_ok and action_ok, {
        "event": row,
        "communication_gap": comm_gap,
        "action_ok": action_ok,
        "expected": {
            "status": "post_hold_loss",
            "risk_level": "high",
            "affected_categories": ["PE-D", "PE-E"],
            "event_date": "2025-02-04",
            "hold_date": "2025-01-09",
            "volume_count": 18,
            "volume_unit": "exports",
            "gap_type": "post_hold_deleted_export",
            "archive_exception_source_id": "SRC-PORT-ENERGYCOMMS",
            "action_type": "disclose_preservation_issue",
            "owner": "litigation_counsel",
        },
    }


def check_p04(answer):
    row = event(answer, "RET-PORT-VOICE")
    comm_gap = gap(answer, "RET-PORT-VOICE")
    event_ok = isinstance(row, dict) and all(
        [
            norm_enum(row.get("status")) == "auto_purged",
            norm_enum(row.get("risk_level")) == "medium",
            norm_set(row.get("affected_categories")) == {"PE-D"},
            as_str(row.get("event_date")) == "2025-03-11",
            as_str(row.get("hold_date")) == "2025-01-09",
            as_str(row.get("policy_section")) == "7.4",
            int_value(row.get("retention_period_months")) == 4,
            int_value(row.get("volume_count")) == 120,
            norm_enum(row.get("volume_unit")) == "days",
        ]
    )
    gap_ok = isinstance(comm_gap, dict) and all(
        [
            norm_enum(comm_gap.get("gap_type")) == "auto_purge",
            norm_enum(comm_gap.get("status")) == "auto_purged",
            norm_enum(comm_gap.get("risk_level")) == "medium",
            norm_set(comm_gap.get("affected_categories")) == {"PE-D"},
            int_value(comm_gap.get("purge_window_days")) == 120,
            int_value(comm_gap.get("volume_count")) == 120,
            norm_enum(comm_gap.get("volume_unit")) == "days",
        ]
    )
    return event_ok and gap_ok, {
        "event": row,
        "communication_gap": comm_gap,
        "expected": {
            "status": "auto_purged",
            "risk_level": "medium",
            "affected_categories": ["PE-D"],
            "event_date": "2025-03-11",
            "hold_date": "2025-01-09",
            "retention_period_months": 4,
            "volume_count": 120,
            "volume_unit": "days",
            "purge_window_days": 120,
        },
    }


def check_p05(answer):
    row = archive(answer, "SRC-PORT-ENERGYCOMMS")
    action_ok = has_action(
        answer,
        "SRC-PORT-ENERGYCOMMS",
        action_type="collect_archive",
        owner="ediscovery_vendor",
        categories={"PE-D", "PE-E"},
        risk_level="medium",
    )
    passed = isinstance(row, dict) and all(
        [
            norm_enum(row.get("archive_status")) == "available_archive",
            norm_enum(row.get("source_type")) == "chat_archive",
            norm_enum(row.get("available_content")) == "chat_attachments",
            norm_set(row.get("affected_categories")) == {"PE-D", "PE-E"},
            norm_set(row.get("limits_irretrievable_loss_for_categories")) == {"PE-D", "PE-E"},
            norm_enum(row.get("action_type")) == "collect_archive",
            norm_enum(row.get("owner")) == "ediscovery_vendor",
            action_ok,
        ]
    )
    return passed, {
        "archive": row,
        "action_ok": action_ok,
        "expected": {
            "source_id": "SRC-PORT-ENERGYCOMMS",
            "archive_status": "available_archive",
            "source_type": "chat_archive",
            "available_content": "chat_attachments",
            "affected_categories": ["PE-D", "PE-E"],
            "limits_irretrievable_loss_for_categories": ["PE-D", "PE-E"],
            "action_type": "collect_archive",
            "owner": "ediscovery_vendor",
        },
    }


def check_p06(answer):
    row = event(answer, "RET-PORT-AUDIT-MISSING")
    action_ok = has_action(
        answer,
        "RET-PORT-AUDIT-MISSING",
        action_type="locate_missing_record",
        owner="compliance_audit",
        categories={"PE-F", "PE-I"},
        risk_level="high",
        max_priority=2,
    )
    passed = isinstance(row, dict) and all(
        [
            norm_enum(row.get("status")) == "should_exist_missing",
            norm_enum(row.get("risk_level")) == "high",
            norm_set(row.get("affected_categories")) == {"PE-F", "PE-I"},
            as_str(row.get("event_date")) == "2024-12-31",
            as_str(row.get("hold_date")) == "2025-01-09",
            as_str(row.get("policy_section")) == "5.8",
            int_value(row.get("retention_period_months")) == 60,
            int_value(row.get("volume_count")) == 1,
            norm_enum(row.get("volume_unit")) == "report",
            action_ok,
        ]
    )
    return passed, {
        "event": row,
        "action_ok": action_ok,
        "expected": {
            "status": "should_exist_missing",
            "risk_level": "high",
            "affected_categories": ["PE-F", "PE-I"],
            "event_date": "2024-12-31",
            "hold_date": "2025-01-09",
            "policy_section": "5.8",
            "retention_period_months": 60,
            "volume_count": 1,
            "volume_unit": "report",
            "action": {
                "target_id": "RET-PORT-AUDIT-MISSING",
                "action_type": "locate_missing_record",
                "owner": "compliance_audit",
                "max_priority_rank": 2,
            },
        },
    }


def check_p07(answer):
    metrics = answer.get("metrics", {})
    expected_counts = {
        "retention_event_count": 4,
        "pre_hold_policy_destroyed_event_count": 1,
        "post_hold_loss_event_count": 1,
        "communication_gap_event_count": 2,
        "should_exist_missing_event_count": 1,
        "available_archive_count": 1,
        "pre_hold_destroyed_monthly_blotter_count": 12,
        "post_hold_deleted_export_count": 18,
        "auto_purge_window_days": 120,
        "missing_required_report_count": 1,
        "unique_affected_category_count": 5,
    }
    counts_ok = isinstance(metrics, dict) and all(
        int_value(metrics.get(key)) == value for key, value in expected_counts.items()
    )
    categories_ok = isinstance(metrics, dict) and norm_set(metrics.get("categories_with_any_gap_or_loss")) == {
        "PE-B",
        "PE-D",
        "PE-E",
        "PE-F",
        "PE-I",
    }
    archive_categories_ok = isinstance(metrics, dict) and norm_set(
        metrics.get("categories_with_archive_exception")
    ) == {
        "PE-D",
        "PE-E",
    }
    return counts_ok and categories_ok and archive_categories_ok, {
        "metrics": metrics,
        "expected_counts": expected_counts,
        "expected_categories_with_any_gap_or_loss": ["PE-B", "PE-D", "PE-E", "PE-F", "PE-I"],
        "expected_categories_with_archive_exception": ["PE-D", "PE-E"],
    }


def check_p08(answer):
    required_actions = [
        ("RET-PORT-CHAT-POST", "disclose_preservation_issue", "litigation_counsel", {"PE-D", "PE-E"}, 1, "high"),
        ("RET-PORT-AUDIT-MISSING", "locate_missing_record", "compliance_audit", {"PE-F", "PE-I"}, 2, "high"),
        ("SRC-PORT-ENERGYCOMMS", "collect_archive", "ediscovery_vendor", {"PE-D", "PE-E"}, 3, "medium"),
        ("RET-PORT-VOICE", "document_system_gap", "it_messaging", {"PE-D"}, 4, "medium"),
        ("RET-PORT-TRADE-2018", "no_action_policy_loss", "records_management", {"PE-B"}, 5, "low"),
    ]
    action_checks = [
        has_action(answer, target, action, owner, categories, rank, risk_level=risk)
        for target, action, owner, categories, rank, risk in required_actions
    ]
    priorities = []
    duplicate_rank = False
    seen_ranks = set()
    for row in answer.get("recommended_actions", []):
        if not isinstance(row, dict):
            continue
        rank = int_value(row.get("priority_rank"))
        if rank is None:
            continue
        if rank in seen_ranks:
            duplicate_rank = True
        seen_ranks.add(rank)
        if norm_id(row.get("target_id")) in {item[0] for item in required_actions}:
            priorities.append((norm_id(row.get("target_id")), rank))
    passed = all(action_checks) and not duplicate_rank
    return passed, {
        "action_checks": dict(zip([item[0] for item in required_actions], action_checks)),
        "priorities": sorted(priorities, key=lambda item: item[1]),
        "duplicate_rank": duplicate_rank,
        "expected_required_actions": [
            {
                "target_id": target,
                "action_type": action,
                "owner": owner,
                "affected_categories": sorted(categories),
                "priority_rank": rank,
                "risk_level": risk,
            }
            for target, action, owner, categories, rank, risk in required_actions
        ],
    }


CHECKS = {
    "P01_matter_and_event_coverage": check_p01,
    "P02_trade_blotter_pre_hold_policy_classification": check_p02,
    "P03_chat_export_post_hold_loss": check_p03,
    "P04_voice_auto_purge_gap": check_p04,
    "P05_energycomms_archive_exception": check_p05,
    "P06_missing_surveillance_report": check_p06,
    "P07_metrics": check_p07,
    "P08_action_ranking": check_p08,
}


def evaluate(answer):
    total_weight = sum(point["weight"] for point in RUBRIC)
    points = []
    score = 0.0
    for point in RUBRIC:
        assigned = point["weight"] / total_weight
        try:
            passed, details = CHECKS[point["id"]](answer)
        except Exception as exc:
            passed = False
            details = {"error": f"{type(exc).__name__}: {exc}"}
        earned = assigned if passed else 0.0
        score += earned
        points.append(
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": round(assigned, 10),
                "passed": bool(passed),
                "earned_score": round(earned, 10),
                "details": details,
            }
        )
    score = round(score, 10)
    return {"score": score, "correct": score == 1.0, "points": points}


def failure_result(error):
    total_weight = sum(point["weight"] for point in RUBRIC)
    return {
        "score": 0.0,
        "correct": False,
        "points": [
            {
                "id": point["id"],
                "goal": point["goal"],
                "weight": point["weight"],
                "assigned_score": round(point["weight"] / total_weight, 10),
                "passed": False,
                "earned_score": 0.0,
                "details": {"error": error},
            }
            for point in RUBRIC
        ],
    }


def main():
    candidate = (
        sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    )
    try:
        answer = load_json(candidate)
        if not isinstance(answer, dict):
            raise ValueError("top-level JSON value must be an object")
        result = evaluate(answer)
    except Exception as exc:
        result = failure_result(f"{type(exc).__name__}: {exc}")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
