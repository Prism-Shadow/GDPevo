#!/usr/bin/env python3
import json
import sys
from pathlib import Path


POINTS = [
    ("SP001", 3, "decision_sets"),
    ("SP002", 2, "capacity"),
    ("SP003", 3, "healthcare_breach_handling"),
    ("SP004", 2, "high_risk_consumer_decline"),
    ("SP005", 2, "startup_sba_structure"),
    ("SP006", 2, "post_approval_concentrations"),
    ("SP007", 1, "priority_ranking"),
]


def load_json(path):
    with open(path, encoding="utf-8-sig") as f:
        return json.load(f)


def money(value):
    try:
        return round(float(value), 2)
    except Exception:
        return None


def ratio(value):
    try:
        return round(float(value), 4)
    except Exception:
        return None


def decisions_by_id(data):
    return {d.get("application_id"): d for d in data.get("decisions", []) if isinstance(d, dict)}


def decision_sets(data):
    by_id = decisions_by_id(data)
    grouped = {"approve": set(), "conditional_approve": set(), "decline": set()}
    for app_id, row in by_id.items():
        if row.get("decision") in grouped:
            grouped[row["decision"]].add(app_id)
    return grouped


def sorted_list(value):
    if not isinstance(value, list):
        return []
    return sorted(str(x) for x in value)


def concentration_map(data):
    rows = data.get("post_approval_concentrations", [])
    return {r.get("sector"): r for r in rows if isinstance(r, dict)}


def get_decision(data, app_id):
    return decisions_by_id(data).get(app_id, {})


def check(point, pred, ans):
    if point == "decision_sets":
        return decision_sets(pred) == decision_sets(ans)

    if point == "capacity":
        pa = pred.get("allocation", {})
        aa = ans.get("allocation", {})
        return money(pa.get("committed_capacity_amount")) == money(aa.get("committed_capacity_amount")) and money(
            pa.get("remaining_capacity")
        ) == money(aa.get("remaining_capacity"))

    if point == "healthcare_breach_handling":
        pd = get_decision(pred, "LAK-APP-901")
        ad = get_decision(ans, "LAK-APP-901")
        pflags = pred.get("concentration_flags", [])
        aflags = ans.get("concentration_flags", [])
        pflag = next((x for x in pflags if isinstance(x, dict) and x.get("application_id") == "LAK-APP-901"), {})
        aflag = next((x for x in aflags if isinstance(x, dict) and x.get("application_id") == "LAK-APP-901"), {})
        return (
            pd.get("decision") == ad.get("decision")
            and sorted_list(pd.get("conditions")) == sorted_list(ad.get("conditions"))
            and money(pd.get("bank_capacity_used")) == money(ad.get("bank_capacity_used"))
            and pflag.get("handling") == aflag.get("handling")
            and ratio(pflag.get("post_approval_pct")) == ratio(aflag.get("post_approval_pct"))
        )

    if point == "high_risk_consumer_decline":
        return sorted_list(pred.get("decline_reasons", {}).get("LAK-APP-903")) == sorted_list(
            ans.get("decline_reasons", {}).get("LAK-APP-903")
        )

    if point == "startup_sba_structure":
        pd = get_decision(pred, "LAK-APP-902")
        ad = get_decision(ans, "LAK-APP-902")
        return (
            pd.get("decision") == ad.get("decision")
            and money(pd.get("approved_amount")) == money(ad.get("approved_amount"))
            and money(pd.get("bank_capacity_used")) == money(ad.get("bank_capacity_used"))
            and sorted_list(pd.get("conditions")) == sorted_list(ad.get("conditions"))
        )

    if point == "post_approval_concentrations":
        pm = concentration_map(pred)
        am = concentration_map(ans)
        if set(pm) != set(am):
            return False
        for sector, ar in am.items():
            pr = pm.get(sector, {})
            if (
                money(pr.get("exposure_after_approval")) != money(ar.get("exposure_after_approval"))
                or ratio(pr.get("post_approval_pct")) != ratio(ar.get("post_approval_pct"))
                or ratio(pr.get("limit_pct")) != ratio(ar.get("limit_pct"))
                or bool(pr.get("over_limit")) != bool(ar.get("over_limit"))
            ):
                return False
        return True

    if point == "priority_ranking":
        return pred.get("allocation", {}).get("priority_ranking") == ans.get("allocation", {}).get("priority_ranking")

    return False


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": "usage: eval.py prediction.json"}))
        return
    answer_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    try:
        pred = load_json(sys.argv[1])
        ans = load_json(answer_path)
    except Exception as exc:
        print(json.dumps({"score": 0.0, "max_score": 1.0, "error": str(exc), "points": []}))
        return

    total = sum(weight for _, weight, _ in POINTS)
    point_rows = []
    earned = 0
    for point_id, weight, key in POINTS:
        passed = check(key, pred, ans)
        if passed:
            earned += weight
        point_rows.append({"id": point_id, "passed": passed, "weight": weight})
    print(json.dumps({"score": round(earned / total, 10), "max_score": 1.0, "points": point_rows}, sort_keys=True))


if __name__ == "__main__":
    main()
