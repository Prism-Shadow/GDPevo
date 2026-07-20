#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED_INCLUDED = ["MC-24-1109", "MC-25-0601", "MC-25-0604", "MC-25-0622"]
PENDING_CASE = "MC-25-0618"


EXPECTED_AUDIT = {
    ("MC-24-1109", "criminal_history_score"): {
        "recommended_resolution": "use_hearing_notes",
        "resolved_value": "5",
    },
    ("MC-24-1109", "counsel_type"): {
        "recommended_resolution": "use_cms",
        "resolved_value": "appointed_private",
    },
    ("MC-25-0601", "defendant_dob"): {
        "recommended_resolution": "use_cms",
        "resolved_value": "1987-02-18",
    },
}


EXPECTED_DISPOSITIONS = {
    "MC-24-1109": {
        "defendant_name": "Darren Mills",
        "dob": "1975-06-02",
        "counsel_type": "appointed_private",
        "criminal_history_score": 5,
        "case_status": "disposed",
        "charge": {
            "count_no": 1,
            "offense_code": "POSS-CS",
            "statute": "Ark. Code 5-64-419",
            "disposition": "deferred",
            "plea": "guilty",
            "departure_status": "dispositional_departure",
        },
        "sentence": {
            "jail_days_imposed": 0,
            "jail_days_suspended": 0,
            "probation_months": 6,
            "fine_ordered": 0.0,
        },
    },
    "MC-25-0601": {
        "defendant_name": "Caleb Foster",
        "dob": "1987-02-18",
        "counsel_type": "public_defender",
        "criminal_history_score": 2,
        "case_status": "disposed",
        "charge": {
            "count_no": 1,
            "offense_code": "FAIL-APP",
            "statute": "Ark. Code 5-54-120",
            "disposition": "guilty",
            "plea": "no contest",
            "departure_status": "no_departure",
        },
        "sentence": {
            "jail_days_imposed": 365,
            "jail_days_suspended": 300,
            "probation_months": 6,
            "fine_ordered": 1000.0,
        },
    },
    "MC-25-0604": {
        "defendant_name": "Priya Shah",
        "dob": "1993-09-20",
        "counsel_type": "retained",
        "criminal_history_score": 1,
        "case_status": "disposed",
        "charge": {
            "count_no": 1,
            "offense_code": "FLEEING",
            "statute": "Ark. Code 5-54-125",
            "disposition": "guilty",
            "plea": "guilty",
            "departure_status": "no_departure",
        },
        "sentence": {
            "jail_days_imposed": 365,
            "jail_days_suspended": 300,
            "probation_months": 24,
            "fine_ordered": 1000.0,
        },
    },
    "MC-25-0622": {
        "defendant_name": "Lydia Cho",
        "dob": "1981-12-08",
        "counsel_type": "retained",
        "criminal_history_score": 0,
        "case_status": "disposed",
        "charge": {
            "count_no": 1,
            "offense_code": "FAIL-APP",
            "statute": "Ark. Code 5-54-120",
            "disposition": "dismissed",
            "plea": "no contest",
            "departure_status": "not_applicable",
        },
        "sentence": {
            "jail_days_imposed": 0,
            "jail_days_suspended": 0,
            "probation_months": 0,
            "fine_ordered": 0.0,
        },
    },
}


EXPECTED_FINANCIALS = {
    "MC-24-1109": {
        "fine_total": 0.0,
        "mandatory_court_cost": 155.0,
        "unsupported_fee_total": 0.0,
        "amount_due": 155.0,
    },
    "MC-25-0601": {
        "fine_total": 1000.0,
        "mandatory_court_cost": 155.0,
        "unsupported_fee_total": 0.0,
        "amount_due": 1155.0,
    },
    "MC-25-0604": {
        "fine_total": 1000.0,
        "mandatory_court_cost": 155.0,
        "unsupported_fee_total": 0.0,
        "amount_due": 1155.0,
    },
    "MC-25-0622": {
        "fine_total": 0.0,
        "mandatory_court_cost": 155.0,
        "unsupported_fee_total": 0.0,
        "amount_due": 155.0,
    },
}


EXPECTED_RECONCILIATION = {
    ("MC-24-1109", "assessment", 0.0, "excluded_unsupported"),
    ("MC-24-1109", "court_cost", 155.0, "corrected_current_schedule"),
    ("MC-24-1109", "user_fee", 0.0, "excluded_unsupported"),
    ("MC-25-0601", "court_cost", 155.0, "corrected_current_schedule"),
    ("MC-25-0601", "user_fee", 0.0, "excluded_unsupported"),
    ("MC-25-0604", "court_cost", 155.0, "corrected_current_schedule"),
    ("MC-25-0618", "draft_financial", 0.0, "excluded_pending"),
    ("MC-25-0622", "court_cost", 155.0, "corrected_current_schedule"),
    ("MC-25-0622", "fine", 0.0, "waived_by_court"),
}


EXPECTED_DOCKETS = {
    ("MC-24-1109", "disposition", "deferred_order_entered", 0.0),
    ("MC-24-1109", "financial", "financial_obligation_entered", 155.0),
    ("MC-25-0601", "disposition", "sentencing_order_entered", 0.0),
    ("MC-25-0601", "financial", "financial_obligation_entered", 1155.0),
    ("MC-25-0604", "disposition", "sentencing_order_entered", 0.0),
    ("MC-25-0604", "financial", "financial_obligation_entered", 1155.0),
    ("MC-25-0622", "disposition", "dismissal_order_entered", 0.0),
    ("MC-25-0622", "financial", "financial_obligation_entered", 155.0),
}


EXPECTED_TOTALS = {
    "included_case_count": 4,
    "excluded_pending_count": 1,
    "disposition_entry_count": 4,
    "financial_entry_count": 4,
    "fine_total": 2000.0,
    "mandatory_court_cost_total": 620.0,
    "unsupported_fee_total": 0.0,
    "grand_total_due": 2620.0,
}


POINTS = [
    ("SP001", "Correct final case set and pending/draft matter exclusion.", 1),
    ("SP002", "Correct audit resolutions for DOB, criminal-history, and counsel/source conflicts.", 2),
    ("SP003", "Correct charge dispositions, pleas, sentences, counsel types, and criminal-history scores.", 3),
    ("SP004", "Correct per-case financial entries using mandatory Madison court costs and ordered fines.", 3),
    (
        "SP005",
        "Correctly treats stale worksheet fees, unsupported fee lines, pending draft amounts, and waived fine.",
        3,
    ),
    ("SP006", "Correct docket entries to post, including entry codes and no pending matter entry.", 1),
    ("SP007", "Correct sentencing register aggregate totals.", 3),
    ("SP008", "Correct controlled source-basis summary.", 1),
]


def money(value):
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def eq_money(a, b):
    return money(a) is not None and math.isclose(money(a), round(float(b), 2), abs_tol=0.005)


def load_candidate(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f), None
    except Exception as exc:
        return {}, f"{type(exc).__name__}: {exc}"


def by_case(rows):
    return {row.get("case_number"): row for row in rows if isinstance(row, dict)}


def check_inclusion(data):
    included = data.get("included_case_numbers")
    excluded = data.get("excluded_matters")
    if included != EXPECTED_INCLUDED:
        return False, f"included_case_numbers was {included!r}"
    if not isinstance(excluded, list) or len(excluded) != 1:
        return False, "excluded_matters must contain exactly one matter"
    item = excluded[0]
    ok = (
        item.get("case_number") == PENDING_CASE
        and item.get("status") == "pending"
        and item.get("exclusion_reason") == "pending_no_signed_order"
        and item.get("draft_disposition_entry") == "do_not_post"
    )
    if not ok:
        return False, f"excluded matter was {item!r}"
    for key in ("case_dispositions", "financial_entries", "docket_entries"):
        rows = data.get(key, [])
        if any(isinstance(row, dict) and row.get("case_number") == PENDING_CASE for row in rows):
            return False, f"{PENDING_CASE} appears in {key}"
    return True, "included four disposed cases and excluded MC-25-0618 as pending/no signed order"


def check_audit(data):
    rows = data.get("audit_findings", [])
    if not isinstance(rows, list):
        return False, "audit_findings is not a list"
    found = {(row.get("case_number"), row.get("field_name")): row for row in rows if isinstance(row, dict)}
    missing = []
    for key, expected in EXPECTED_AUDIT.items():
        row = found.get(key)
        if not row:
            missing.append(f"{key}: missing")
            continue
        for field, value in expected.items():
            if str(row.get(field)) != str(value):
                missing.append(f"{key}: {field}={row.get(field)!r}")
    if missing:
        return False, "; ".join(missing)
    return True, "audit findings resolve the DOB, criminal-history, and counsel/source conflicts"


def nested_matches(actual, expected, path=""):
    for key, value in expected.items():
        here = f"{path}.{key}" if path else key
        if isinstance(value, dict):
            if not isinstance(actual.get(key), dict):
                return False, f"{here} missing or not object"
            ok, detail = nested_matches(actual[key], value, here)
            if not ok:
                return ok, detail
        elif isinstance(value, float):
            if not eq_money(actual.get(key), value):
                return False, f"{here} expected {value}, got {actual.get(key)!r}"
        else:
            if actual.get(key) != value:
                return False, f"{here} expected {value!r}, got {actual.get(key)!r}"
    return True, "matched"


def check_dispositions(data):
    rows = by_case(data.get("case_dispositions", []))
    if set(rows) != set(EXPECTED_DISPOSITIONS):
        return False, f"case_dispositions cases were {sorted(rows)}"
    for case_number, expected in EXPECTED_DISPOSITIONS.items():
        ok, detail = nested_matches(rows[case_number], expected, case_number)
        if not ok:
            return False, detail
    return True, "all included case dispositions and sentence fields match"


def check_financials(data):
    rows = by_case(data.get("financial_entries", []))
    if set(rows) != set(EXPECTED_FINANCIALS):
        return False, f"financial_entries cases were {sorted(rows)}"
    for case_number, expected in EXPECTED_FINANCIALS.items():
        ok, detail = nested_matches(rows[case_number], expected, case_number)
        if not ok:
            return False, detail
    return True, "per-case fine, current court cost, unsupported fee, and amount due values match"


def check_reconciliation(data):
    rows = data.get("fee_reconciliation", [])
    if not isinstance(rows, list):
        return False, "fee_reconciliation is not a list"
    actual = {
        (
            row.get("case_number"),
            row.get("line_type"),
            money(row.get("approved_amount")),
            row.get("status"),
        )
        for row in rows
        if isinstance(row, dict)
    }
    if actual != EXPECTED_RECONCILIATION:
        return False, (
            "reconciliation set mismatch; "
            f"expected {sorted(EXPECTED_RECONCILIATION, key=str)}, got {sorted(actual, key=str)}"
        )
    return True, "worksheet traps and corrected/excluded/waived statuses match"


def check_dockets(data):
    rows = data.get("docket_entries", [])
    if not isinstance(rows, list):
        return False, "docket_entries is not a list"
    actual = {
        (
            row.get("case_number"),
            row.get("entry_type"),
            row.get("entry_code"),
            money(row.get("amount_due")),
        )
        for row in rows
        if isinstance(row, dict) and row.get("entry_date") == "2025-07-14"
    }
    if actual != EXPECTED_DOCKETS:
        return False, (
            f"docket entry set mismatch; expected {sorted(EXPECTED_DOCKETS, key=str)}, got {sorted(actual, key=str)}"
        )
    if any(isinstance(row, dict) and row.get("case_number") == PENDING_CASE for row in rows):
        return False, f"{PENDING_CASE} should not have a docket entry"
    return True, "docket disposition and financial entries match for the four included cases"


def check_totals(data):
    totals = data.get("register_totals", {})
    if not isinstance(totals, dict):
        return False, "register_totals is not an object"
    for key, expected in EXPECTED_TOTALS.items():
        actual = totals.get(key)
        if isinstance(expected, float):
            if not eq_money(actual, expected):
                return False, f"{key} expected {expected}, got {actual!r}"
        elif actual != expected:
            return False, f"{key} expected {expected!r}, got {actual!r}"
    return True, "register count and currency totals match"


def check_source_summary(data):
    expected = {
        "case_record_basis": "portal_plus_hearing_notes",
        "fee_schedule_basis": "current_portal_schedule",
        "pending_matter_handling": "exclude_from_final_entries",
    }
    summary = data.get("source_summary", {})
    if not isinstance(summary, dict):
        return False, "source_summary is not an object"
    for key, value in expected.items():
        if summary.get(key) != value:
            return False, f"{key} expected {value!r}, got {summary.get(key)!r}"
    return True, "source-basis summary uses controlled values correctly"


CHECKS = [
    check_inclusion,
    check_audit,
    check_dispositions,
    check_financials,
    check_reconciliation,
    check_dockets,
    check_totals,
    check_source_summary,
]


def main():
    default_path = Path(__file__).resolve().parents[1] / "output" / "answer.json"
    candidate_path = Path(sys.argv[1]) if len(sys.argv) > 1 else default_path
    data, load_error = load_candidate(candidate_path)

    total_weight = sum(weight for _, _, weight in POINTS)
    point_results = []
    for (point_id, goal, weight), check in zip(POINTS, CHECKS):
        assigned = weight / total_weight
        if load_error:
            passed = False
            details = f"candidate JSON could not be loaded: {load_error}"
        else:
            passed, details = check(data)
        point_results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": round(assigned, 6),
                "passed": bool(passed),
                "earned": round(assigned if passed else 0.0, 6),
                "details": details,
            }
        )

    score = round(min(1.0, sum(point["earned"] for point in point_results)), 6)
    print(json.dumps({"score": score, "points": point_results}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
