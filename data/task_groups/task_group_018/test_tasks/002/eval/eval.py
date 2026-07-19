#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


WEIGHTS = {
    "SP001": 1,
    "SP002": 1,
    "SP003": 1,
    "SP004": 1,
    "SP005": 1,
    "SP006": 1,
    "SP007": 2,
    "SP008": 3,
    "SP009": 3,
}
TOTAL_WEIGHT = sum(WEIGHTS.values())

EXPECTED_LABELS = {
    "Citation #",
    "Account Reference",
    "Total Balance Due",
    "Payment Schedule",
    "Clerk Notes",
}

EXPECTED_EXCLUSIONS = {
    "account_management_fee": {"applies_to": "all", "reason_code": "not_current_policy"},
    "collection_fee": {"applies_to": "all", "reason_code": "no_triggering_event"},
    "copied_high_speed_fine_on_dismissal": {
        "applies_to": "OR27-TR-2219",
        "reason_code": "dismissed_no_financial_entry",
    },
    "dmv_fee": {"applies_to": "all", "reason_code": "no_triggering_event"},
    "late_payment_fee": {"applies_to": "all", "reason_code": "no_triggering_event"},
    "returned_check_fee": {"applies_to": "all", "reason_code": "no_triggering_event"},
    "traffic_school_fee": {"applies_to": "all", "reason_code": "not_in_hearing_order"},
    "work_zone_multiplier": {"applies_to": "OR27-TR-2201", "reason_code": "unsupported_enhancement"},
}

EXPECTED = {
    "OR27-TR-2201": {
        "jurisdiction_code": "OR27-CLAT",
        "defendant_name": "Mina Patel",
        "disposition": {
            "plea": "no_contest",
            "finding": "violation_found",
            "disposition_date": "2027-03-24",
            "agreement_sequence": "post_disposition",
        },
        "financial_entry": {
            "violation_code": "ORS_811_109_100PLUS",
            "fine_tier": "speed_100_or_greater",
            "fee_schedule_source": "F-OR27-100-2025",
            "standard_fine": 1200.0,
            "county_surcharge": 10.0,
            "amount_due": 1210.0,
            "unsupported_charge_total_included": 0.0,
        },
        "payment_plan": {
            "plan_status": "approved",
            "agreement_type": "extended_payment_plan",
            "monthly_payment": 110.0,
            "down_payment": 0.0,
            "first_due_date": "2027-04-23",
            "full_payment_count": 11,
            "final_payment_amount": 0.0,
            "total_installments": 11,
            "final_due_date": "2028-02-23",
        },
        "form_entry": {
            "form_id": "OR_27JD_PLAN",
            "form_label": "payment_plan_agreement",
            "account_reference": "OR27-TR-2201",
            "required_labels_used": EXPECTED_LABELS,
        },
    },
    "OR27-TR-2208": {
        "jurisdiction_code": "OR27-CLAT",
        "defendant_name": "Victor Lane",
        "disposition": {
            "plea": "guilty",
            "finding": "violation_found",
            "disposition_date": "2027-03-24",
            "agreement_sequence": "post_disposition",
        },
        "financial_entry": {
            "violation_code": "ORS_811_109_21_30",
            "fine_tier": "speed_21_to_30_over",
            "fee_schedule_source": "F-OR27-21-2025",
            "standard_fine": 265.0,
            "county_surcharge": 10.0,
            "amount_due": 275.0,
            "unsupported_charge_total_included": 0.0,
        },
        "payment_plan": {
            "plan_status": "approved",
            "agreement_type": "extended_payment_plan",
            "monthly_payment": 55.0,
            "down_payment": 0.0,
            "first_due_date": "2027-04-23",
            "full_payment_count": 5,
            "final_payment_amount": 0.0,
            "total_installments": 5,
            "final_due_date": "2027-08-23",
        },
        "form_entry": {
            "form_id": "OR_27JD_PLAN",
            "form_label": "payment_plan_agreement",
            "account_reference": "OR27-TR-2208",
            "required_labels_used": EXPECTED_LABELS,
        },
    },
    "OR27-TR-2219": {
        "jurisdiction_code": "OR27-CLAT",
        "defendant_name": "Leah Crane",
        "disposition": {
            "plea": "not_guilty",
            "finding": "dismissed",
            "disposition_date": "2027-03-24",
            "agreement_sequence": "no_agreement",
        },
        "financial_entry": {
            "violation_code": "ORS_811_109_100PLUS",
            "fine_tier": "dismissed_no_fine",
            "fee_schedule_source": "not_applicable_dismissed",
            "standard_fine": 0.0,
            "county_surcharge": 0.0,
            "amount_due": 0.0,
            "unsupported_charge_total_included": 0.0,
        },
        "payment_plan": {
            "plan_status": "not_applicable",
            "agreement_type": "none",
            "monthly_payment": None,
            "down_payment": 0.0,
            "first_due_date": None,
            "full_payment_count": 0,
            "final_payment_amount": None,
            "total_installments": 0,
            "final_due_date": None,
        },
        "form_entry": {
            "form_id": "not_applicable",
            "form_label": "not_applicable",
            "account_reference": "OR27-TR-2219",
            "required_labels_used": set(),
        },
    },
}


def money_equal(actual, expected):
    try:
        return math.isclose(round(float(actual), 2), round(float(expected), 2), abs_tol=0.005)
    except (TypeError, ValueError):
        return False


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
    sp001_detail = "target citation set, identities, and dispositions matched"
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
            "Correctly identifies the three target matters and records their dispositions.",
            sp001_ok,
            sp001_detail,
        )
    )

    for pid, citation, goal in [
        ("SP002", "OR27-TR-2201", "Correct current standard fine tier for OR27-TR-2201."),
        ("SP003", "OR27-TR-2208", "Correct current standard fine tier for OR27-TR-2208."),
    ]:
        expected_fields = {
            k: EXPECTED[citation]["financial_entry"][k]
            for k in ["violation_code", "fine_tier", "fee_schedule_source", "standard_fine"]
        }
        ok, detail = check_fields(matters.get(citation, {}), "financial_entry", expected_fields)
        pts.append(point(pid, goal, ok, f"{citation}: {detail}"))

    citation = "OR27-TR-2219"
    dismissed_fields = {}
    dismissed_fields.update(EXPECTED[citation]["financial_entry"])
    ok_fin, detail_fin = check_fields(matters.get(citation, {}), "financial_entry", dismissed_fields)
    ok_plan, detail_plan = check_fields(matters.get(citation, {}), "payment_plan", EXPECTED[citation]["payment_plan"])
    sp004_ok = ok_fin and ok_plan
    sp004_detail = "dismissed matter has no financial balance and no payment plan"
    if not sp004_ok:
        sp004_detail = f"{citation}: {detail_fin if not ok_fin else detail_plan}"
    pts.append(
        point(
            "SP004",
            "Keeps the dismissed high-speed matter out of fines, surcharge, and payment planning.",
            sp004_ok,
            sp004_detail,
        )
    )

    sp005_ok = True
    sp005_detail = "surcharges, per-citation balances, and batch financial totals matched"
    for citation in ["OR27-TR-2201", "OR27-TR-2208"]:
        expected_fields = {
            "county_surcharge": EXPECTED[citation]["financial_entry"]["county_surcharge"],
            "amount_due": EXPECTED[citation]["financial_entry"]["amount_due"],
        }
        ok, detail = check_fields(matters.get(citation, {}), "financial_entry", expected_fields)
        if not ok:
            sp005_ok = False
            sp005_detail = f"{citation}: {detail}"
            break
    batch = data.get("batch_totals", {}) if isinstance(data, dict) else {}
    if sp005_ok:
        expected_batch = {
            "matter_count": 3,
            "payable_matter_count": 2,
            "dismissed_matter_count": 1,
            "combined_standard_fine": 1465.0,
            "combined_county_surcharge": 20.0,
            "combined_amount_due": 1485.0,
        }
        for key, expected in expected_batch.items():
            actual = batch.get(key)
            if isinstance(expected, float):
                ok = money_equal(actual, expected)
            else:
                ok = actual == expected
            if not ok:
                sp005_ok = False
                sp005_detail = f"batch_totals.{key}: expected {expected!r}, got {actual!r}"
                break
    pts.append(
        point(
            "SP005",
            "Applies Clatsop surcharge once per payable citation and calculates batch financial totals.",
            sp005_ok,
            sp005_detail,
        )
    )

    sp006_ok = True
    sp006_detail = "payment status, type, monthly amount, first due date, and down payment matched"
    for citation in ["OR27-TR-2201", "OR27-TR-2208"]:
        expected_fields = {
            k: EXPECTED[citation]["payment_plan"][k]
            for k in ["plan_status", "agreement_type", "monthly_payment", "down_payment", "first_due_date"]
        }
        ok, detail = check_fields(matters.get(citation, {}), "payment_plan", expected_fields)
        if not ok:
            sp006_ok = False
            sp006_detail = f"{citation}: {detail}"
            break
    pts.append(
        point(
            "SP006",
            "Records approved post-disposition extended payment-plan terms for both payable citations.",
            sp006_ok,
            sp006_detail,
        )
    )

    sp007_ok = True
    sp007_detail = "installment counts, final remainders, final due dates, and scheduled total matched"
    for citation in ["OR27-TR-2201", "OR27-TR-2208"]:
        expected_fields = {
            k: EXPECTED[citation]["payment_plan"][k]
            for k in ["full_payment_count", "final_payment_amount", "total_installments", "final_due_date"]
        }
        ok, detail = check_fields(matters.get(citation, {}), "payment_plan", expected_fields)
        if not ok:
            sp007_ok = False
            sp007_detail = f"{citation}: {detail}"
            break
    if sp007_ok and batch.get("total_installments_scheduled") != 16:
        sp007_ok = False
        sp007_detail = (
            f"batch_totals.total_installments_scheduled expected 16, got {batch.get('total_installments_scheduled')!r}"
        )
    pts.append(
        point(
            "SP007",
            "Computes installment counts, final remainder amounts, final due dates, and total scheduled installments.",
            sp007_ok,
            sp007_detail,
        )
    )

    sp008_ok = True
    sp008_detail = "form id, label, account references, and required labels matched"
    for citation in ["OR27-TR-2201", "OR27-TR-2208"]:
        form = matters.get(citation, {}).get("form_entry", {})
        labels = (
            set(form.get("required_labels_used", [])) if isinstance(form.get("required_labels_used"), list) else set()
        )
        if (
            form.get("form_id") != "OR_27JD_PLAN"
            or form.get("form_label") != "payment_plan_agreement"
            or form.get("account_reference") != citation
            or labels != EXPECTED_LABELS
        ):
            sp008_ok = False
            sp008_detail = f"{citation}: got form_entry {form!r}"
            break
    if sp008_ok:
        form = matters.get("OR27-TR-2219", {}).get("form_entry", {})
        labels = form.get("required_labels_used", [])
        if (
            form.get("form_id") != "not_applicable"
            or form.get("form_label") != "not_applicable"
            or form.get("account_reference") != "OR27-TR-2219"
            or labels not in ([], None)
        ):
            sp008_ok = False
            sp008_detail = f"OR27-TR-2219: expected no payment form, got {form!r}"
    pts.append(
        point(
            "SP008",
            "Uses the 27th Judicial District form metadata and citation numbers as account references.",
            sp008_ok,
            sp008_detail,
        )
    )

    exclusions = data.get("excluded_charges", []) if isinstance(data, dict) else []
    by_code = {item.get("charge_code"): item for item in exclusions if isinstance(item, dict)}
    sp009_ok = set(EXPECTED_EXCLUSIONS).issubset(by_code)
    sp009_detail = "all required excluded unsupported charges were listed with correct reasons"
    if sp009_ok:
        for code, expected in EXPECTED_EXCLUSIONS.items():
            item = by_code[code]
            for key, expected_value in expected.items():
                if item.get(key) != expected_value:
                    sp009_ok = False
                    sp009_detail = f"{code}.{key}: expected {expected_value!r}, got {item.get(key)!r}"
                    break
            if not sp009_ok:
                break
    else:
        sp009_detail = f"missing excluded charge codes {sorted(set(EXPECTED_EXCLUSIONS) - set(by_code))}"
    if sp009_ok:
        for citation in EXPECTED:
            actual = nested_get(matters.get(citation, {}), "financial_entry", "unsupported_charge_total_included")
            if not money_equal(actual, 0.0):
                sp009_ok = False
                sp009_detail = f"{citation}: unsupported_charge_total_included expected 0.0, got {actual!r}"
                break
    if sp009_ok and not money_equal(batch.get("unsupported_charge_total_included"), 0.0):
        sp009_ok = False
        sp009_detail = (
            "batch_totals.unsupported_charge_total_included expected 0.0, "
            f"got {batch.get('unsupported_charge_total_included')!r}"
        )
    pts.append(
        point(
            "SP009",
            "Excludes unsupported, stale, enhancement, and no-trigger charges from the starting balances.",
            sp009_ok,
            sp009_detail,
        )
    )

    score = round(sum(WEIGHTS[p["id"]] for p in pts if p["passed"]) / TOTAL_WEIGHT, 6)
    return {"score": score, "points": pts}


def main():
    candidate = (
        sys.argv[1] if len(sys.argv) > 1 else str(Path(__file__).resolve().parents[1] / "output" / "answer.json")
    )
    data, err = load_candidate(candidate)
    if err:
        pts = [
            point(pid, goal, False, f"Could not parse candidate JSON: {err}")
            for pid, goal in [
                ("SP001", "Correctly identifies the three target matters and records their dispositions."),
                ("SP002", "Correct current standard fine tier for OR27-TR-2201."),
                ("SP003", "Correct current standard fine tier for OR27-TR-2208."),
                ("SP004", "Keeps the dismissed high-speed matter out of fines, surcharge, and payment planning."),
                (
                    "SP005",
                    "Applies Clatsop surcharge once per payable citation and calculates batch financial totals.",
                ),
                ("SP006", "Records approved post-disposition extended payment-plan terms for both payable citations."),
                (
                    "SP007",
                    "Computes installment counts, final remainder amounts, final due dates, and total scheduled installments.",
                ),
                ("SP008", "Uses the 27th Judicial District form metadata and citation numbers as account references."),
                (
                    "SP009",
                    "Excludes unsupported, stale, enhancement, and no-trigger charges from the starting balances.",
                ),
            ]
        ]
        print(json.dumps({"score": 0.0, "points": pts}, indent=2))
        return
    print(json.dumps(evaluate(data), indent=2))


if __name__ == "__main__":
    main()
