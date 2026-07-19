#!/usr/bin/env python3
import json
import sys
from pathlib import Path


TASK_DIR = Path(__file__).resolve().parents[1]
GOLD_PATH = TASK_DIR / "output" / "answer.json"
TARGET_IDS = [f"C-TR1-{idx:03d}" for idx in range(1, 9)]
TOTAL_WEIGHT = 16


EXPECTED = {
    "application_decisions": [
        {
            "application_id": "C-TR1-001",
            "determination": "HOLD",
            "deficiency_codes": [
                "bond_shortfall",
                "endorsement_missing",
                "experience_shortfall",
            ],
            "required_actions": [
                "increase_bond_amount",
                "obtain_required_endorsement",
                "submit_experience_evidence",
            ],
            "risk_tier": "medium",
            "policy_impacted": True,
        },
        {
            "application_id": "C-TR1-002",
            "determination": "HOLD",
            "deficiency_codes": [
                "endorsement_pending",
                "inspection_doc_gap",
                "insurance_expired",
            ],
            "required_actions": [
                "clear_document_gap",
                "provide_current_insurance",
                "verify_pending_endorsement",
            ],
            "risk_tier": "medium",
            "policy_impacted": False,
        },
        {
            "application_id": "C-TR1-003",
            "determination": "DENY",
            "deficiency_codes": [
                "active_suspension",
                "inspection_safety_recheck",
                "insurance_pending",
            ],
            "required_actions": [
                "board_review_suspension",
                "complete_safety_recheck",
                "verify_insurance_binding",
            ],
            "risk_tier": "high",
            "policy_impacted": False,
        },
        {
            "application_id": "C-TR1-004",
            "determination": "HOLD",
            "deficiency_codes": ["bond_cancelled"],
            "required_actions": ["obtain_current_bond"],
            "risk_tier": "medium",
            "policy_impacted": False,
        },
        {
            "application_id": "C-TR1-005",
            "determination": "DENY",
            "deficiency_codes": [
                "endorsement_pending",
                "experience_shortfall",
                "insurance_shortfall",
                "open_serious_violation",
            ],
            "required_actions": [
                "increase_insurance_amount",
                "resolve_serious_violation",
                "submit_experience_evidence",
                "verify_pending_endorsement",
            ],
            "risk_tier": "high",
            "policy_impacted": True,
        },
        {
            "application_id": "C-TR1-006",
            "determination": "HOLD",
            "deficiency_codes": ["experience_shortfall"],
            "required_actions": ["submit_experience_evidence"],
            "risk_tier": "medium",
            "policy_impacted": False,
        },
        {
            "application_id": "C-TR1-007",
            "determination": "HOLD",
            "deficiency_codes": [
                "bond_shortfall",
                "endorsement_missing",
                "inspection_doc_gap",
                "open_minor_violation",
            ],
            "required_actions": [
                "clear_document_gap",
                "increase_bond_amount",
                "obtain_required_endorsement",
                "resolve_minor_violation_review",
            ],
            "risk_tier": "medium",
            "policy_impacted": True,
        },
        {
            "application_id": "C-TR1-008",
            "determination": "HOLD",
            "deficiency_codes": [
                "endorsement_pending",
                "insurance_expired",
            ],
            "required_actions": [
                "provide_current_insurance",
                "verify_pending_endorsement",
            ],
            "risk_tier": "medium",
            "policy_impacted": False,
        },
    ],
    "summary": {
        "approve_count": 0,
        "hold_count": 6,
        "deny_count": 2,
        "high_risk_application_ids": ["C-TR1-003", "C-TR1-005"],
        "policy_impacted_application_ids": [
            "C-TR1-001",
            "C-TR1-005",
            "C-TR1-007",
        ],
        "stale_or_unverified_correspondence_ids": [
            "COR-C-TR1-001-1",
            "COR-C-TR1-002-1",
            "COR-C-TR1-004-1",
            "COR-C-TR1-007-1",
        ],
    },
}


def load_candidate(path_arg):
    candidate_path = Path(path_arg) if path_arg else GOLD_PATH
    with candidate_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def as_list(value):
    return value if isinstance(value, list) else []


def sorted_unique_strings(value):
    if not isinstance(value, list):
        return None
    if not all(isinstance(item, str) for item in value):
        return None
    return sorted(set(value))


def decision_map(answer):
    rows = as_list(answer.get("application_decisions") if isinstance(answer, dict) else None)
    result = {}
    duplicates = set()
    for row in rows:
        if not isinstance(row, dict):
            continue
        app_id = row.get("application_id")
        if app_id in result:
            duplicates.add(app_id)
        result[app_id] = row
    return rows, result, duplicates


def expected_map():
    return {row["application_id"]: row for row in EXPECTED["application_decisions"]}


def add_point(points, point_id, goal, weight, passed, details):
    assigned = weight / TOTAL_WEIGHT
    points.append(
        {
            "id": point_id,
            "goal": goal,
            "weight": weight,
            "assigned_score": round(assigned, 6),
            "passed": bool(passed),
            "earned_score": round(assigned if passed else 0.0, 6),
            "details": details,
        }
    )


def score_answer(answer):
    points = []
    exp_map = expected_map()
    rows, got_map, duplicates = decision_map(answer)
    summary = answer.get("summary") if isinstance(answer, dict) else None
    if not isinstance(summary, dict):
        summary = {}

    ordered_ids = [row.get("application_id") for row in rows if isinstance(row, dict)]
    coverage_pass = ordered_ids == TARGET_IDS and not duplicates
    add_point(
        points,
        "SP001",
        "Includes exactly the target applications in application_id order.",
        1,
        coverage_pass,
        f"observed_order={ordered_ids}; duplicate_ids={sorted(duplicates)}",
    )

    determination_mismatches = []
    for app_id in TARGET_IDS:
        got = got_map.get(app_id, {}).get("determination")
        expected = exp_map[app_id]["determination"]
        if got != expected:
            determination_mismatches.append(f"{app_id}: expected {expected}, got {got}")
    add_point(
        points,
        "SP002",
        "Correct approve, hold, or deny determination for every target application.",
        3,
        not determination_mismatches,
        "; ".join(determination_mismatches) or "all determinations match",
    )

    deficiency_mismatches = []
    for app_id in TARGET_IDS:
        got = sorted_unique_strings(got_map.get(app_id, {}).get("deficiency_codes"))
        expected = sorted(exp_map[app_id]["deficiency_codes"])
        if got != expected:
            deficiency_mismatches.append(f"{app_id}: expected {expected}, got {got}")
    add_point(
        points,
        "SP003",
        "Correct deficiency code set for each target application.",
        3,
        not deficiency_mismatches,
        "; ".join(deficiency_mismatches) or "all deficiency code sets match",
    )

    action_mismatches = []
    for app_id in TARGET_IDS:
        got = sorted_unique_strings(got_map.get(app_id, {}).get("required_actions"))
        expected = sorted(exp_map[app_id]["required_actions"])
        if got != expected:
            action_mismatches.append(f"{app_id}: expected {expected}, got {got}")
    add_point(
        points,
        "SP004",
        "Correct required action set for each target application.",
        2,
        not action_mismatches,
        "; ".join(action_mismatches) or "all required action sets match",
    )

    risk_mismatches = []
    for app_id in TARGET_IDS:
        got = got_map.get(app_id, {}).get("risk_tier")
        expected = exp_map[app_id]["risk_tier"]
        if got != expected:
            risk_mismatches.append(f"{app_id}: expected {expected}, got {got}")
    got_high_risk = sorted_unique_strings(summary.get("high_risk_application_ids"))
    expected_high_risk = sorted(EXPECTED["summary"]["high_risk_application_ids"])
    if got_high_risk != expected_high_risk:
        risk_mismatches.append(f"summary.high_risk_application_ids expected {expected_high_risk}, got {got_high_risk}")
    add_point(
        points,
        "SP005",
        "Correct risk tiers and high-risk application summary.",
        2,
        not risk_mismatches,
        "; ".join(risk_mismatches) or "risk tiers and high-risk summary match",
    )

    policy_mismatches = []
    for app_id in TARGET_IDS:
        got = got_map.get(app_id, {}).get("policy_impacted")
        expected = exp_map[app_id]["policy_impacted"]
        if got is not expected:
            policy_mismatches.append(f"{app_id}: expected {expected}, got {got}")
    got_policy_ids = sorted_unique_strings(summary.get("policy_impacted_application_ids"))
    expected_policy_ids = sorted(EXPECTED["summary"]["policy_impacted_application_ids"])
    if got_policy_ids != expected_policy_ids:
        policy_mismatches.append(
            f"summary.policy_impacted_application_ids expected {expected_policy_ids}, got {got_policy_ids}"
        )
    add_point(
        points,
        "SP006",
        "Correct current-policy impact flags and policy-impact summary set.",
        2,
        not policy_mismatches,
        "; ".join(policy_mismatches) or "policy-impact fields match",
    )

    count_mismatches = []
    for key in ("approve_count", "hold_count", "deny_count"):
        got = summary.get(key)
        expected = EXPECTED["summary"][key]
        if got != expected:
            count_mismatches.append(f"{key}: expected {expected}, got {got}")
    add_point(
        points,
        "SP007",
        "Correct approve, hold, and deny batch summary counts.",
        2,
        not count_mismatches,
        "; ".join(count_mismatches) or "summary counts match",
    )

    got_stale = sorted_unique_strings(summary.get("stale_or_unverified_correspondence_ids"))
    expected_stale = sorted(EXPECTED["summary"]["stale_or_unverified_correspondence_ids"])
    add_point(
        points,
        "SP008",
        "Correct stale or unverified correspondence summary identifiers.",
        1,
        got_stale == expected_stale,
        (
            "stale_or_unverified_correspondence_ids match"
            if got_stale == expected_stale
            else f"expected {expected_stale}, got {got_stale}"
        ),
    )

    score = round(sum(point["earned_score"] for point in points), 6)
    return {"score": score, "points": points}


def main():
    path_arg = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1] else ""
    try:
        answer = load_candidate(path_arg)
        result = score_answer(answer)
    except Exception as exc:
        result = {
            "score": 0.0,
            "points": [
                {
                    "id": "PARSE",
                    "goal": "Candidate answer must be readable JSON.",
                    "weight": 1,
                    "assigned_score": 0.0,
                    "passed": False,
                    "earned_score": 0.0,
                    "details": str(exc),
                }
            ],
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
