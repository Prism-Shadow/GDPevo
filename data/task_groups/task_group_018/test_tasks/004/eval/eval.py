#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED_CASES = ["LC-24-0899", "LC-25-0320", "LC-25-0326", "LC-25-0331"]
INCLUDED = {"LC-24-0899", "LC-25-0320", "LC-25-0326"}
EXCLUDED = {"LC-25-0331"}

EXPECTED_AUDIT = {
    ("LC-24-0899", "counsel_type", "appointed_private B. Vale", "use_corrob_memo"),
    ("LC-24-0899", "departure_status", "no_departure", "use_hearing_notes"),
    ("LC-24-0899", "source_system", "bench_trial_guilty", "use_hearing_notes"),
    ("LC-25-0320", "merged_counts", "merge_counts_2_3_no_separate_financial", "use_hearing_notes"),
    ("LC-25-0326", "filed_date", "2025-02-21", "use_cms"),
    ("LC-25-0326", "user_fee", "public_defender_user_fee_waived", "use_hearing_notes"),
    ("LC-25-0331", "disposition_status", "continued_no_final_order", "exclude_pending"),
}

EXPECTED_COUNSEL_USER_FEE = {
    "LC-24-0899": ("appointed_private", "B. Vale", "not_applicable_non_pd"),
    "LC-25-0320": ("retained", "D. Wray", "not_applicable_non_pd"),
    "LC-25-0326": ("public_defender", "E. Soto", "waived_by_court"),
    "LC-25-0331": ("public_defender", "E. Soto", "do_not_post_pending"),
}

EXPECTED_DISPOSITIONS = {
    "LC-24-0899": {
        "case_status": "disposed",
        "closeout_action": "enter_disposition",
        "disposition_date": "2025-06-18",
        "active_count_no": 1,
        "merged_counts": [],
        "merged_count_handling": "no_merged_counts",
        "offense_code": "THEFT-CLASS-D",
        "plea": "not guilty",
        "charge_disposition": "guilty",
        "trial_or_plea_posture": "bench_trial",
        "fine_ordered": 1000.0,
        "jail_days_imposed": 90,
        "jail_days_suspended": 300,
        "probation_months": 12,
    },
    "LC-25-0320": {
        "case_status": "disposed",
        "closeout_action": "enter_disposition",
        "disposition_date": "2025-06-18",
        "active_count_no": 1,
        "merged_counts": [2, 3],
        "merged_count_handling": "merge_no_separate_financial",
        "offense_code": "POSS-CS",
        "plea": "no contest",
        "charge_disposition": "deferred",
        "trial_or_plea_posture": "no_contest_plea",
        "fine_ordered": 250.0,
        "jail_days_imposed": 365,
        "jail_days_suspended": 0,
        "probation_months": 12,
    },
    "LC-25-0326": {
        "case_status": "disposed",
        "closeout_action": "enter_disposition",
        "disposition_date": "2025-06-18",
        "active_count_no": 1,
        "merged_counts": [],
        "merged_count_handling": "no_merged_counts",
        "offense_code": "POSS-CS",
        "plea": "none",
        "charge_disposition": "nolle_prosequi",
        "trial_or_plea_posture": "nolle_no_plea",
        "fine_ordered": 0.0,
        "jail_days_imposed": 0,
        "jail_days_suspended": 0,
        "probation_months": 0,
    },
    "LC-25-0331": {
        "case_status": "continued",
        "closeout_action": "no_closeout",
        "disposition_date": None,
        "active_count_no": 1,
        "merged_counts": [],
        "merged_count_handling": "not_applicable_pending",
        "offense_code": "FAIL-APP",
        "plea": "none",
        "charge_disposition": "pending",
        "trial_or_plea_posture": "continued_no_plea",
        "fine_ordered": 0.0,
        "jail_days_imposed": 0,
        "jail_days_suspended": 0,
        "probation_months": 0,
    },
}

EXPECTED_DEPARTURES = {
    "LC-24-0899": "no_departure",
    "LC-25-0320": "durational_departure",
    "LC-25-0326": "not_applicable",
    "LC-25-0331": "not_applicable",
}

EXPECTED_FEES = {
    "LC-24-0899": ("post", {("fine", 1000.0), ("court_cost", 145.0)}, 1145.0),
    "LC-25-0320": ("post", {("fine", 250.0), ("court_cost", 145.0)}, 395.0),
    "LC-25-0326": ("post", {("court_cost", 145.0)}, 145.0),
    "LC-25-0331": ("exclude", set(), 0.0),
}

EXPECTED_DOCKET = {
    "LC-24-0899": (
        "2025-06-18",
        "disposition",
        "sentencing_order_entered",
        "enter_final_disposition_and_financials",
        "bench_trial_conviction_no_departure",
        1145.0,
    ),
    "LC-25-0320": (
        "2025-06-18",
        "disposition",
        "deferred_order_entered",
        "enter_final_disposition_and_financials",
        "merged_counts_deferred_departure",
        395.0,
    ),
    "LC-25-0326": (
        "2025-06-18",
        "disposition",
        "dismissal_order_entered",
        "enter_final_disposition_and_financials",
        "nolle_pd_fee_waived",
        145.0,
    ),
    "LC-25-0331": (
        None,
        "disposition_hold",
        "continued_no_disposition",
        "exclude_no_final_order",
        "continued_no_closeout",
        0.0,
    ),
}

EXPECTED_TOTALS = {
    "included_case_count": 3,
    "excluded_pending_count": 1,
    "disposition_entry_count": 3,
    "financial_entry_count": 3,
    "fine_total": 1250.0,
    "mandatory_court_cost_total": 435.0,
    "user_fee_total": 0.0,
    "assessment_total": 0.0,
    "grand_total_due": 1685.0,
}

POINTS = [
    ("SP001", "Correct final included case set and continued/pending exclusion record.", 1),
    (
        "SP002",
        "Correct audit findings for counsel, filing/source, merged-count, departure, user-fee, and continued-status conflicts.",
        3,
    ),
    (
        "SP003",
        "Correct counsel-type reconciliation and conditional public-defender user-fee treatment for all target cases.",
        2,
    ),
    (
        "SP004",
        "Correct disposition outcomes, closeout actions, dates, count merging, pleas, sentences, and pending treatment.",
        3,
    ),
    ("SP005", "Correct departure and non-departure classification for every target case.", 1),
    ("SP006", "Correct per-case financial posting, fee inclusion/exclusion, and case totals.", 1),
    ("SP007", "Correct docket/register action language codes, entry codes, dates, and amount due for each case.", 3),
    ("SP008", "Correct aggregate Lake County register counts and dollar totals.", 1),
]


def load_candidate(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__load_error__": str(exc)}


def norm_text(value):
    if value is None:
        return ""
    return " ".join(str(value).strip().lower().replace("_", " ").split()).replace(" ", "_")


def norm_value(value):
    return " ".join(str(value).strip().lower().split()) if value is not None else ""


def money(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def is_money(value, expected):
    actual = money(value)
    return actual is not None and math.isclose(actual, round(expected, 2), abs_tol=0.005)


def int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def by_case(items):
    if not isinstance(items, list):
        return {}
    out = {}
    for item in items:
        if isinstance(item, dict) and isinstance(item.get("case_number"), str):
            out[item["case_number"]] = item
    return out


def sorted_ints(value):
    if not isinstance(value, list):
        return None
    try:
        return sorted(int(v) for v in value)
    except (TypeError, ValueError):
        return None


def check_sp001(data):
    included = set(data.get("included_case_numbers") or [])
    exclusions = by_case(data.get("excluded_matters"))
    row = exclusions.get("LC-25-0331", {})
    ok = (
        included == INCLUDED
        and set(exclusions) == EXCLUDED
        and norm_text(row.get("status")) == "continued"
        and norm_text(row.get("exclusion_reason")) == "continued_no_final_order"
        and norm_text(row.get("draft_disposition_entry")) == "do_not_post"
        and row.get("next_status_check_date") == "2025-07-16"
        and row.get("financial_posting_allowed") is False
    )
    return ok, f"included={sorted(included)} exclusions={sorted(exclusions)}"


def check_sp002(data):
    findings = data.get("audit_findings")
    if not isinstance(findings, list):
        return False, "audit_findings is not a list"
    actual = set()
    for item in findings:
        if not isinstance(item, dict):
            continue
        actual.add(
            (
                str(item.get("case_number", "")),
                norm_text(item.get("field_name")),
                norm_value(item.get("resolved_value")),
                norm_text(item.get("recommended_resolution")),
            )
        )
    expected = {
        (case, norm_text(field), norm_value(resolved), norm_text(source))
        for case, field, resolved, source in EXPECTED_AUDIT
    }
    return actual == expected, f"expected {len(expected)} audit findings; got {len(actual)}"


def check_sp003(data):
    cases = by_case(data.get("case_dispositions"))
    fees = by_case(data.get("fee_reconciliation"))
    failures = []
    for case, (counsel, attorney, user_fee_decision) in EXPECTED_COUNSEL_USER_FEE.items():
        case_row = cases.get(case, {})
        fee_row = fees.get(case, {})
        if norm_text(case_row.get("counsel_type")) != counsel:
            failures.append(f"{case}.counsel_type")
        if case_row.get("attorney_name") != attorney:
            failures.append(f"{case}.attorney_name")
        if norm_text(fee_row.get("user_fee_decision")) != user_fee_decision:
            failures.append(f"{case}.user_fee_decision")
    return not failures, "mismatches=" + ",".join(failures[:12])


def check_sp004(data):
    cases = by_case(data.get("case_dispositions"))
    failures = []
    for case, exp in EXPECTED_DISPOSITIONS.items():
        row = cases.get(case, {})
        charge = row.get("charge") if isinstance(row.get("charge"), dict) else {}
        sentence = row.get("sentence") if isinstance(row.get("sentence"), dict) else {}
        for key in ["case_status", "closeout_action"]:
            if norm_text(row.get(key)) != exp[key]:
                failures.append(f"{case}.{key}")
        if row.get("disposition_date") != exp["disposition_date"]:
            failures.append(f"{case}.disposition_date")
        for key in ["merged_count_handling", "plea", "charge_disposition", "trial_or_plea_posture"]:
            if norm_text(charge.get(key)) != norm_text(exp[key]):
                failures.append(f"{case}.{key}")
        if int_or_none(charge.get("active_count_no")) != exp["active_count_no"]:
            failures.append(f"{case}.active_count_no")
        if sorted_ints(charge.get("merged_counts")) != exp["merged_counts"]:
            failures.append(f"{case}.merged_counts")
        if charge.get("offense_code") != exp["offense_code"]:
            failures.append(f"{case}.offense_code")
        for key in ["jail_days_imposed", "jail_days_suspended", "probation_months"]:
            if int_or_none(sentence.get(key)) != exp[key]:
                failures.append(f"{case}.{key}")
        if not is_money(sentence.get("fine_ordered"), exp["fine_ordered"]):
            failures.append(f"{case}.fine_ordered")
    return not failures, "mismatches=" + ",".join(failures[:16])


def check_sp005(data):
    cases = by_case(data.get("case_dispositions"))
    failures = []
    for case, expected in EXPECTED_DEPARTURES.items():
        charge = cases.get(case, {}).get("charge", {})
        if not isinstance(charge, dict) or norm_text(charge.get("departure_status")) != expected:
            failures.append(case)
    return not failures, "departure mismatches=" + ",".join(failures)


def check_sp006(data):
    fees = by_case(data.get("fee_reconciliation"))
    failures = []
    for case, (status, expected_items, total) in EXPECTED_FEES.items():
        row = fees.get(case, {})
        if norm_text(row.get("fee_status")) != status:
            failures.append(f"{case}.fee_status")
        items = row.get("fee_items", [])
        actual_items = set()
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict) and money(item.get("amount")) is not None:
                    actual_items.add((norm_text(item.get("fee_code")), money(item.get("amount"))))
        expected_norm = {(norm_text(code), round(amount, 2)) for code, amount in expected_items}
        if actual_items != expected_norm:
            failures.append(f"{case}.fee_items")
        if not is_money(row.get("case_total"), total):
            failures.append(f"{case}.case_total")
    return not failures, "mismatches=" + ",".join(failures[:12])


def check_sp007(data):
    entries = by_case(data.get("docket_entries"))
    failures = []
    for case, exp in EXPECTED_DOCKET.items():
        row = entries.get(case, {})
        actual = (
            row.get("entry_date"),
            norm_text(row.get("docket_entry_type")),
            norm_text(row.get("entry_code")),
            norm_text(row.get("action_code")),
            norm_text(row.get("language_code")),
            money(row.get("amount_due")),
        )
        expected = (
            exp[0],
            norm_text(exp[1]),
            norm_text(exp[2]),
            norm_text(exp[3]),
            norm_text(exp[4]),
            round(exp[5], 2),
        )
        if actual != expected:
            failures.append(case)
    return not failures, "docket mismatches=" + ",".join(failures)


def check_sp008(data):
    totals = data.get("register_totals", {})
    if not isinstance(totals, dict):
        return False, "register_totals is not an object"
    failures = []
    for key, expected in EXPECTED_TOTALS.items():
        if isinstance(expected, int):
            ok = int_or_none(totals.get(key)) == expected
        else:
            ok = is_money(totals.get(key), expected)
        if not ok:
            failures.append(key)
    return not failures, "total mismatches=" + ",".join(failures)


CHECKS = [check_sp001, check_sp002, check_sp003, check_sp004, check_sp005, check_sp006, check_sp007, check_sp008]


def main():
    candidate_path = (
        sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    candidate = load_candidate(candidate_path)
    total_weight = sum(weight for _, _, weight in POINTS)
    results = []
    earned_total = 0.0

    if "__load_error__" in candidate:
        for point_id, goal, weight in POINTS:
            assigned = weight / total_weight
            results.append(
                {
                    "id": point_id,
                    "goal": goal,
                    "weight": weight,
                    "assigned_score": round(assigned, 6),
                    "passed": False,
                    "earned": 0.0,
                    "details": candidate["__load_error__"],
                }
            )
    else:
        for (point_id, goal, weight), check in zip(POINTS, CHECKS):
            assigned = weight / total_weight
            passed, details = check(candidate)
            earned = assigned if passed else 0.0
            earned_total += earned
            results.append(
                {
                    "id": point_id,
                    "goal": goal,
                    "weight": weight,
                    "assigned_score": round(assigned, 6),
                    "passed": passed,
                    "earned": round(earned, 6),
                    "details": details,
                }
            )

    print(json.dumps({"score": round(earned_total, 6), "points": results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
