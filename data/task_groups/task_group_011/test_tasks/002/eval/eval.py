#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    ("SP001", 3, "decision_sets"),
    ("SP002", 2, "capacity"),
    ("SP003", 3, "sector_breach_handling"),
    ("SP004", 2, "startup_sba_net_exposure"),
    ("SP005", 2, "post_approval_concentrations"),
    ("SP006", 1, "priority_ranking"),
    ("SP007", 2, "low_quality_declines"),
    ("SP008", 1, "capacity_decline"),
]


def load_json(path):
    with open(path, "r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def money(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def ratio(value):
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def sorted_list(value):
    if not isinstance(value, list):
        return []
    return sorted(str(item) for item in value)


def decisions_by_id(data):
    rows = data.get("decisions", [])
    if not isinstance(rows, list):
        return {}
    return {row.get("application_id"): row for row in rows if isinstance(row, dict)}


def decision_sets(data):
    grouped = {"approve": set(), "conditional_approve": set(), "decline": set()}
    for app_id, row in decisions_by_id(data).items():
        decision = row.get("decision")
        if decision in grouped:
            grouped[decision].add(app_id)
    return grouped


def get_decision(data, app_id):
    return decisions_by_id(data).get(app_id, {})


def concentration_flags_by_id(data):
    rows = data.get("concentration_flags", [])
    if not isinstance(rows, list):
        return {}
    return {row.get("application_id"): row for row in rows if isinstance(row, dict)}


def concentration_map(data):
    rows = data.get("post_approval_concentrations", [])
    if not isinstance(rows, list):
        return {}
    return {row.get("sector"): row for row in rows if isinstance(row, dict)}


def decline_reasons(data, app_id):
    reasons = data.get("decline_reasons", {})
    if not isinstance(reasons, dict):
        return []
    return sorted_list(reasons.get(app_id))


def same_decision_amounts(pred, ans, app_id):
    prow = get_decision(pred, app_id)
    arow = get_decision(ans, app_id)
    return (
        prow.get("decision") == arow.get("decision")
        and money(prow.get("approved_amount")) == money(arow.get("approved_amount"))
        and money(prow.get("bank_capacity_used")) == money(arow.get("bank_capacity_used"))
        and sorted_list(prow.get("conditions")) == sorted_list(arow.get("conditions"))
    )


def check(point, pred, ans):
    if point == "decision_sets":
        return pred.get("branch_id") == ans.get("branch_id") and decision_sets(pred) == decision_sets(ans)

    if point == "capacity":
        pa = pred.get("allocation", {})
        aa = ans.get("allocation", {})
        return (
            money(pa.get("lending_capacity_q1")) == money(aa.get("lending_capacity_q1"))
            and money(pa.get("gross_approved_amount")) == money(aa.get("gross_approved_amount"))
            and money(pa.get("committed_capacity_amount")) == money(aa.get("committed_capacity_amount"))
            and money(pa.get("remaining_capacity")) == money(aa.get("remaining_capacity"))
        )

    if point == "sector_breach_handling":
        pflags = concentration_flags_by_id(pred)
        aflags = concentration_flags_by_id(ans)
        retail_pred = pflags.get("EAS-APP-902", {})
        retail_ans = aflags.get("EAS-APP-902", {})
        residential_pred = pflags.get("EAS-APP-004", {})
        residential_ans = aflags.get("EAS-APP-004", {})
        return (
            same_decision_amounts(pred, ans, "EAS-APP-902")
            and retail_pred.get("sector") == retail_ans.get("sector")
            and ratio(retail_pred.get("limit_pct")) == ratio(retail_ans.get("limit_pct"))
            and ratio(retail_pred.get("post_approval_pct")) == ratio(retail_ans.get("post_approval_pct"))
            and bool(retail_pred.get("flag")) == bool(retail_ans.get("flag"))
            and retail_pred.get("handling") == retail_ans.get("handling")
            and get_decision(pred, "EAS-APP-004").get("decision") == get_decision(ans, "EAS-APP-004").get("decision")
            and decline_reasons(pred, "EAS-APP-004") == decline_reasons(ans, "EAS-APP-004")
            and residential_pred.get("handling") == residential_ans.get("handling")
            and ratio(residential_pred.get("post_approval_pct")) == ratio(residential_ans.get("post_approval_pct"))
        )

    if point == "startup_sba_net_exposure":
        return same_decision_amounts(pred, ans, "EAS-APP-903")

    if point == "post_approval_concentrations":
        pm = concentration_map(pred)
        am = concentration_map(ans)
        if set(pm) != set(am):
            return False
        for sector, expected in am.items():
            observed = pm.get(sector, {})
            if (
                money(observed.get("exposure_after_approval")) != money(expected.get("exposure_after_approval"))
                or ratio(observed.get("post_approval_pct")) != ratio(expected.get("post_approval_pct"))
                or ratio(observed.get("limit_pct")) != ratio(expected.get("limit_pct"))
                or bool(observed.get("over_limit")) != bool(expected.get("over_limit"))
            ):
                return False
        return True

    if point == "priority_ranking":
        return pred.get("allocation", {}).get("priority_ranking") == ans.get("allocation", {}).get("priority_ranking")

    if point == "low_quality_declines":
        return (
            decline_reasons(pred, "EAS-APP-001") == decline_reasons(ans, "EAS-APP-001")
            and decline_reasons(pred, "EAS-APP-003") == decline_reasons(ans, "EAS-APP-003")
            and decline_reasons(pred, "EAS-APP-006") == decline_reasons(ans, "EAS-APP-006")
        )

    if point == "capacity_decline":
        return (
            get_decision(pred, "EAS-APP-002").get("decision") == get_decision(ans, "EAS-APP-002").get("decision")
            and decline_reasons(pred, "EAS-APP-002") == decline_reasons(ans, "EAS-APP-002")
            and money(get_decision(pred, "EAS-APP-002").get("bank_capacity_used")) == 0.0
        )

    return False


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "usage: eval.py prediction.json"}))
        return 2

    answer_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        pred = load_json(sys.argv[1])
        ans = load_json(answer_path)
    except Exception as exc:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": str(exc), "points": []}))
        return 0

    total = sum(weight for _, weight, _ in POINTS)
    earned = 0
    point_rows = []
    for point_id, weight, key in POINTS:
        passed = check(key, pred, ans)
        if passed:
            earned += weight
        point_rows.append({"id": point_id, "passed": passed, "weight": weight})

    print(json.dumps({"score": round(earned / total, 10), "max_score": 1.0, "points": point_rows}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
