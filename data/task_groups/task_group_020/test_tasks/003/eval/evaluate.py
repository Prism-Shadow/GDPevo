#!/usr/bin/env python3
import json
import math
import sys
from pathlib import Path


EXPECTED = {
    "holder_allocation": [
        {
            "holder": "Employee option pool",
            "security_class": "options",
            "fully_diluted_pct": 0.092,
            "as_converted_shares": 4200000,
            "cash_amount": 37720000,
            "stock_amount": 9200000,
            "total_consideration": 46920000,
        },
        {
            "holder": "Founders and executives",
            "security_class": "common stock",
            "fully_diluted_pct": 0.185,
            "as_converted_shares": 8400000,
            "cash_amount": 75850000,
            "stock_amount": 18500000,
            "total_consideration": 94350000,
        },
        {
            "holder": "Lead investor group",
            "security_class": "preferred stock",
            "fully_diluted_pct": 0.341,
            "as_converted_shares": 15500000,
            "cash_amount": 139810000,
            "stock_amount": 34100000,
            "total_consideration": 173910000,
        },
        {
            "holder": "Public or minority holders",
            "security_class": "common stock",
            "fully_diluted_pct": 0.382,
            "as_converted_shares": 17300000,
            "cash_amount": 156620000,
            "stock_amount": 38200000,
            "total_consideration": 194820000,
        },
    ],
    "required_consents": ["CNS_PRJ_HELIX_01", "CNS_PRJ_HELIX_03"],
    "material_contract_conditions": ["MAT_PRJ_HELIX_01", "MAT_PRJ_HELIX_03"],
    "non_blocking_notices": ["CNS_PRJ_HELIX_02", "MAT_PRJ_HELIX_02"],
    "service_credit_employee_ids": ["EMP_PRJ_HELIX_01", "EMP_PRJ_HELIX_02", "EMP_PRJ_HELIX_03"],
    "warn_risk_employee_ids": ["EMP_PRJ_HELIX_02", "EMP_PRJ_HELIX_03"],
    "blocker_ids": [
        "CNS_PRJ_HELIX_01",
        "CNS_PRJ_HELIX_03",
        "EMP_SERVICE_CREDIT",
        "ESCROW_RELEASE",
        "INDEMNITY_PACKAGE",
        "MAT_PRJ_HELIX_01",
        "MAT_PRJ_HELIX_03",
        "NWC_COLLAR",
        "REG_PRJ_HELIX_HSR",
    ],
}

POINTS = [
    ("holder_allocation", 3, "Correct holder-level cash, stock, total consideration, shares, and percentages."),
    (
        "indemnity_special",
        2,
        "Correct indemnity cap, special indemnity shortfall, survival, and materiality scrape posture.",
    ),
    ("escrow_nwc", 2, "Correct general escrow and NWC collar mechanics."),
    ("consents", 2, "Correct required closing consents and non-blocking consent notice."),
    ("regulatory_hsr", 2, "Correct HSR status and regulatory closing condition."),
    ("employment_restrictive_do", 3, "Correct employment, restrictive covenant, D&O tail, and expense treatment."),
    ("contracts_debt", 2, "Correct material-contract closing conditions and debt-payoff workbench status."),
    ("closing_readiness", 3, "Correct final readiness, blocker classification, and summary totals."),
]


def load_answer(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get(data, path, default=None):
    cur = data
    for part in path:
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def norm_str(value):
    return str(value).strip()


def norm_enum(value):
    return norm_str(value).upper()


def as_int(value):
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip().replace(",", "")
        if stripped.lstrip("-").isdigit():
            return int(stripped)
    return None


def as_float(value):
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"yes", "true", "required"}:
            return True
        if lowered in {"no", "false", "not_required"}:
            return False
    return None


def sorted_strings(values):
    if not isinstance(values, list):
        return []
    return sorted(norm_str(v) for v in values)


def check_num(value, expected, tol=0.0):
    actual = as_float(value)
    return actual is not None and math.isclose(actual, expected, abs_tol=tol)


def check_int(value, expected):
    return as_int(value) == expected


def holder_key(row):
    return norm_str(row.get("holder")) if isinstance(row, dict) else ""


def check_holder_allocation(data):
    rows = get(data, ["economics", "holder_allocation"], [])
    if not isinstance(rows, list):
        return False, {"reason": "holder_allocation is not a list"}
    actual = sorted((r for r in rows if isinstance(r, dict)), key=holder_key)
    expected = sorted(EXPECTED["holder_allocation"], key=holder_key)
    if len(actual) != len(expected):
        return False, {"expected_count": len(expected), "actual_count": len(actual)}
    for actual_row, expected_row in zip(actual, expected):
        if norm_str(actual_row.get("holder")) != expected_row["holder"]:
            return False, {"field": "holder", "actual": actual_row.get("holder"), "expected": expected_row["holder"]}
        if norm_str(actual_row.get("security_class")) != expected_row["security_class"]:
            return False, {"holder": expected_row["holder"], "field": "security_class"}
        for field in ["as_converted_shares", "cash_amount", "stock_amount", "total_consideration"]:
            if not check_int(actual_row.get(field), expected_row[field]):
                return False, {
                    "holder": expected_row["holder"],
                    "field": field,
                    "actual": actual_row.get(field),
                    "expected": expected_row[field],
                }
        if not check_num(actual_row.get("fully_diluted_pct"), expected_row["fully_diluted_pct"], 0.00001):
            return False, {"holder": expected_row["holder"], "field": "fully_diluted_pct"}
    totals_ok = (
        check_int(get(data, ["economics", "headline_value"]), 510000000)
        and check_int(get(data, ["economics", "upfront_cash"]), 410000000)
        and check_int(get(data, ["economics", "stock_value"]), 100000000)
        and check_int(get(data, ["economics", "milestone_value"]), 0)
    )
    return totals_ok, {"holder_rows": len(actual), "deal_economics_ok": totals_ok}


def check_indemnity_special(data):
    pkg = get(data, ["economics", "indemnity_package"], {})
    checks = {
        "source": norm_str(pkg.get("source_term_id")) == "TERM_PRJ_HELIX_02",
        "draft_cap_pct": check_num(pkg.get("draft_cap_pct"), 9.0, 0.0001),
        "draft_cap_amount": check_int(pkg.get("draft_cap_amount"), 45900000),
        "special_indemnity": check_int(pkg.get("draft_special_indemnity_amount"), 15000000),
        "identified_findings": check_int(pkg.get("identified_findings_amount"), 23970000),
        "special_shortfall": check_int(pkg.get("special_indemnity_shortfall"), 8970000),
        "preferred_cap_pct": check_num(pkg.get("buyer_preferred_cap_pct"), 12.0, 0.0001),
        "preferred_cap_amount": check_int(pkg.get("buyer_preferred_cap_amount"), 61200000),
        "fallback_cap_pct": check_num(pkg.get("buyer_fallback_cap_pct"), 10.0, 0.0001),
        "fallback_cap_amount": check_int(pkg.get("buyer_fallback_cap_amount"), 51000000),
        "fallback_shortfall": check_int(pkg.get("cap_shortfall_to_fallback"), 5100000),
        "preferred_shortfall": check_int(pkg.get("cap_shortfall_to_preferred"), 15300000),
        "preferred_survival": check_int(pkg.get("buyer_preferred_survival_months"), 18),
        "fallback_survival": check_int(pkg.get("fallback_survival_with_escrow_months"), 15),
        "survival_status": norm_str(pkg.get("survival_status")) == "missing_required_term",
        "scrape_required": norm_enum(pkg.get("materiality_scrape_required")) == "FULL_BREACH_AND_DAMAGES",
        "scrape_status": norm_str(pkg.get("materiality_scrape_status")) == "missing_required_term",
        "risk": norm_enum(pkg.get("risk_rating")) == "HIGH",
    }
    return all(checks.values()), checks


def check_escrow_nwc(data):
    escrow = get(data, ["economics", "escrow"], {})
    nwc = get(data, ["economics", "nwc_adjustment"], {})
    checks = {
        "escrow_basis": norm_str(escrow.get("basis")) == "purchase_price",
        "escrow_pct": check_num(escrow.get("required_pct"), 10.0, 0.0001),
        "escrow_amount": check_int(escrow.get("amount"), 51000000),
        "escrow_release": check_int(escrow.get("release_months"), 15),
        "escrow_trigger": norm_str(escrow.get("release_trigger")) == "general_rep_survival_expiration",
        "escrow_status": norm_str(escrow.get("status")) == "required_buyer_fallback",
        "nwc_required": as_bool(nwc.get("required")) is True,
        "nwc_mechanic": norm_str(nwc.get("mechanic")) == "dollar_for_dollar_outside_collar",
        "nwc_amount": check_int(nwc.get("collar_amount"), 3060000),
        "nwc_source": norm_str(nwc.get("source_finding_id")) == "FND_PRJ_HELIX_03",
        "nwc_status": norm_str(nwc.get("status")) == "add_closing_mechanic",
    }
    return all(checks.values()), checks


def check_consents(data):
    consents = get(data, ["closing_conditions", "required_consents"], [])
    consent_ids = sorted(norm_str(row.get("source_id")) for row in consents if isinstance(row, dict))
    amounts = {
        norm_str(row.get("source_id")): as_int(row.get("amount_at_risk")) for row in consents if isinstance(row, dict)
    }
    risks = {
        norm_str(row.get("source_id")): norm_enum(row.get("risk_rating")) for row in consents if isinstance(row, dict)
    }
    notices = sorted_strings(get(data, ["closing_conditions", "non_blocking_notices"], []))
    checks = {
        "ids": consent_ids == EXPECTED["required_consents"],
        "amounts": amounts == {"CNS_PRJ_HELIX_01": 28050000, "CNS_PRJ_HELIX_03": 850000},
        "risks": risks == {"CNS_PRJ_HELIX_01": "HIGH", "CNS_PRJ_HELIX_03": "LOW"},
        "notices": notices == EXPECTED["non_blocking_notices"],
    }
    return all(checks.values()), checks


def check_regulatory(data):
    reg = get(data, ["regulatory"], {})
    checks = {
        "hsr_required": norm_str(reg.get("hsr_required")).lower() == "yes",
        "threshold_basis": norm_str(reg.get("threshold_basis")) == "size-of-transaction",
        "approval": norm_str(reg.get("regulatory_approval")) == "HSR only",
        "hhw": norm_str(reg.get("hell_or_high_water_required")).lower() == "no",
        "condition": as_bool(reg.get("closing_condition_required")) is True,
    }
    return all(checks.values()), checks


def check_employment_restrictive_do(data):
    emp = get(data, ["covenants", "employment"], {})
    rc = get(data, ["covenants", "restrictive_covenants"], {})
    tail = get(data, ["covenants", "do_tail_and_expenses"], {})
    checks = {
        "employee_count": check_int(emp.get("continuing_employee_count"), 87),
        "service_credit": sorted_strings(emp.get("service_credit_employee_ids"))
        == EXPECTED["service_credit_employee_ids"],
        "pto": check_int(emp.get("pto_liability_total"), 3520000),
        "warn": sorted_strings(emp.get("warn_risk_employee_ids")) == EXPECTED["warn_risk_employee_ids"],
        "employee_action": norm_str(emp.get("required_action")) == "revise_service_credit_and_pto",
        "rc_required": as_bool(rc.get("required")) is True,
        "rc_groups": sorted_strings(rc.get("covered_holder_groups")) == ["Founders and executives"],
        "rc_action": norm_str(rc.get("required_action")) == "add_founder_executive_non_compete_and_non_solicit",
        "tail_required": as_bool(tail.get("do_tail_required")) is True,
        "tail_period": check_int(tail.get("tail_period_years"), 6),
        "tail_cost": norm_str(tail.get("tail_cost_allocation")) == "seller_expense_or_purchase_price_reduction",
        "seller_expenses": norm_str(tail.get("seller_transaction_expenses"))
        == "seller_responsibility_or_purchase_price_reduction",
        "buyer_expenses": norm_str(tail.get("buyer_transaction_expenses")) == "buyer_responsibility",
        "amount_status": norm_str(tail.get("amount_status")) == "amount_not_in_workbench",
    }
    return all(checks.values()), checks


def check_contracts_debt(data):
    contracts = get(data, ["closing_conditions", "material_contract_conditions"], [])
    contract_ids = sorted(norm_str(row.get("contract_id")) for row in contracts if isinstance(row, dict))
    revenues = {
        norm_str(row.get("contract_id")): as_int(row.get("annual_revenue"))
        for row in contracts
        if isinstance(row, dict)
    }
    debt = get(data, ["closing_conditions", "debt_payoff"], {})
    checks = {
        "contract_ids": contract_ids == EXPECTED["material_contract_conditions"],
        "revenues": revenues == {"MAT_PRJ_HELIX_01": 43350000, "MAT_PRJ_HELIX_03": 13260000},
        "debt_required": as_bool(debt.get("required")) is False,
        "debt_status": norm_str(debt.get("status")) == "no_debt_payoff_record",
        "debt_blocker": debt.get("blocker_id") is None,
        "debt_amount": debt.get("amount") is None,
        "debt_action": norm_str(debt.get("required_action")) == "none",
    }
    return all(checks.values()), checks


def check_closing_readiness(data):
    ready = get(data, ["closing_readiness"], {})
    checks = {
        "status": norm_enum(ready.get("overall_status")) == "NOT_READY",
        "risk": norm_enum(ready.get("risk_rating")) == "HIGH",
        "blockers": sorted_strings(ready.get("blocker_ids")) == EXPECTED["blocker_ids"],
        "tradeable": sorted_strings(ready.get("tradeable_issue_ids"))
        == ["CNS_PRJ_HELIX_02", "DO_TAIL_AMOUNT", "MAT_PRJ_HELIX_02"],
        "consent_amount": check_int(ready.get("closing_consent_amount_at_risk"), 28900000),
        "contract_revenue": check_int(ready.get("material_contract_revenue_conditioned"), 56610000),
        "pto_total": check_int(ready.get("employee_pto_liability_total"), 3520000),
        "risk_low": check_int(ready.get("total_modeled_exposure_low"), 13770000),
        "risk_high": check_int(ready.get("total_modeled_exposure_high"), 46410000),
        "highest": norm_str(ready.get("highest_modeled_exposure_category")) == "closing_certainty",
    }
    return all(checks.values()), checks


CHECKS = {
    "holder_allocation": check_holder_allocation,
    "indemnity_special": check_indemnity_special,
    "escrow_nwc": check_escrow_nwc,
    "consents": check_consents,
    "regulatory_hsr": check_regulatory,
    "employment_restrictive_do": check_employment_restrictive_do,
    "contracts_debt": check_contracts_debt,
    "closing_readiness": check_closing_readiness,
}


def evaluate(data):
    total_weight = sum(weight for _, weight, _ in POINTS)
    results = []
    score = 0.0
    for point_id, weight, goal in POINTS:
        try:
            passed, details = CHECKS[point_id](data)
        except Exception as exc:
            passed, details = False, {"error": type(exc).__name__}
        assigned = weight / total_weight
        earned = assigned if passed else 0.0
        score += earned
        results.append(
            {
                "id": point_id,
                "goal": goal,
                "weight": weight,
                "assigned_score": assigned,
                "passed": bool(passed),
                "earned_score": earned,
                "details": details,
            }
        )
    return {
        "score": round(min(1.0, max(0.0, score)), 12),
        "points": results,
        "max_score": 1.0,
        "raw_total_weight": total_weight,
    }


def main():
    answer_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("answer.json")
    try:
        data = load_answer(answer_path)
        result = evaluate(data)
    except Exception as exc:
        total_weight = sum(weight for _, weight, _ in POINTS)
        result = {
            "score": 0.0,
            "points": [],
            "max_score": 1.0,
            "raw_total_weight": total_weight,
            "error": f"Could not parse or evaluate answer: {type(exc).__name__}",
        }
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
