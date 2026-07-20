#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


WEIGHTS = {
    "SP001": 2,
    "SP002": 2,
    "SP003": 2,
    "SP004": 2,
    "SP005": 2,
    "SP006": 3,
    "SP007": 2,
    "SP008": 2,
}
TOTAL_WEIGHT = sum(WEIGHTS.values())

EXPECTED_LABELS = {
    "Case # / Account #",
    "Case/Account Balance",
    "Action Table(s) / Notes",
    "TERMS of PAYMENT",
}

EXPECTED_EXCLUSIONS = {
    "account_management_fee": {"applies_to": "all", "reason_code": "not_current_policy"},
    "collection_fee": {"applies_to": "all", "reason_code": "no_triggering_event"},
    "dmv_fee": {"applies_to": "all", "reason_code": "no_triggering_event"},
    "late_payment_fee": {"applies_to": "all", "reason_code": "no_triggering_event"},
    "returned_check_fee": {"applies_to": "all", "reason_code": "no_triggering_event"},
    "stale_2022_standard_fine": {"applies_to": "OR26-TR-1188", "reason_code": "stale_schedule"},
    "statutory_maximum_substitution": {
        "applies_to": "OR26-TR-1188",
        "reason_code": "unsupported_post_disposition",
    },
    "traffic_school_fee": {"applies_to": "all", "reason_code": "not_in_hearing_order"},
}

EXPECTED = {
    "OR26-TR-1188": {
        "jurisdiction_code": "OR22-JEFF",
        "defendant_name": "Sarah Benton",
        "disposition": {
            "plea": "no_contest",
            "finding": "violation_found",
            "disposition_date": "2026-11-12",
            "agreement_sequence": "post_disposition",
        },
        "financial_entry": {
            "violation_code": "ORS_811_109_100PLUS",
            "fine_tier": "speed_100_or_greater",
            "fee_schedule_source": "F-OR22-100-2024",
            "standard_fine": 1150.0,
            "county_surcharge": 5.0,
            "amount_due": 1155.0,
            "unsupported_charge_total_included": 0.0,
        },
        "payment_plan": {
            "plan_status": "approved",
            "agreement_type": "extended_payment_plan",
            "monthly_payment": 50.0,
            "down_payment": 0.0,
            "first_due_date": "2026-12-15",
            "full_payment_count": 23,
            "final_payment_amount": 5.0,
            "total_installments": 24,
            "final_due_date": "2028-11-15",
        },
    },
    "OR26-TR-1194": {
        "jurisdiction_code": "OR22-JEFF",
        "defendant_name": "Jonah Merritt",
        "disposition": {
            "plea": "no_contest",
            "finding": "violation_found",
            "disposition_date": "2026-11-12",
            "agreement_sequence": "post_disposition",
        },
        "financial_entry": {
            "violation_code": "ORS_811_109_31_40",
            "fine_tier": "speed_31_to_40_over",
            "fee_schedule_source": "F-OR22-31-2024",
            "standard_fine": 440.0,
            "county_surcharge": 5.0,
            "amount_due": 445.0,
            "unsupported_charge_total_included": 0.0,
        },
        "payment_plan": {
            "plan_status": "approved",
            "agreement_type": "extended_payment_plan",
            "monthly_payment": 55.0,
            "down_payment": 0.0,
            "first_due_date": "2026-12-15",
            "full_payment_count": 8,
            "final_payment_amount": 5.0,
            "total_installments": 9,
            "final_due_date": "2027-08-15",
        },
    },
}


def money_equal(actual, expected):
    try:
        return math.isclose(round(float(actual), 2), round(float(expected), 2), abs_tol=0.005)
    except (TypeError, ValueError):
        return False


def exact(actual, expected):
    return actual == expected


def nested_get(obj, *keys):
    cur = obj
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def load_candidate(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8")), None
    except Exception as exc:
        return None, str(exc)


def matters_by_citation(data):
    matters = data.get("matters") if isinstance(data, dict) else None
    if not isinstance(matters, list):
        return {}
    out = {}
    for item in matters:
        if isinstance(item, dict) and isinstance(item.get("citation_number"), str):
            out[item["citation_number"]] = item
    return out


def check_fields(matter, section, expected_fields):
    for key, expected in expected_fields.items():
        actual = nested_get(matter, section, key) if section else matter.get(key)
        if isinstance(expected, float):
            if not money_equal(actual, expected):
                return False, f"{key}: expected {expected}, got {actual!r}"
        elif isinstance(expected, int):
            if actual != expected:
                return False, f"{key}: expected {expected}, got {actual!r}"
        elif actual != expected:
            return False, f"{key}: expected {expected!r}, got {actual!r}"
    return True, "ok"


def point(pid, goal, passed, details):
    assigned = WEIGHTS[pid] / TOTAL_WEIGHT
    return {
        "id": pid,
        "goal": goal,
        "weight": WEIGHTS[pid],
        "assigned_score": round(assigned, 6),
        "passed": bool(passed),
        "earned": round(assigned if passed else 0.0, 6),
        "details": details,
    }


def evaluate(data):
    pts = []
    matters = matters_by_citation(data)
    target_set = set(EXPECTED)

    sp001_ok = set(matters) == target_set
    sp001_detail = "target citation set matched"
    if sp001_ok:
        for citation, expected in EXPECTED.items():
            matter = matters[citation]
            ok_top, detail_top = check_fields(
                matter,
                None,
                {
                    "jurisdiction_code": expected["jurisdiction_code"],
                    "defendant_name": expected["defendant_name"],
                },
            )
            ok_disp, detail_disp = check_fields(matter, "disposition", expected["disposition"])
            if not (ok_top and ok_disp):
                sp001_ok = False
                sp001_detail = f"{citation}: {detail_top if not ok_top else detail_disp}"
                break
    else:
        sp001_detail = f"expected citations {sorted(target_set)}, got {sorted(matters)}"
    pts.append(
        point(
            "SP001",
            "Correctly identifies both target matters and records no-contest violation-found post-disposition closeout.",
            sp001_ok,
            sp001_detail,
        )
    )

    for pid, citation, goal in [
        ("SP002", "OR26-TR-1188", "Correct current standard fine tier for OR26-TR-1188."),
        ("SP003", "OR26-TR-1194", "Correct current standard fine tier for OR26-TR-1194."),
    ]:
        matter = matters.get(citation, {})
        expected_fields = {
            k: EXPECTED[citation]["financial_entry"][k]
            for k in ["violation_code", "fine_tier", "fee_schedule_source", "standard_fine"]
        }
        ok, detail = check_fields(matter, "financial_entry", expected_fields)
        pts.append(point(pid, goal, ok, f"{citation}: {detail}"))

    sp004_ok = True
    sp004_detail = "surcharges, per-citation balances, and batch total matched"
    for citation in EXPECTED:
        matter = matters.get(citation, {})
        expected_fields = {
            "county_surcharge": EXPECTED[citation]["financial_entry"]["county_surcharge"],
            "amount_due": EXPECTED[citation]["financial_entry"]["amount_due"],
        }
        ok, detail = check_fields(matter, "financial_entry", expected_fields)
        if not ok:
            sp004_ok = False
            sp004_detail = f"{citation}: {detail}"
            break
    batch = data.get("batch_totals", {}) if isinstance(data, dict) else {}
    if sp004_ok and not (batch.get("matter_count") == 2 and money_equal(batch.get("combined_amount_due"), 1600.0)):
        sp004_ok = False
        sp004_detail = f"batch_totals expected matter_count 2 and combined_amount_due 1600.0, got {batch!r}"
    pts.append(
        point(
            "SP004",
            "Applies the Jefferson County surcharge once per citation and calculates amount due totals.",
            sp004_ok,
            sp004_detail,
        )
    )

    sp005_ok = True
    sp005_detail = "payment status, type, monthly amount, first due date, and down payment matched"
    for citation in EXPECTED:
        expected_fields = {
            k: EXPECTED[citation]["payment_plan"][k]
            for k in ["plan_status", "agreement_type", "monthly_payment", "down_payment", "first_due_date"]
        }
        ok, detail = check_fields(matters.get(citation, {}), "payment_plan", expected_fields)
        if not ok:
            sp005_ok = False
            sp005_detail = f"{citation}: {detail}"
            break
    pts.append(
        point(
            "SP005",
            "Records approved post-disposition extended payment-plan terms for both citations.",
            sp005_ok,
            sp005_detail,
        )
    )

    sp006_ok = True
    sp006_detail = "installment counts, final remainder payments, and final due dates matched"
    for citation in EXPECTED:
        expected_fields = {
            k: EXPECTED[citation]["payment_plan"][k]
            for k in ["full_payment_count", "final_payment_amount", "total_installments", "final_due_date"]
        }
        ok, detail = check_fields(matters.get(citation, {}), "payment_plan", expected_fields)
        if not ok:
            sp006_ok = False
            sp006_detail = f"{citation}: {detail}"
            break
    pts.append(
        point(
            "SP006",
            "Computes full installment count, final partial payment, total installments, and final due date.",
            sp006_ok,
            sp006_detail,
        )
    )

    sp007_ok = True
    sp007_detail = "form id, form label, account references, and required labels matched"
    for citation, matter in matters.items():
        form = matter.get("form_entry", {}) if isinstance(matter, dict) else {}
        labels = (
            set(form.get("required_labels_used", [])) if isinstance(form.get("required_labels_used"), list) else set()
        )
        if (
            form.get("form_id") != "OR_22JD_PLAN"
            or form.get("form_label") != "extended_payment_plan_agreement"
            or form.get("account_reference") != citation
            or labels != EXPECTED_LABELS
        ):
            sp007_ok = False
            sp007_detail = f"{citation}: got form_entry {form!r}"
            break
    if set(matters) != target_set:
        sp007_ok = False
        sp007_detail = "target matters missing, cannot verify form entries"
    pts.append(
        point(
            "SP007",
            "Uses the 22nd Judicial District form label, labels, and citation number as account reference.",
            sp007_ok,
            sp007_detail,
        )
    )

    exclusions = data.get("excluded_charges", []) if isinstance(data, dict) else []
    by_code = {item.get("charge_code"): item for item in exclusions if isinstance(item, dict)}
    sp008_ok = set(EXPECTED_EXCLUSIONS).issubset(by_code)
    sp008_detail = "all required excluded stale or unsupported charges were listed with correct reasons"
    if sp008_ok:
        for code, expected in EXPECTED_EXCLUSIONS.items():
            item = by_code[code]
            for key, expected_value in expected.items():
                if item.get(key) != expected_value:
                    sp008_ok = False
                    sp008_detail = f"{code}: expected {key} {expected_value!r}, got {item.get(key)!r}"
                    break
            if not sp008_ok:
                break
    else:
        missing = sorted(set(EXPECTED_EXCLUSIONS) - set(by_code))
        sp008_detail = f"missing excluded charge codes {missing}"
    if sp008_ok:
        unsupported_totals = [
            nested_get(m, "financial_entry", "unsupported_charge_total_included") for m in matters.values()
        ]
        unsupported_totals.append((data.get("batch_totals") or {}).get("unsupported_charge_total_included"))
        if not all(money_equal(value, 0.0) for value in unsupported_totals):
            sp008_ok = False
            sp008_detail = f"unsupported charge totals should be zero, got {unsupported_totals!r}"
    pts.append(
        point(
            "SP008",
            "Excludes stale schedule amounts and unsupported late, collection, DMV, returned-check, account, and traffic-school charges.",
            sp008_ok,
            sp008_detail,
        )
    )

    score = round(sum(p["earned"] for p in pts), 6)
    return {"score": score, "points": pts}


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"score": 0.0, "error": "Usage: eval.py /path/to/answer.json"}))
        sys.exit(2)
    data, err = load_candidate(sys.argv[1])
    if err is not None:
        pts = [
            point(pid, goal, False, f"Could not parse candidate JSON: {err}")
            for pid, goal in [
                (
                    "SP001",
                    "Correctly identifies both target matters and records no-contest violation-found post-disposition closeout.",
                ),
                ("SP002", "Correct current standard fine tier for OR26-TR-1188."),
                ("SP003", "Correct current standard fine tier for OR26-TR-1194."),
                (
                    "SP004",
                    "Applies the Jefferson County surcharge once per citation and calculates amount due totals.",
                ),
                ("SP005", "Records approved post-disposition extended payment-plan terms for both citations."),
                (
                    "SP006",
                    "Computes full installment count, final partial payment, total installments, and final due date.",
                ),
                (
                    "SP007",
                    "Uses the 22nd Judicial District form label, labels, and citation number as account reference.",
                ),
                (
                    "SP008",
                    "Excludes stale schedule amounts and unsupported late, collection, DMV, returned-check, account, and traffic-school charges.",
                ),
            ]
        ]
        print(json.dumps({"score": 0.0, "points": pts}, indent=2, sort_keys=True))
        return
    print(json.dumps(evaluate(data), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
