#!/usr/bin/env python3
"""
Reference solver for the private-wealth advisory benchmark.

This is a STARTING POINT, not a black box. It implements the verified formulas and the exact
RMD simulation order. Read it, adapt the enum decisions to the specific answer_template.json you
are given (field names and enum sets vary slightly per task), and always validate against the
worked numbers with:  python solver.py --selftest

Usage:
    python solver.py --selftest
    python solver.py --base http://127.0.0.1:8066 roth   CLT-1001 --horizon 2046
    python solver.py --base http://127.0.0.1:8066 ilit   CLT-1002
    python solver.py --base http://127.0.0.1:8066 trust  CLT-1003
    python solver.py --base http://127.0.0.1:8066 plan   CLT-1004

The script prints the computed numeric fields. You assemble the final JSON to match the exact
template keys/enum spellings for your task (do not assume key names — read the template).
"""
import argparse, json, urllib.request, datetime, os, sys

def api(base, path):
    with urllib.request.urlopen(base + path) as r:
        return json.load(r)

def round2(x):
    return round(float(x) + 0.0, 2)

# ---------- data access + source resolution ----------
def load_client_bundle(base, cid):
    docs = api(base, f"/api/source-documents?client_id={cid}")
    by_type = {d["source_type"]: d["facts"] for d in docs}
    signed = by_type.get("SIGNED_PROFILE", {})
    attorney = by_type.get("ATTORNEY_MEMO", {})
    header = api(base, f"/api/clients/{cid}")
    ira = api(base, f"/api/retirement-accounts?client_id={cid}")
    life = api(base, f"/api/life-insurance?client_id={cid}")
    trusts = api(base, f"/api/trust-candidates?client_id={cid}")
    pol = api(base, "/api/policies/tax")
    rmd = {int(k): v for k, v in api(base, "/api/rmd-factors").items()}
    return dict(cid=cid, header=header, signed=signed, attorney=attorney,
                ira=ira[0] if ira else None, life=life[0] if life else None,
                trust=trusts[0] if trusts else None, pol=pol, rmd=rmd)

def resolved(b):
    """Resolved facts per the source-of-truth rules."""
    s = b["signed"]; a = b["attorney"]
    estate_value = a.get("estate_value", s.get("estate_value", b["header"].get("estate_value")))
    return dict(
        estate_value=estate_value,                       # ATTORNEY_MEMO authoritative
        marital_status=s.get("marital_status", b["header"].get("marital_status")),
        filing_status=s.get("filing_status", b["header"].get("filing_status")),
        liquid_assets=s.get("liquid_assets", b["header"].get("liquid_assets")),
        planning_year=s.get("planning_year", b["header"].get("planning_year")),
        age=s.get("age", b["header"].get("age")),
        beneficiary_count=s.get("beneficiary_count"),
        philanthropic_intent=s.get("philanthropic_intent"),
        family_transfer_priority=s.get("family_transfer_priority"),
        marginal_tax_rate=s.get("marginal_tax_rate"),
        annual_non_ira_income=s.get("annual_non_ira_income"),
    )

# ---------- Roth + RMD ----------
def simulate_roth(b, horizon, with_conversion):
    r = resolved(b); ira = b["ira"]; rmd = b["rmd"]
    pol = b["pol"]
    target = pol["conversion_bracket_targets"][r["filing_status"]]
    annual_conv = target - r["annual_non_ira_income"]
    conv_years = ira["recommended_conversion_years"]
    mtr = r["marginal_tax_rate"]; ret = ira["expected_return"]
    py = r["planning_year"]; age0 = r["age"]; start = ira["rmd_start_age"]
    trad = ira["traditional_balance"]; roth = ira["roth_balance"]
    rmd_tax = 0.0
    for year in range(py, horizon + 1):
        age = age0 + (year - py)
        if with_conversion and year < py + conv_years:
            amt = min(annual_conv, trad)
            trad -= amt; roth += amt
        if age >= start and age in rmd:
            d = trad / rmd[age]
            trad -= d; rmd_tax += d * mtr
        trad *= (1 + ret); roth *= (1 + ret)
    return rmd_tax, trad, roth

def roth_fields(b, horizon):
    r = resolved(b); ira = b["ira"]; pol = b["pol"]
    target = pol["conversion_bracket_targets"][r["filing_status"]]
    annual_conv = target - r["annual_non_ira_income"]
    conv_years = ira["recommended_conversion_years"]
    base_tax, _, _ = simulate_roth(b, horizon, False)
    conv_tax, trad_h, roth_h = simulate_roth(b, horizon, True)
    share = roth_h / (roth_h + trad_h) if (roth_h + trad_h) else 0
    heir = ("MOSTLY_TAX_FREE" if share >= 0.7 else
            "MOSTLY_TAXABLE" if share <= 0.3 else "MIXED_TAXABLE_AND_TAX_FREE")
    return dict(
        first_conversion_year=r["planning_year"],
        conversion_years=conv_years, conversion_years_positive=conv_years,
        annual_conversion_amount=round2(annual_conv),
        total_converted=round2(annual_conv * conv_years),
        total_conversion_tax=round2(annual_conv * conv_years * r["marginal_tax_rate"]),
        horizon_year=horizon,
        first_rmd_year=r["planning_year"] + (ira["rmd_start_age"] - r["age"]),
        baseline_rmd_tax_through_horizon=round2(base_tax),
        conversion_rmd_tax_through_horizon=round2(conv_tax),
        rmd_tax_savings_through_horizon=round2(base_tax - conv_tax),
        projected_roth_balance_horizon=round2(roth_h),
        projected_traditional_balance_horizon=round2(trad_h),
        heir_tax_profile=heir,
    )

# ---------- estate context ----------
def estate_context(b):
    r = resolved(b); pol = b["pol"]; py = str(r["planning_year"])
    base_ex = pol["estate_tax_exemption"][py]
    ex = base_ex * (2 if r["marital_status"] == "married" else 1)
    taxable = max(0, r["estate_value"] - ex)
    exposure = taxable * pol["estate_tax_rate"]
    liq = r["liquid_assets"]
    gap = max(0, exposure - liq)
    return dict(planning_year=r["planning_year"], exemption_used=round2(ex),
                taxable_estate=round2(taxable), estate_tax_exposure=round2(exposure),
                liquid_assets_available=round2(liq), liquidity_gap_before_planning=round2(gap))

# ---------- GRAT / CRAT ----------
def trust_fields(b):
    t = b["trust"]; pol = b["pol"]; A = t["asset_value"]; g = t["expected_growth_rate"]
    grat = A * (1 + g) ** t["grat_term_years"] - A * t["grat_annuity_rate"] * t["grat_term_years"]
    crat = A * (1 + g) ** t["crat_term_years"] - A * t["crat_payout_rate"] * t["crat_term_years"]
    return dict(
        grat_term_years=t["grat_term_years"],
        grat_remainder=round2(grat),
        grat_est_tax_reduction=round2(grat * pol["estate_tax_rate"]),
        crat_term_years=t["crat_term_years"],
        crat_remainder=round2(crat),
        crat_income_deduction=round2(crat * pol["charitable_deduction_rate"]),
    )

RANK = {"low": 0, "moderate": 1, "high": 2}
def preferred_strategy(b):
    r = resolved(b)
    fam = RANK.get(r["family_transfer_priority"], 0)
    phil = RANK.get(r["philanthropic_intent"], 0)
    return "CRAT" if phil > fam else "GRAT"

# ---------- ILIT ----------
def ilit_fields(b):
    r = resolved(b); pol = b["pol"]; life = b["life"]; py = str(r["planning_year"])
    gift = pol["annual_gift_exclusion"][py]
    cap = gift * r["beneficiary_count"]
    premium = life["annual_premium"]
    gap = max(0, premium - cap)
    transfer = life.get("is_existing_policy_transfer", False)
    if transfer and gap > 0: risk = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
    elif transfer:           risk = "THREE_YEAR_LOOKBACK"
    elif gap > 0:            risk = "EXCLUSION_SHORTFALL"
    else:                    risk = "LOW_IF_FORMALITIES_MET"
    cdate = datetime.date.fromisoformat(life["planned_contribution_date"])
    notice = cdate + datetime.timedelta(days=7)
    window_end = notice + datetime.timedelta(days=30)
    earliest = window_end + datetime.timedelta(days=1)
    return dict(
        annual_exclusion_per_beneficiary=round2(gift),
        beneficiary_count=r["beneficiary_count"],
        annual_exclusion_capacity=round2(cap),
        annual_premium=round2(premium),
        premium_gap=round2(gap),
        notices_required=r["beneficiary_count"],
        contribution_date=cdate.isoformat(),
        notice_due_date=notice.isoformat(),
        withdrawal_window_end=window_end.isoformat(),
        earliest_premium_payment_date=earliest.isoformat(),
        dedicated_bank_account_required=True,
        death_benefit=round2(life["death_benefit"]),
        projected_outside_estate_if_implemented=round2(life["death_benefit"]),
        tax_liquidity_support=round2(life["death_benefit"] * pol["estate_tax_rate"]),
        estate_inclusion_risk=risk,
        risk_flag=risk,
    )

# ---------- selftest ----------
def selftest(base):
    ok = True
    def check(label, got, exp):
        nonlocal ok
        good = abs(got - exp) < 0.01 if isinstance(exp, float) else got == exp
        ok = ok and good
        print(f"  [{'OK' if good else 'XX'}] {label}: got {got} expected {exp}")
    b = load_client_bundle(base, "CLT-1001"); f = roth_fields(b, 2046)
    check("roth annual_conv", f["annual_conversion_amount"], 209600.0)
    check("roth baseline_tax", f["baseline_rmd_tax_through_horizon"], 1097182.33)
    check("roth conv_tax", f["conversion_rmd_tax_through_horizon"], 617448.59)
    check("roth roth_bal", f["projected_roth_balance_horizon"], 4594320.16)
    check("roth trad_bal", f["projected_traditional_balance_horizon"], 2895040.03)
    b = load_client_bundle(base, "CLT-1002"); il = ilit_fields(b)
    check("ilit capacity", il["annual_exclusion_capacity"], 80000.0)
    check("ilit liquidity_support", il["tax_liquidity_support"], 1800000.0)
    check("ilit notice_due", il["notice_due_date"], "2026-03-17")
    check("ilit earliest", il["earliest_premium_payment_date"], "2026-04-17")
    b = load_client_bundle(base, "CLT-1003"); tf = trust_fields(b); ec = estate_context(b)
    check("grat remainder", tf["grat_remainder"], 10154624.61)
    check("grat reduction", tf["grat_est_tax_reduction"], 4061849.85)
    check("crat remainder", tf["crat_remainder"], 28487657.15)
    check("crat deduction", tf["crat_income_deduction"], 9970680.0)
    check("estate exposure", ec["estate_tax_exposure"], 4632000.0)
    b = load_client_bundle(base, "CLT-1004"); ec = estate_context(b)
    check("single exemption", ec["exemption_used"], 13610000.0)
    check("single liquidity_gap", ec["liquidity_gap_before_planning"], 4636000.0)
    print("ALL PASS" if ok else "SOME FAILED")
    return ok

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("family", nargs="?", choices=["roth", "ilit", "trust", "plan"])
    ap.add_argument("client_id", nargs="?")
    ap.add_argument("--base", default=os.environ.get("API_BASE", "http://127.0.0.1:8066"))
    ap.add_argument("--horizon", type=int)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        sys.exit(0 if selftest(a.base) else 1)
    b = load_client_bundle(a.base, a.client_id)
    if a.family == "roth":
        print(json.dumps(roth_fields(b, a.horizon), indent=2))
    elif a.family == "ilit":
        print(json.dumps(ilit_fields(b), indent=2))
    elif a.family == "trust":
        out = dict(estate_context=estate_context(b), preferred=preferred_strategy(b), **trust_fields(b))
        print(json.dumps(out, indent=2))
    elif a.family == "plan":
        out = dict(estate_context=estate_context(b), ilit=ilit_fields(b),
                   preferred=preferred_strategy(b), **trust_fields(b))
        print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
