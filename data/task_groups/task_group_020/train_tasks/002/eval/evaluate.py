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
            "cash_amount": 30360000,
            "stock_amount": 8280000,
            "total_consideration": 38640000,
        },
        {
            "holder": "Founders and executives",
            "security_class": "common stock",
            "fully_diluted_pct": 0.185,
            "as_converted_shares": 8400000,
            "cash_amount": 61050000,
            "stock_amount": 16650000,
            "total_consideration": 77700000,
        },
        {
            "holder": "Lead investor group",
            "security_class": "preferred stock",
            "fully_diluted_pct": 0.341,
            "as_converted_shares": 15500000,
            "cash_amount": 112530000,
            "stock_amount": 30690000,
            "total_consideration": 143220000,
        },
        {
            "holder": "Public or minority holders",
            "security_class": "common stock",
            "fully_diluted_pct": 0.382,
            "as_converted_shares": 17300000,
            "cash_amount": 126060000,
            "stock_amount": 34380000,
            "total_consideration": 160440000,
        },
    ],
    "required_consents": ["CNS_PRJ_MERIDIAN_01", "CNS_PRJ_MERIDIAN_03"],
    "material_contract_conditions": ["MAT_PRJ_MERIDIAN_01", "MAT_PRJ_MERIDIAN_03"],
    "non_blocking_notices": ["CNS_PRJ_MERIDIAN_02", "MAT_PRJ_MERIDIAN_02"],
    "service_credit_employee_ids": ["EMP_PRJ_MERIDIAN_01", "EMP_PRJ_MERIDIAN_02", "EMP_PRJ_MERIDIAN_03"],
    "warn_risk_employee_ids": ["EMP_PRJ_MERIDIAN_02", "EMP_PRJ_MERIDIAN_03"],
    "blocker_ids": [
        "CNS_PRJ_MERIDIAN_01",
        "CNS_PRJ_MERIDIAN_03",
        "EMP_SERVICE_CREDIT",
        "INDEMNITY_PACKAGE",
        "MAT_PRJ_MERIDIAN_03",
        "NWC_COLLAR",
        "REG_HSR",
    ],
}

POINTS = [
    ("holder_allocation", 3, "Correct holder-level cash, stock, total consideration, shares, and percentages."),
    (
        "escrow_indemnity",
        2,
        "Correct buyer indemnity fallback, escrow amount, survival, release, and materiality scrape.",
    ),
    ("nwc_mechanics", 2, "Correct NWC collar and dollar-for-dollar adjustment posture."),
    (
        "consents_contracts",
        3,
        "Correct required consents, material-contract closing conditions, and non-blocking notices.",
    ),
    ("regulatory_hsr", 2, "Correct HSR status and regulatory closing condition."),
    (
        "employment_restrictive",
        2,
        "Correct employee service-credit, PTO, WARN-risk, and restrictive-covenant treatment.",
    ),
    ("do_tail_expenses", 1, "Correct D&O tail and transaction-expense allocation."),
    ("closing_readiness", 3, "Correct final readiness, blocker classification, and business-risk totals."),
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
    details = {"expected_count": len(expected), "actual_count": len(actual)}
    if len(actual) != len(expected):
        return False, details
    for a, e in zip(actual, expected):
        if norm_str(a.get("holder")) != e["holder"]:
            return False, {"mismatch": "holder", "actual": a.get("holder"), "expected": e["holder"]}
        for field in ["security_class"]:
            if norm_str(a.get(field)) != e[field]:
                return False, {"holder": e["holder"], "field": field, "actual": a.get(field), "expected": e[field]}
        for field in ["as_converted_shares", "cash_amount", "stock_amount", "total_consideration"]:
            if not check_int(a.get(field), e[field]):
                return False, {"holder": e["holder"], "field": field, "actual": a.get(field), "expected": e[field]}
        if not check_num(a.get("fully_diluted_pct"), e["fully_diluted_pct"], 0.00001):
            return False, {
                "holder": e["holder"],
                "field": "fully_diluted_pct",
                "actual": a.get("fully_diluted_pct"),
                "expected": e["fully_diluted_pct"],
            }
    totals_ok = (
        check_int(get(data, ["economics", "headline_value"]), 420000000)
        and check_int(get(data, ["economics", "upfront_cash"]), 330000000)
        and check_int(get(data, ["economics", "stock_value"]), 90000000)
        and check_int(get(data, ["economics", "milestone_value"]), 0)
    )
    return totals_ok, {"holder_rows": len(actual), "deal_economics_ok": totals_ok}


def check_escrow_indemnity(data):
    pkg = get(data, ["economics", "indemnity_package"], {})
    escrow = get(data, ["economics", "escrow"], {})
    checks = {
        "draft_cap_pct": check_num(pkg.get("draft_cap_pct"), 6.0, 0.0001),
        "preferred_cap_pct": check_num(pkg.get("buyer_preferred_cap_pct"), 12.0, 0.0001),
        "preferred_cap_amount": check_int(pkg.get("buyer_preferred_cap_amount"), 50400000),
        "fallback_cap_pct": check_num(pkg.get("buyer_fallback_cap_pct"), 10.0, 0.0001),
        "fallback_cap_amount": check_int(pkg.get("buyer_fallback_cap_amount"), 42000000),
        "draft_survival": check_int(pkg.get("draft_survival_months"), 12),
        "preferred_survival": check_int(pkg.get("buyer_preferred_survival_months"), 18),
        "fallback_survival": check_int(pkg.get("fallback_survival_with_escrow_months"), 15),
        "scrape": norm_enum(pkg.get("materiality_scrape_required")) == "FULL_BREACH_AND_DAMAGES",
        "risk": norm_enum(pkg.get("risk_rating")) == "HIGH",
        "escrow_basis": norm_str(escrow.get("basis")) == "purchase_price",
        "escrow_pct": check_num(escrow.get("required_pct"), 10.0, 0.0001),
        "escrow_amount": check_int(escrow.get("amount"), 42000000),
        "escrow_release": check_int(escrow.get("release_months"), 15),
        "escrow_status": norm_str(escrow.get("status")) == "required_buyer_fallback",
    }
    return all(checks.values()), checks


def check_nwc(data):
    nwc = get(data, ["economics", "nwc_adjustment"], {})
    checks = {
        "required": as_bool(nwc.get("required")) is True,
        "mechanic": norm_str(nwc.get("mechanic")) == "dollar_for_dollar_outside_collar",
        "collar_amount": check_int(nwc.get("collar_amount"), 2520000),
        "source": norm_str(nwc.get("source_finding_id")) == "FND_PRJ_MERIDIAN_03",
        "status": norm_str(nwc.get("status")) == "add_closing_mechanic",
    }
    return all(checks.values()), checks


def check_consents_contracts(data):
    consents = get(data, ["closing_conditions", "required_consents"], [])
    contracts = get(data, ["closing_conditions", "material_contract_conditions"], [])
    consent_ids = sorted(norm_str(r.get("source_id")) for r in consents if isinstance(r, dict))
    contract_ids = sorted(norm_str(r.get("contract_id")) for r in contracts if isinstance(r, dict))
    notices = sorted_strings(get(data, ["closing_conditions", "non_blocking_notices"], []))
    consent_amounts = {
        norm_str(r.get("source_id")): as_int(r.get("amount_at_risk")) for r in consents if isinstance(r, dict)
    }
    contract_revenue = {
        norm_str(r.get("contract_id")): as_int(r.get("annual_revenue")) for r in contracts if isinstance(r, dict)
    }
    details = {
        "consent_ids": consent_ids,
        "contract_ids": contract_ids,
        "notices": notices,
        "amounts_ok": consent_amounts == {"CNS_PRJ_MERIDIAN_01": 23100000, "CNS_PRJ_MERIDIAN_03": 850000},
        "revenue_ok": contract_revenue == {"MAT_PRJ_MERIDIAN_01": 35700000, "MAT_PRJ_MERIDIAN_03": 10920000},
    }
    passed = (
        consent_ids == EXPECTED["required_consents"]
        and contract_ids == EXPECTED["material_contract_conditions"]
        and notices == EXPECTED["non_blocking_notices"]
        and details["amounts_ok"]
        and details["revenue_ok"]
    )
    return passed, details


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


def check_employment_restrictive(data):
    emp = get(data, ["covenants", "employment"], {})
    rc = get(data, ["covenants", "restrictive_covenants"], {})
    checks = {
        "count": check_int(emp.get("continuing_employee_count"), 87),
        "service_credit": sorted_strings(emp.get("service_credit_employee_ids"))
        == EXPECTED["service_credit_employee_ids"],
        "pto": check_int(emp.get("pto_liability_total"), 3520000),
        "warn": sorted_strings(emp.get("warn_risk_employee_ids")) == EXPECTED["warn_risk_employee_ids"],
        "emp_action": norm_str(emp.get("required_action")) == "revise_service_credit_and_pto",
        "rc_required": as_bool(rc.get("required")) is True,
        "rc_groups": sorted_strings(rc.get("covered_holder_groups")) == ["Founders and executives"],
        "rc_action": norm_str(rc.get("required_action")) == "add_founder_executive_non_compete_and_non_solicit",
    }
    return all(checks.values()), checks


def check_do_tail_expenses(data):
    tail = get(data, ["covenants", "do_tail_and_expenses"], {})
    checks = {
        "tail_required": as_bool(tail.get("do_tail_required")) is True,
        "period": check_int(tail.get("tail_period_years"), 6),
        "tail_cost": norm_str(tail.get("tail_cost_allocation")) == "seller_expense_or_purchase_price_reduction",
        "seller_expenses": norm_str(tail.get("seller_transaction_expenses"))
        == "seller_responsibility_or_purchase_price_reduction",
        "buyer_expenses": norm_str(tail.get("buyer_transaction_expenses")) == "buyer_responsibility",
        "amount_status": norm_str(tail.get("amount_status")) == "amount_not_in_workbench",
    }
    return all(checks.values()), checks


def check_closing_readiness(data):
    ready = get(data, ["closing_readiness"], {})
    checks = {
        "status": norm_enum(ready.get("overall_status")) == "NOT_READY",
        "risk": norm_enum(ready.get("risk_rating")) == "HIGH",
        "blockers": sorted_strings(ready.get("blocker_ids")) == EXPECTED["blocker_ids"],
        "tradeable": sorted_strings(ready.get("tradeable_issue_ids"))
        == ["CNS_PRJ_MERIDIAN_02", "DO_TAIL_AMOUNT", "MAT_PRJ_MERIDIAN_02"],
        "consent_amount": check_int(ready.get("closing_consent_amount_at_risk"), 23950000),
        "contract_revenue": check_int(ready.get("material_contract_revenue_conditioned"), 46620000),
        "pto_total": check_int(ready.get("employee_pto_liability_total"), 3520000),
    }
    return all(checks.values()), checks


CHECKS = {
    "holder_allocation": check_holder_allocation,
    "escrow_indemnity": check_escrow_indemnity,
    "nwc_mechanics": check_nwc,
    "consents_contracts": check_consents_contracts,
    "regulatory_hsr": check_regulatory,
    "employment_restrictive": check_employment_restrictive,
    "do_tail_expenses": check_do_tail_expenses,
    "closing_readiness": check_closing_readiness,
}


def evaluate(data):
    total_weight = sum(weight for _, weight, _ in POINTS)
    results = []
    score = 0.0
    for point_id, weight, goal in POINTS:
        try:
            passed, details = CHECKS[point_id](data)
        except Exception as exc:  # deterministic failure with diagnostics
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
    score = round(min(1.0, max(0.0, score)), 12)
    return {
        "score": score,
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
