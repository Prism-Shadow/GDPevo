#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


RUBRIC = [
    {
        "id": "P01_matter_and_event_coverage",
        "weight": 1,
        "goal": "Identifies the HarborStone matter and the complete target retention-event set.",
    },
    {
        "id": "P02_pre_hold_policy_destruction",
        "weight": 2,
        "goal": "Correctly classifies the 2019 lab data boxes as pre-hold policy destruction under policy section 3.1.",
    },
    {
        "id": "P03_post_hold_loss",
        "weight": 3,
        "goal": "Correctly classifies the EHS correspondence destruction as a high-risk post-hold loss with the right timing, volume, and affected categories.",
    },
    {
        "id": "P04_communication_gaps",
        "weight": 2,
        "goal": "Correctly identifies voicemail auto-purge and Teams active-system loss as separate communication gaps.",
    },
    {
        "id": "P05_missing_audit_retention",
        "weight": 3,
        "goal": "Correctly treats the October 2023 Calverley audit as a required record that should still exist under a 60-month retention period.",
    },
    {
        "id": "P06_archive_exception",
        "weight": 2,
        "goal": "Correctly identifies IronVault as an available seven-year email archive affecting categories D and E.",
    },
    {
        "id": "P07_metrics",
        "weight": 2,
        "goal": "Reports the required numeric counts and unique affected-category set.",
    },
    {
        "id": "P08_recommended_actions",
        "weight": 2,
        "goal": "Provides the correct prioritized action and owner set for the preservation loss, missing audit, archive collection, system gaps, and policy-compliant loss.",
    },
]

EXPECTED_EVENT_IDS = {
    "RET-HARB-LAB-2019",
    "RET-HARB-EHS-POST",
    "RET-HARB-VOICE",
    "RET-HARB-TEAMS",
    "RET-HARB-AUDIT",
}


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


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
    return {as_str(v).upper() for v in values if as_str(v)}


def int_value(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
            return int(text)
    return None


def list_by_id(answer, list_name, id_key):
    rows = answer.get(list_name, [])
    if not isinstance(rows, list):
        return {}
    result = {}
    for row in rows:
        if isinstance(row, dict):
            key = norm_id(row.get(id_key))
            if key:
                result[key] = row
    return result


def action_by_target(answer):
    return list_by_id(answer, "recommended_actions", "target_id")


def has_action(answer, target_id, action_type=None, owner=None, categories=None, max_priority=None):
    row = action_by_target(answer).get(target_id)
    if not isinstance(row, dict):
        return False
    if action_type is not None and norm_enum(row.get("action_type")) != action_type:
        return False
    if owner is not None and norm_enum(row.get("owner")) != owner:
        return False
    if categories is not None and norm_set(row.get("affected_categories")) != set(categories):
        return False
    if max_priority is not None:
        priority = int_value(row.get("priority_rank"))
        if priority is None or priority > max_priority:
            return False
    return True


def event(answer, event_id):
    return list_by_id(answer, "retention_events", "event_id").get(event_id)


def gap(answer, event_id):
    return list_by_id(answer, "communication_gaps", "event_id").get(event_id)


def archive(answer, source_id):
    return list_by_id(answer, "available_archives", "source_id").get(source_id)


def check_p01(answer):
    events = set(list_by_id(answer, "retention_events", "event_id").keys())
    passed = answer.get("matter_id") == "MTR-HARBORSTONE-GJ" and events == EXPECTED_EVENT_IDS
    return passed, {
        "matter_id": answer.get("matter_id"),
        "retention_event_ids": sorted(events),
        "expected_event_ids": sorted(EXPECTED_EVENT_IDS),
    }


def check_p02(answer):
    row = event(answer, "RET-HARB-LAB-2019")
    passed = isinstance(row, dict) and all(
        [
            norm_enum(row.get("status")) == "policy_destroyed_pre_hold",
            norm_enum(row.get("risk_level")) == "low",
            norm_set(row.get("affected_categories")) == {"B"},
            int_value(row.get("volume_count")) == 4,
            norm_enum(row.get("volume_unit")) == "boxes",
            as_str(row.get("event_date")) == "2023-01-18",
            as_str(row.get("hold_date")) == "2024-11-14",
            as_str(row.get("policy_section")) == "3.1",
        ]
    )
    return passed, {
        "event": row,
        "expected": {
            "status": "policy_destroyed_pre_hold",
            "risk_level": "low",
            "affected_categories": ["B"],
            "volume_count": 4,
            "volume_unit": "boxes",
            "event_date": "2023-01-18",
            "hold_date": "2024-11-14",
            "policy_section": "3.1",
        },
    }


def check_p03(answer):
    row = event(answer, "RET-HARB-EHS-POST")
    passed = isinstance(row, dict) and all(
        [
            norm_enum(row.get("status")) == "post_hold_loss",
            norm_enum(row.get("risk_level")) == "high",
            norm_set(row.get("affected_categories")) == {"C", "D", "H"},
            int_value(row.get("volume_count")) == 2,
            norm_enum(row.get("volume_unit")) == "boxes",
            as_str(row.get("event_date")) == "2025-01-06",
            as_str(row.get("hold_date")) == "2024-11-14",
        ]
    )
    return passed, {
        "event": row,
        "expected": {
            "status": "post_hold_loss",
            "risk_level": "high",
            "affected_categories": ["C", "D", "H"],
            "volume_count": 2,
            "volume_unit": "boxes",
            "event_date": "2025-01-06",
            "hold_date": "2024-11-14",
        },
    }


def check_p04(answer):
    voice = gap(answer, "RET-HARB-VOICE")
    teams = gap(answer, "RET-HARB-TEAMS")
    voice_ok = isinstance(voice, dict) and all(
        [
            norm_enum(voice.get("gap_type")) == "auto_purge",
            norm_enum(voice.get("status")) == "auto_purged",
            norm_set(voice.get("affected_categories")) == {"D"},
            int_value(voice.get("purge_window_days")) == 90,
        ]
    )
    teams_ok = isinstance(teams, dict) and all(
        [
            norm_enum(teams.get("gap_type")) == "active_system_loss",
            norm_enum(teams.get("status")) == "active_system_loss",
            norm_set(teams.get("affected_categories")) == {"D", "E"},
            as_str(teams.get("cutoff_date")) == "2022-02-01",
        ]
    )
    return voice_ok and teams_ok, {
        "voice_gap": voice,
        "teams_gap": teams,
        "expected": {
            "RET-HARB-VOICE": {
                "gap_type": "auto_purge",
                "status": "auto_purged",
                "affected_categories": ["D"],
                "purge_window_days": 90,
            },
            "RET-HARB-TEAMS": {
                "gap_type": "active_system_loss",
                "status": "active_system_loss",
                "affected_categories": ["D", "E"],
                "cutoff_date": "2022-02-01",
            },
        },
    }


def check_p05(answer):
    row = event(answer, "RET-HARB-AUDIT")
    action_ok = has_action(
        answer,
        "RET-HARB-AUDIT",
        action_type="locate_missing_record",
        owner="compliance_audit",
        categories={"E", "F", "I"},
        max_priority=2,
    )
    passed = isinstance(row, dict) and all(
        [
            norm_enum(row.get("status")) == "should_exist_missing",
            norm_enum(row.get("risk_level")) == "high",
            norm_set(row.get("affected_categories")) == {"E", "F", "I"},
            int_value(row.get("retention_period_months")) == 60,
            action_ok,
        ]
    )
    return passed, {
        "event": row,
        "action_ok": action_ok,
        "expected": {
            "status": "should_exist_missing",
            "risk_level": "high",
            "affected_categories": ["E", "F", "I"],
            "retention_period_months": 60,
            "action": {
                "target_id": "RET-HARB-AUDIT",
                "action_type": "locate_missing_record",
                "owner": "compliance_audit",
                "max_priority_rank": 2,
            },
        },
    }


def check_p06(answer):
    row = archive(answer, "SRC-HARB-IRONVAULT")
    action_ok = has_action(
        answer,
        "SRC-HARB-IRONVAULT",
        action_type="collect_archive",
        owner="ediscovery_vendor",
        categories={"D", "E"},
    )
    passed = isinstance(row, dict) and all(
        [
            norm_enum(row.get("archive_status")) == "available_archive",
            int_value(row.get("retention_years")) == 7,
            norm_set(row.get("affected_categories")) == {"D", "E"},
            norm_set(row.get("limits_irretrievable_loss_for_categories")) == {"D", "E"},
            norm_enum(row.get("action_type")) == "collect_archive",
            norm_enum(row.get("owner")) == "ediscovery_vendor",
            action_ok,
        ]
    )
    return passed, {
        "archive": row,
        "action_ok": action_ok,
        "expected": {
            "source_id": "SRC-HARB-IRONVAULT",
            "archive_status": "available_archive",
            "retention_years": 7,
            "affected_categories": ["D", "E"],
            "action_type": "collect_archive",
            "owner": "ediscovery_vendor",
        },
    }


def check_p07(answer):
    metrics = answer.get("metrics", {})
    expected = {
        "retention_event_count": 5,
        "pre_hold_policy_destroyed_event_count": 1,
        "post_hold_loss_event_count": 1,
        "communication_gap_event_count": 2,
        "should_exist_missing_event_count": 1,
        "available_archive_count": 1,
        "destroyed_box_count": 6,
        "pre_hold_destroyed_box_count": 4,
        "post_hold_destroyed_box_count": 2,
        "unique_affected_category_count": 7,
    }
    counts_ok = isinstance(metrics, dict) and all(int_value(metrics.get(k)) == v for k, v in expected.items())
    categories_ok = isinstance(metrics, dict) and norm_set(metrics.get("categories_with_any_gap_or_loss")) == {
        "B",
        "C",
        "D",
        "E",
        "F",
        "H",
        "I",
    }
    return counts_ok and categories_ok, {
        "metrics": metrics,
        "expected_counts": expected,
        "expected_categories_with_any_gap_or_loss": ["B", "C", "D", "E", "F", "H", "I"],
    }


def check_p08(answer):
    required_actions = [
        ("RET-HARB-EHS-POST", "disclose_preservation_issue", "litigation_counsel", {"C", "D", "H"}),
        ("RET-HARB-AUDIT", "locate_missing_record", "compliance_audit", {"E", "F", "I"}),
        ("SRC-HARB-IRONVAULT", "collect_archive", "ediscovery_vendor", {"D", "E"}),
        ("RET-HARB-TEAMS", "document_system_gap", "it_messaging", {"D", "E"}),
        ("RET-HARB-VOICE", "document_system_gap", "it_messaging", {"D"}),
        ("RET-HARB-LAB-2019", "no_action_policy_loss", "records_management", {"B"}),
    ]
    action_checks = [
        has_action(answer, target, action, owner, categories) for target, action, owner, categories in required_actions
    ]
    priorities = []
    for target, *_ in required_actions:
        row = action_by_target(answer).get(target, {})
        priorities.append(int_value(row.get("priority_rank")))
    priorities_ok = (
        all(p is not None for p in priorities) and priorities[:3] == sorted(priorities[:3]) and priorities[0] == 1
    )
    passed = all(action_checks) and priorities_ok
    return passed, {
        "action_checks": dict(zip([item[0] for item in required_actions], action_checks)),
        "priorities": priorities,
        "expected_required_actions": [
            {
                "target_id": target,
                "action_type": action,
                "owner": owner,
                "affected_categories": sorted(categories),
            }
            for target, action, owner, categories in required_actions
        ],
    }


CHECKS = {
    "P01_matter_and_event_coverage": check_p01,
    "P02_pre_hold_policy_destruction": check_p02,
    "P03_post_hold_loss": check_p03,
    "P04_communication_gaps": check_p04,
    "P05_missing_audit_retention": check_p05,
    "P06_archive_exception": check_p06,
    "P07_metrics": check_p07,
    "P08_recommended_actions": check_p08,
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
        total_weight = sum(point["weight"] for point in RUBRIC)
        result = {
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
                    "details": {"error": f"{type(exc).__name__}: {exc}"},
                }
                for point in RUBRIC
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
