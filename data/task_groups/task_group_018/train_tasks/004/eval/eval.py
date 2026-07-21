#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED_CASES = ["UC-24-0775", "UC-25-0221", "UC-25-0224", "UC-25-0230", "UC-25-0238"]
DISPOSED = {"UC-24-0775", "UC-25-0221", "UC-25-0224", "UC-25-0230"}
PENDING = {"UC-25-0238"}

EXPECTED_AUDIT = {
    "UC-24-0775": {
        "dob_for_entry": "1990-05-30",
        "identity_action": "use_cms_dob",
        "counsel_classification": "appointed_private",
        "audit_flags": ["apd_label_not_public_defender"],
        "recommended_resolution": "use_corrob_memo",
    },
    "UC-25-0221": {
        "dob_for_entry": "1995-03-12",
        "identity_action": "use_cms_dob",
        "counsel_classification": "retained",
        "audit_flags": ["amended_non_lab_conviction"],
        "recommended_resolution": "use_hearing_notes",
    },
    "UC-25-0224": {
        "dob_for_entry": "1984-08-02",
        "identity_action": "use_cms_dob",
        "counsel_classification": "public_defender",
        "audit_flags": ["lab_fee_worksheet_omitted"],
        "recommended_resolution": "use_hearing_notes",
    },
    "UC-25-0230": {
        "dob_for_entry": "TBD from case file",
        "identity_action": "use_placeholder_verify",
        "counsel_classification": "retained",
        "audit_flags": ["dob_missing_verify"],
        "recommended_resolution": "verify_before_entry",
    },
    "UC-25-0238": {
        "dob_for_entry": "2002-12-11",
        "identity_action": "exclude_pending",
        "counsel_classification": "public_defender",
        "audit_flags": ["no_final_order_pending"],
        "recommended_resolution": "exclude_pending",
    },
}

EXPECTED_DISPOSITIONS = {
    "UC-24-0775": ("disposed_enter", "2025-05-20", "bench_trial_guilty", "not_applicable", 1, 0, "none"),
    "UC-25-0221": ("disposed_enter", "2025-05-20", "guilty_plea", "guilty", 1, 1, "not_evaluated_misdemeanor"),
    "UC-25-0224": ("disposed_enter", "2025-05-20", "no_contest_guilty", "no_contest", 1, 0, "none"),
    "UC-25-0230": ("disposed_enter", "2025-05-20", "guilty_plea", "guilty", 1, 0, "not_evaluated_misdemeanor"),
    "UC-25-0238": ("pending_exclude", None, "continued_pending", "not_entered", 0, 0, "not_entered_pending"),
}

EXPECTED_FEES = {
    "UC-24-0775": ("post", 150.0, 0.0, 500.0, 650.0),
    "UC-25-0221": ("post", 150.0, 0.0, 0.0, 150.0),
    "UC-25-0224": ("post", 150.0, 75.0, 0.0, 225.0),
    "UC-25-0230": ("post", 150.0, 0.0, 0.0, 150.0),
    "UC-25-0238": ("do_not_post_pending", 0.0, 0.0, 0.0, 0.0),
}

EXPECTED_REGISTER = {
    "UC-24-0775": ("enter_disposition_and_financials", "SENTENCING_ORDER_ENTERED", "2025-05-20"),
    "UC-25-0221": ("enter_disposition_and_financials", "SENTENCING_ORDER_ENTERED", "2025-05-20"),
    "UC-25-0224": ("enter_disposition_and_financials", "SENTENCING_ORDER_ENTERED", "2025-05-20"),
    "UC-25-0230": ("enter_disposition_and_financials", "SENTENCING_ORDER_ENTERED", "2025-05-20"),
    "UC-25-0238": ("exclude_no_final_order", "CONTINUED_NO_DISPOSITION", None),
}

EXPECTED_TOTALS = {
    "disposed_case_count": 4,
    "excluded_pending_count": 1,
    "court_cost_total": 600.0,
    "crime_lab_fee_total": 75.0,
    "fine_total": 500.0,
    "batch_total_due": 1175.0,
}

POINTS = [
    ("SP001", "Correct disposed target set and pending exclusion set.", 2),
    (
        "SP002",
        "Correct audit resolutions for DOB, counsel, lab-fee omission, amendment, and pending status conflicts.",
        2,
    ),
    (
        "SP003",
        "Correct disposition outcomes, pleas, dates, count treatment, and departure statuses for all target cases.",
        3,
    ),
    (
        "SP004",
        "Correct court-cost and crime-lab fee postings per case, including lab fee only on the controlled-substance conviction.",
        3,
    ),
    (
        "SP005",
        "Correct fine and total-due amounts per case, including no financial posting for the continued matter.",
        2,
    ),
    ("SP006", "Correct docket/register action and docket code for each case.", 2),
    (
        "SP007",
        "Correct aggregate register totals for disposed cases, excluded cases, court costs, lab fees, fines, and batch total.",
        2,
    ),
    ("SP008", "Correct detailed exclusion record for UC-25-0238 with next status date and no financial posting.", 1),
]


def load_candidate(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as exc:
        return {"__load_error__": str(exc)}


def by_case(rows):
    if not isinstance(rows, list):
        return {}
    out = {}
    for row in rows:
        if isinstance(row, dict) and isinstance(row.get("case_number"), str):
            out[row["case_number"]] = row
    return out


def money_equal(actual, expected):
    try:
        return math.isclose(round(float(actual), 2), expected, abs_tol=0.005)
    except (TypeError, ValueError):
        return False


def sorted_list(value):
    if not isinstance(value, list):
        return []
    return sorted(str(v) for v in value)


def check_sp001(candidate):
    dispositions = by_case(candidate.get("dispositions"))
    disposed = {case for case, row in dispositions.items() if row.get("entry_status") == "disposed_enter"}
    pending = {case for case, row in dispositions.items() if row.get("entry_status") == "pending_exclude"}
    ok = disposed == DISPOSED and pending == PENDING and set(dispositions) == set(EXPECTED_CASES)
    return ok, f"disposed={sorted(disposed)} pending={sorted(pending)}"


def check_sp002(candidate):
    audit = by_case(candidate.get("case_audit"))
    failures = []
    for case, exp in EXPECTED_AUDIT.items():
        row = audit.get(case, {})
        for key, expected_value in exp.items():
            actual_value = sorted_list(row.get(key)) if key == "audit_flags" else row.get(key)
            expected_norm = sorted_list(expected_value) if key == "audit_flags" else expected_value
            if actual_value != expected_norm:
                failures.append(f"{case}.{key}")
    return not failures, "mismatches=" + ",".join(failures[:10])


def check_sp003(candidate):
    dispositions = by_case(candidate.get("dispositions"))
    failures = []
    keys = [
        "entry_status",
        "disposition_date",
        "primary_outcome",
        "plea",
        "convicted_counts",
        "dismissed_or_amended_away_counts",
        "departure_status",
    ]
    for case, expected_values in EXPECTED_DISPOSITIONS.items():
        row = dispositions.get(case, {})
        for key, expected_value in zip(keys, expected_values):
            if row.get(key) != expected_value:
                failures.append(f"{case}.{key}")
    return not failures, "mismatches=" + ",".join(failures[:12])


def check_sp004(candidate):
    fees = by_case(candidate.get("fee_entries"))
    failures = []
    for case, (_, court_cost, lab_fee, _, _) in EXPECTED_FEES.items():
        row = fees.get(case, {})
        if not money_equal(row.get("court_cost"), court_cost):
            failures.append(f"{case}.court_cost")
        if not money_equal(row.get("crime_lab_fee"), lab_fee):
            failures.append(f"{case}.crime_lab_fee")
        if row.get("fee_status") != EXPECTED_FEES[case][0]:
            failures.append(f"{case}.fee_status")
    return not failures, "mismatches=" + ",".join(failures[:12])


def check_sp005(candidate):
    fees = by_case(candidate.get("fee_entries"))
    failures = []
    for case, (_, _, _, fine, total) in EXPECTED_FEES.items():
        row = fees.get(case, {})
        if not money_equal(row.get("fine"), fine):
            failures.append(f"{case}.fine")
        if not money_equal(row.get("total_due"), total):
            failures.append(f"{case}.total_due")
    return not failures, "mismatches=" + ",".join(failures[:12])


def check_sp006(candidate):
    entries = by_case((candidate.get("docket_register") or {}).get("entries"))
    failures = []
    for case, (action, code, date) in EXPECTED_REGISTER.items():
        row = entries.get(case, {})
        if row.get("register_action") != action:
            failures.append(f"{case}.register_action")
        if row.get("docket_code") != code:
            failures.append(f"{case}.docket_code")
        if row.get("entry_date") != date:
            failures.append(f"{case}.entry_date")
    return not failures, "mismatches=" + ",".join(failures[:12])


def check_sp007(candidate):
    totals = (candidate.get("docket_register") or {}).get("totals") or {}
    failures = []
    for key, expected in EXPECTED_TOTALS.items():
        actual = totals.get(key)
        if isinstance(expected, float):
            if not money_equal(actual, expected):
                failures.append(key)
        elif actual != expected:
            failures.append(key)
    return not failures, "mismatches=" + ",".join(failures)


def check_sp008(candidate):
    exclusions = by_case(candidate.get("exclusions"))
    row = exclusions.get("UC-25-0238", {})
    ok = (
        set(exclusions) == {"UC-25-0238"}
        and row.get("exclusion_reason") == "continued_pending_no_final_order"
        and row.get("next_status_check_date") == "2025-06-17"
        and row.get("financial_posting_allowed") is False
    )
    return ok, f"exclusions={sorted(exclusions)}"


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
