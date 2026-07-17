#!/usr/bin/env python3
import json
import sys
from pathlib import Path


CAUSES = [
    "ExternalDependency",
    "Environment",
    "SecurityReview",
    "Capacity",
    "DesignDecision",
    "DataMigration",
    "Vendor",
    "OwnershipGap",
]

CATEGORY_ORDER = ["NewFeature", "TechDebt", "Reliability", "Security"]


def load_json(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def at(obj, *path, default=None):
    cur = obj
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def id_set(value):
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def ordered_id_list(value):
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def as_round1(value):
    try:
        return round(float(value), 1)
    except (TypeError, ValueError):
        return None


def milestone_completion(obj):
    rows = at(obj, "release", "milestone_completion", default=[])
    if not isinstance(rows, list):
        return {}
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        milestone_id = row.get("milestone_id")
        if milestone_id is not None:
            result[str(milestone_id)] = as_round1(row.get("completion_percentage"))
    return result


def blocker_cause_counts(obj):
    raw = at(obj, "release", "blocker_cause_counts", default={})
    if not isinstance(raw, dict):
        raw = {}
    result = {cause: as_int(raw.get(cause, 0)) for cause in CAUSES}
    for key, value in raw.items():
        if key not in CAUSES and as_int(value) not in (None, 0):
            result[str(key)] = as_int(value)
    return result


def category_gap_summary(obj):
    section = at(obj, "release_scoped_portfolio_allocation", default={})
    if not isinstance(section, dict):
        section = {}
    rows = section.get("category_rows", [])
    row_summary = {}
    if isinstance(rows, list):
        for row in rows:
            if not isinstance(row, dict):
                continue
            category = row.get("category")
            if category is None:
                continue
            row_summary[str(category)] = {
                "count": as_int(row.get("count")),
                "actual_percentage": as_round1(row.get("actual_percentage")),
                "target_percentage": as_round1(row.get("target_percentage")),
                "gap_basis_points": as_int(row.get("gap_basis_points")),
                "evidence_sample_ids": id_set(row.get("evidence_sample_ids", [])),
            }
    ordered_rows = {category: row_summary.get(category) for category in CATEGORY_ORDER}
    under = section.get("under_invested_categories", [])
    actions = section.get("follow_up_actions", [])
    action_summary = []
    if isinstance(actions, list):
        for action in actions:
            if not isinstance(action, dict):
                continue
            action_summary.append(
                (
                    str(action.get("category")),
                    str(action.get("action")),
                    str(action.get("owner_team_id")),
                )
            )
    return {
        "eligible_total": as_int(section.get("eligible_total")),
        "category_rows": ordered_rows,
        "under_invested_categories": [
            category for category in CATEGORY_ORDER if category in set(under if isinstance(under, list) else [])
        ],
        "largest_negative_gap_category": section.get("largest_negative_gap_category"),
        "follow_up_actions": sorted(action_summary),
    }


def make_point(point_id, weight, passed, goal):
    return {
        "id": point_id,
        "weight": weight,
        "passed": bool(passed),
        "goal": goal,
    }


def main():
    here = Path(__file__).resolve()
    expected_path = here.parents[1] / "output" / "answer.json"
    prediction_path = Path(sys.argv[1]) if len(sys.argv) > 1 else expected_path

    try:
        expected = load_json(expected_path)
        prediction = load_json(prediction_path)
    except Exception as exc:
        points = [
            make_point(
                "SP000",
                1,
                False,
                f"Prediction must be readable JSON: {type(exc).__name__}",
            )
        ]
        print(json.dumps({"score": 0.0, "max_score": 1.0, "points": points}, indent=2))
        return 0

    points = [
        make_point(
            "SP001",
            2,
            at(prediction, "release", "ship_decision") == at(expected, "release", "ship_decision"),
            "Release ship decision matches the readiness gate result.",
        ),
        make_point(
            "SP002",
            3,
            id_set(at(prediction, "release", "gating_work_item_ids", default=[]))
            == id_set(at(expected, "release", "gating_work_item_ids", default=[])),
            "Gating work item set matches active critical release gates.",
        ),
        make_point(
            "SP003",
            2,
            milestone_completion(prediction) == milestone_completion(expected),
            "Milestone completion percentages match by milestone.",
        ),
        make_point(
            "SP004",
            2,
            blocker_cause_counts(prediction) == blocker_cause_counts(expected),
            "Blocker cause counts match controlled release blocker causes.",
        ),
        make_point(
            "SP005",
            2,
            ordered_id_list(at(prediction, "release", "critical_dependency_chain", default=[]))
            == ordered_id_list(at(expected, "release", "critical_dependency_chain", default=[])),
            "Critical dependency chain matches the lexicographically smallest qualifying chain.",
        ),
        make_point(
            "SP006",
            3,
            id_set(at(prediction, "release_scoped_portfolio_allocation", "eligible_work_item_ids", default=[]))
            == id_set(at(expected, "release_scoped_portfolio_allocation", "eligible_work_item_ids", default=[])),
            "Release-scoped portfolio eligible closed-work set matches.",
        ),
        make_point(
            "SP007",
            3,
            category_gap_summary(prediction) == category_gap_summary(expected),
            "Portfolio category counts, percentages, gaps, under-investment, and follow-up mapping match.",
        ),
        make_point(
            "SP008",
            1,
            at(prediction, "combined_action") == at(expected, "combined_action"),
            "Combined action enum matches the release and portfolio result.",
        ),
    ]

    total_weight = sum(point["weight"] for point in points)
    earned = sum(point["weight"] for point in points if point["passed"])
    score = earned / total_weight if total_weight else 0.0
    print(json.dumps({"score": round(score, 6), "max_score": 1.0, "points": points}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
