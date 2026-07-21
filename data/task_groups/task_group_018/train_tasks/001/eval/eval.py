#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


WEIGHTS = {
    "SP001": 2,
    "SP002": 2,
    "SP003": 3,
    "SP004": 2,
    "SP005": 3,
    "SP006": 2,
    "SP007": 2,
    "SP008": 2,
}

GOALS = {
    "SP001": "Correct audit findings for identity, counsel, fee schedule, departure, and unsigned-order conflicts.",
    "SP002": "Correct identity and counsel values for all four target cases.",
    "SP003": "Correct disposition status, closeout action, and disposition date decisions for all four cases.",
    "SP004": "Correct charge outcome, sentence, fine, and departure classifications for all four cases.",
    "SP005": "Correct fee item inclusion and exclusion for each case.",
    "SP006": "Correct per-case reconciled financial totals.",
    "SP007": "Correct docket entry type and summary code for each case.",
    "SP008": "Correct criminal register aggregate counts and dollar totals.",
}

EXPECTED_AUDIT = {
    ("RC-24-0987", "departure", "no_departure", "use_hearing_notes"),
    ("RC-25-0412", "counsel", "appointed_private lena ortiz", "use_corrob_memo"),
    ("RC-25-0412", "identity", "evan simmons dob 1991-04-18", "use_cms"),
    ("RC-25-0418", "fee_schedule", "drug_assessment 250 plus public_defender_user_fee 200", "use_fee_schedule"),
    ("RC-25-0502", "status", "deferred hold_unsigned_order", "hold_unsigned_order"),
}

EXPECTED_IDENTITY_COUNSEL = {
    "RC-24-0987": ("Tanya Morales", "1979-07-03", "retained", "James Pell"),
    "RC-25-0412": ("Evan Simmons", "1991-04-18", "appointed_private", "Lena Ortiz"),
    "RC-25-0418": ("Marisol Vega", "1988-11-22", "public_defender", "C. Hill"),
    "RC-25-0502": ("Nolan Reed", "2000-01-09", "public_defender", "C. Hill"),
}

EXPECTED_STATUS = {
    "RC-24-0987": ("disposed", "enter_disposition", "2025-06-09"),
    "RC-25-0412": ("disposed", "enter_disposition", "2025-06-09"),
    "RC-25-0418": ("disposed", "enter_disposition", "2025-06-09"),
    "RC-25-0502": ("deferred", "hold_unsigned_order", "2025-06-09"),
}

EXPECTED_CHARGES = {
    "RC-24-0987": {
        "offense_code": "THEFT-CLASS-D",
        "plea": "not guilty",
        "charge_disposition": "guilty",
        "fine_amount": 500.0,
        "jail_days_imposed": 365,
        "jail_days_suspended": 335,
        "probation_months": 24,
        "departure_status": "no_departure",
    },
    "RC-25-0412": {
        "offense_code": "FLEEING",
        "plea": "guilty",
        "charge_disposition": "guilty",
        "fine_amount": 0.0,
        "jail_days_imposed": 0,
        "jail_days_suspended": 30,
        "probation_months": 0,
        "departure_status": "not_applicable",
    },
    "RC-25-0418": {
        "offense_code": "POSS-CS",
        "plea": "no contest",
        "charge_disposition": "guilty",
        "fine_amount": 250.0,
        "jail_days_imposed": 30,
        "jail_days_suspended": 300,
        "probation_months": 0,
        "departure_status": "dispositional_departure",
    },
    "RC-25-0502": {
        "offense_code": "FAIL-APP",
        "plea": "not guilty",
        "charge_disposition": "pending",
        "fine_amount": 0.0,
        "jail_days_imposed": 0,
        "jail_days_suspended": 0,
        "probation_months": 0,
        "departure_status": "not_applicable",
    },
}

EXPECTED_FEE_ITEMS = {
    "RC-24-0987": {("fine", 500.0), ("court_cost", 150.0)},
    "RC-25-0412": {("court_cost", 150.0)},
    "RC-25-0418": {
        ("fine", 250.0),
        ("court_cost", 150.0),
        ("drug_assessment", 250.0),
        ("public_defender_user_fee", 200.0),
    },
    "RC-25-0502": set(),
}

EXPECTED_FEE_STATUS = {
    "RC-24-0987": "post",
    "RC-25-0412": "post",
    "RC-25-0418": "post",
    "RC-25-0502": "hold",
}

EXPECTED_CASE_TOTALS = {
    "RC-24-0987": 650.0,
    "RC-25-0412": 150.0,
    "RC-25-0418": 850.0,
    "RC-25-0502": 0.0,
}

EXPECTED_DOCKET = {
    "RC-24-0987": ("sentencing_order", "conviction_no_departure", 650.0),
    "RC-25-0412": ("sentencing_order", "conviction_no_pd_fee", 150.0),
    "RC-25-0418": ("sentencing_order", "conviction_drug_assessment", 850.0),
    "RC-25-0502": ("disposition_hold", "hold_unsigned_order", 0.0),
}

EXPECTED_TOTALS = {
    "assessed_case_count": 3,
    "held_case_count": 1,
    "fine_total": 750.0,
    "court_cost_total": 450.0,
    "assessment_total": 250.0,
    "user_fee_total": 200.0,
    "grand_total": 1650.0,
}


def norm_text(value):
    return (
        " ".join(str(value).strip().lower().replace("_", " ").split()).replace(" ", "_") if value is not None else ""
    )


def norm_value(value):
    return " ".join(str(value).strip().lower().split())


def money(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def is_money(value, expected):
    actual = money(value)
    return actual is not None and math.isclose(actual, round(expected, 2), abs_tol=0.005)


def by_case(items, key="case_number"):
    if not isinstance(items, list):
        return {}
    result = {}
    for item in items:
        if isinstance(item, dict) and item.get(key):
            result[str(item[key])] = item
    return result


def check_audit(data):
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
                norm_text(item.get("issue_type")),
                norm_value(item.get("corrected_value")),
                norm_text(item.get("resolution_source")),
            )
        )
    expected = {(a, norm_text(b), norm_value(c), norm_text(d)) for a, b, c, d in EXPECTED_AUDIT}
    return actual == expected, f"expected {len(expected)} exact normalized audit findings; got {len(actual)}"


def check_identity_counsel(data):
    cases = by_case(data.get("case_dispositions"))
    failures = []
    for case, expected in EXPECTED_IDENTITY_COUNSEL.items():
        item = cases.get(case, {})
        actual = (
            item.get("defendant_name"),
            item.get("dob"),
            norm_text(item.get("counsel_type")),
            item.get("attorney_name"),
        )
        wanted = (expected[0], expected[1], norm_text(expected[2]), expected[3])
        if actual != wanted:
            failures.append(case)
    return not failures, "identity/counsel mismatches: " + ", ".join(
        failures
    ) if failures else "all target identity/counsel values match"


def check_status(data):
    cases = by_case(data.get("case_dispositions"))
    failures = []
    for case, expected in EXPECTED_STATUS.items():
        item = cases.get(case, {})
        actual = (
            norm_text(item.get("case_status")),
            norm_text(item.get("closeout_action")),
            item.get("disposition_date"),
        )
        wanted = (norm_text(expected[0]), norm_text(expected[1]), expected[2])
        if actual != wanted:
            failures.append(case)
    return not failures, "status/action mismatches: " + ", ".join(
        failures
    ) if failures else "all target status/action values match"


def check_charges(data):
    cases = by_case(data.get("case_dispositions"))
    failures = []
    for case, expected in EXPECTED_CHARGES.items():
        charge = cases.get(case, {}).get("charge_summary", {})
        if not isinstance(charge, dict):
            failures.append(case)
            continue
        ok = True
        for key, wanted in expected.items():
            actual = charge.get(key)
            if isinstance(wanted, float):
                ok = ok and is_money(actual, wanted)
            elif isinstance(wanted, int):
                ok = ok and int_or_none(actual) == wanted
            elif key in {"plea", "charge_disposition", "departure_status"}:
                ok = ok and norm_text(actual) == norm_text(wanted)
            else:
                ok = ok and actual == wanted
        if not ok:
            failures.append(case)
    return not failures, "charge/sentence mismatches: " + ", ".join(
        failures
    ) if failures else "all charge summaries match"


def check_fee_items(data):
    recs = by_case(data.get("fee_reconciliation"))
    failures = []
    for case, expected in EXPECTED_FEE_ITEMS.items():
        rec = recs.get(case, {})
        status_ok = norm_text(rec.get("fee_status")) == norm_text(EXPECTED_FEE_STATUS[case])
        items = rec.get("fee_items", [])
        actual = set()
        if isinstance(items, list):
            for item in items:
                if isinstance(item, dict):
                    amount = money(item.get("amount"))
                    if amount is not None:
                        actual.add((norm_text(item.get("fee_code")), amount))
        expected_norm = {(norm_text(code), round(amount, 2)) for code, amount in expected}
        if actual != expected_norm or not status_ok:
            failures.append(case)
    return not failures, "fee item/status mismatches: " + ", ".join(
        failures
    ) if failures else "all fee items and statuses match"


def check_case_totals(data):
    recs = by_case(data.get("fee_reconciliation"))
    failures = []
    for case, expected in EXPECTED_CASE_TOTALS.items():
        if not is_money(recs.get(case, {}).get("case_total"), expected):
            failures.append(case)
    return not failures, "case total mismatches: " + ", ".join(failures) if failures else "all case totals match"


def check_docket(data):
    entries = by_case(data.get("docket_entries"))
    failures = []
    for case, expected in EXPECTED_DOCKET.items():
        item = entries.get(case, {})
        actual = (
            norm_text(item.get("docket_entry_type")),
            norm_text(item.get("summary_code")),
            money(item.get("financial_total")),
        )
        wanted = (norm_text(expected[0]), norm_text(expected[1]), round(expected[2], 2))
        if actual != wanted:
            failures.append(case)
    return not failures, "docket mismatches: " + ", ".join(failures) if failures else "all docket entries match"


def check_totals(data):
    totals = data.get("register_totals", {})
    if not isinstance(totals, dict):
        return False, "register_totals is not an object"
    failures = []
    for key, expected in EXPECTED_TOTALS.items():
        actual = totals.get(key)
        if isinstance(expected, int):
            ok = int_or_none(actual) == expected
        else:
            ok = is_money(actual, expected)
        if not ok:
            failures.append(key)
    return not failures, "register total mismatches: " + ", ".join(failures) if failures else "register totals match"


CHECKS = {
    "SP001": check_audit,
    "SP002": check_identity_counsel,
    "SP003": check_status,
    "SP004": check_charges,
    "SP005": check_fee_items,
    "SP006": check_case_totals,
    "SP007": check_docket,
    "SP008": check_totals,
}


def main():
    candidate_path = (
        Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / "output" / "answer.json"
    )
    try:
        data = json.loads(candidate_path.read_text())
    except Exception as exc:
        total_weight = sum(WEIGHTS.values())
        points = []
        for point_id, weight in WEIGHTS.items():
            assigned = weight / total_weight
            points.append(
                {
                    "id": point_id,
                    "goal": GOALS[point_id],
                    "weight": weight,
                    "assigned_score": round(assigned, 6),
                    "passed": False,
                    "earned": 0,
                    "details": f"Could not parse candidate JSON: {exc}",
                }
            )
        print(json.dumps({"score": 0, "points": points}, indent=2))
        return

    total_weight = sum(WEIGHTS.values())
    points = []
    score = 0.0
    for point_id, weight in WEIGHTS.items():
        assigned = weight / total_weight
        passed, details = CHECKS[point_id](data)
        earned = assigned if passed else 0.0
        score += earned
        points.append(
            {
                "id": point_id,
                "goal": GOALS[point_id],
                "weight": weight,
                "assigned_score": round(assigned, 6),
                "passed": bool(passed),
                "earned": round(earned, 6),
                "details": details,
            }
        )
    print(json.dumps({"score": round(score, 6), "points": points}, indent=2))


if __name__ == "__main__":
    main()
