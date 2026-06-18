"""
advisory_lib.py — reusable computation helpers for the Private Wealth Advisory
benchmark (Roth/RMD, ILIT/Crummey, GRAT vs CRAT, integrated estate-liquidity).

These functions reproduce the exact gold numbers of the worked training tasks
(verified to the cent). Pull *all* constants (gift exclusion, estate exemption,
estate tax rate, bracket targets, charitable deduction rate, RMD divisors) from
the live API — never hard-code them — and pass them in here.

Usage pattern: fetch the API records, resolve the controlling sources (see
SKILL.md / reference.md), then call the helper that matches the task family.
Round every USD field to 2 decimals (cents) only in the FINAL JSON; keep full
precision through intermediate steps.

All HTTP is GET-only. Base URL is given by the harness (env API_BASE, else
http://127.0.0.1:8066).
"""
import json
import os
import subprocess
from datetime import date, timedelta

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8066").rstrip("/")


def api(path):
    """GET a JSON endpoint. `path` starts with '/api/...'."""
    raw = subprocess.check_output(["curl", "-s", BASE + path])
    return json.loads(raw)


# --------------------------------------------------------------------------
# Source resolution
# --------------------------------------------------------------------------
# Profile / goal / beneficiary / policy facts: SIGNED_PROFILE always controls.
# Tie-break by latest effective_date if several signed profiles ever appear.
# ATTORNEY_MEMO, CRM_NOTE, STALE_MARKETING_INTAKE never override a signed value.
# Account balances/returns/RMD age: CUSTODIAN_EXPORT (the retirement-accounts
# endpoint) controls. Trust mechanics: the trust-candidates endpoint controls.
PROFILE_PRIORITY = [
    "SIGNED_PROFILE", "ATTORNEY_MEMO", "CUSTODIAN_EXPORT",
    "CRM_NOTE", "STALE_MARKETING_INTAKE",
]


def resolve_profile(source_docs):
    """Return the controlling profile facts dict (highest-priority, latest)."""
    def rank(doc):
        st = doc["source_type"]
        pr = PROFILE_PRIORITY.index(st) if st in PROFILE_PRIORITY else 99
        # lower priority index wins; among equal, later effective_date wins
        return (pr, _neg_date(doc.get("effective_date", "0000-00-00")))
    best = sorted(source_docs, key=rank)[0]
    return best["facts"], best["source_type"]


def signed_profile(source_docs):
    """The latest SIGNED_PROFILE facts (the normal controlling profile)."""
    signed = [d for d in source_docs if d["source_type"] == "SIGNED_PROFILE"]
    signed.sort(key=lambda d: d["effective_date"])
    return signed[-1]["facts"]


def _neg_date(s):
    # helper so that a later date sorts first within the same priority bucket
    y, m, d = (int(x) for x in s.split("-"))
    return -(y * 10000 + m * 100 + d)


# --------------------------------------------------------------------------
# Estate context (used by trust_comparison and estate_liquidity_action_plan)
# --------------------------------------------------------------------------
def estate_exemption(marital_status, policies, year):
    base = policies["estate_tax_exemption"][str(year)]
    return base * 2 if marital_status == "married" else base


def estate_context(profile, policies, year):
    estate = float(profile["estate_value"])
    liquid = float(profile["liquid_assets"])
    exemption = estate_exemption(profile["marital_status"], policies, year)
    taxable = max(0.0, estate - exemption)
    exposure = taxable * policies["estate_tax_rate"]
    gap = max(0.0, exposure - liquid)
    return {
        "planning_year": year,
        "exemption_used": round(exemption, 2),
        "taxable_estate": round(taxable, 2),
        "estate_tax_exposure": round(exposure, 2),
        "liquid_assets_available": round(liquid, 2),
        "liquidity_gap_before_planning": round(gap, 2),
    }


# --------------------------------------------------------------------------
# Roth conversion + RMD
# --------------------------------------------------------------------------
def roth_conversion_rmd(profile, account, policies, rmd_factors, horizon_year):
    """Return the conversion_plan + rmd_projection + legacy_projection figures.

    Order of operations inside each projection year (CRITICAL — verified to the
    cent): (1) do the conversion if this is a conversion year, (2) take the RMD
    if age >= rmd_start_age, (3) grow both balances by expected_return.
    """
    income = float(profile["annual_non_ira_income"])
    mtr = float(profile["marginal_tax_rate"])
    bracket = float(policies["conversion_bracket_targets"][profile["filing_status"]])
    annual_conv = bracket - income            # may be <= 0 (see SKILL.md)

    trad0 = float(account["traditional_balance"])
    roth0 = float(account["roth_balance"])
    r = float(account["expected_return"])
    rmd_start_age = int(account["rmd_start_age"])
    conv_years = int(account["recommended_conversion_years"])

    age0 = int(profile["age"])
    py = int(profile["planning_year"])
    first_rmd_year = py + (rmd_start_age - age0)

    rmd = {int(k): float(v) for k, v in rmd_factors.items()}

    def simulate(do_conversion):
        trad, roth, rmd_tax = trad0, roth0, 0.0
        for year in range(py, horizon_year + 1):
            age = age0 + (year - py)
            if do_conversion and annual_conv > 0 and year < py + conv_years:
                trad -= annual_conv
                roth += annual_conv
            if age >= rmd_start_age:
                distribution = trad / rmd[age]
                trad -= distribution
                rmd_tax += distribution * mtr
            trad *= (1 + r)
            roth *= (1 + r)
        return trad, roth, rmd_tax

    base_trad, base_roth, base_tax = simulate(False)
    conv_trad, conv_roth, conv_tax = simulate(True)

    eff_conv = annual_conv if annual_conv > 0 else 0.0
    total_converted = eff_conv * conv_years
    total_conv_tax = eff_conv * mtr * conv_years

    return {
        "annual_conversion_amount": round(annual_conv, 2),
        "conversion_years": conv_years,
        "conversion_years_positive": conv_years if annual_conv > 0 else 0,
        "first_conversion_year": py,
        "total_converted": round(total_converted, 2),
        "total_conversion_tax": round(total_conv_tax, 2),
        "first_rmd_year": first_rmd_year,
        "horizon_year": horizon_year,
        "baseline_rmd_tax_through_horizon": round(base_tax, 2),
        "conversion_rmd_tax_through_horizon": round(conv_tax, 2),
        "rmd_tax_savings_through_horizon": round(base_tax - conv_tax, 2),
        "projected_roth_balance_horizon": round(conv_roth, 2),
        "projected_traditional_balance_horizon": round(conv_trad, 2),
    }


def heir_tax_profile(roth_balance, trad_balance):
    total = roth_balance + trad_balance
    if total <= 0:
        return "MIXED_TAXABLE_AND_TAX_FREE"
    roth_frac = roth_balance / total
    if roth_frac >= 0.80:
        return "MOSTLY_TAX_FREE"
    if roth_frac <= 0.20:
        return "MOSTLY_TAXABLE"
    return "MIXED_TAXABLE_AND_TAX_FREE"


# --------------------------------------------------------------------------
# ILIT / Crummey
# --------------------------------------------------------------------------
def crummey_dates(planned_contribution_date):
    """contribution -> +7d notice due -> +30d window end -> +1d earliest pay."""
    cdate = date.fromisoformat(planned_contribution_date)
    notice_due = cdate + timedelta(days=7)
    window_end = notice_due + timedelta(days=30)
    earliest_pay = window_end + timedelta(days=1)
    return {
        "contribution_date": cdate.isoformat(),
        "notice_due_date": notice_due.isoformat(),
        "withdrawal_window_end": window_end.isoformat(),
        "earliest_premium_payment_date": earliest_pay.isoformat(),
    }


def ilit_plan(profile, policy, policies, year):
    bene = int(profile["beneficiary_count"])
    excl = float(policies["annual_gift_exclusion"][str(year)])
    capacity = bene * excl
    premium = float(policy["annual_premium"])
    gap = max(0.0, premium - capacity)
    out = {
        "planning_year": year,
        "annual_exclusion_per_beneficiary": round(excl, 2),
        "beneficiary_count": bene,
        "annual_exclusion_capacity": round(capacity, 2),
        "annual_premium": round(premium, 2),
        "premium_gap": round(gap, 2),
        "notices_required": bene,
        "dedicated_bank_account_required": True,
        "death_benefit": round(float(policy["death_benefit"]), 2),
        "projected_outside_estate_if_implemented": round(float(policy["death_benefit"]), 2),
        "tax_liquidity_support": round(float(profile["liquid_assets"]), 2),
        "is_existing_policy_transfer": bool(policy.get("is_existing_policy_transfer", False)),
    }
    out.update(crummey_dates(policy["planned_contribution_date"]))
    out["risk_flag"] = ilit_risk_flag(gap, out["is_existing_policy_transfer"])
    return out


def ilit_risk_flag(premium_gap, is_transfer):
    shortfall = premium_gap > 0
    if is_transfer and shortfall:
        return "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
    if is_transfer:
        return "THREE_YEAR_LOOKBACK"
    if shortfall:
        return "EXCLUSION_SHORTFALL"
    return "LOW_IF_FORMALITIES_MET"


# --------------------------------------------------------------------------
# GRAT / CRAT  (identical flat-annuity remainder engine)
# --------------------------------------------------------------------------
def flat_annuity_remainder(asset, growth, term_years, payout_rate):
    """remainder = asset*(1+g)^term  -  (asset*payout_rate)*term

    The annuity/payout is a FLAT dollar amount (asset*rate) each year and is NOT
    reinvested. Verified to the cent against GRAT and CRAT gold numbers.
    """
    return asset * (1 + growth) ** term_years - (asset * payout_rate) * term_years


def grat(trust, estate_tax_rate):
    asset = float(trust["asset_value"])
    g = float(trust["expected_growth_rate"])
    term = int(trust["grat_term_years"])
    remainder = flat_annuity_remainder(asset, g, term, float(trust["grat_annuity_rate"]))
    return {
        "term_years": term,
        "projected_remainder_to_heirs": round(remainder, 2),
        "estimated_estate_tax_reduction": round(remainder * estate_tax_rate, 2),
        "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
    }


def crat(trust, policies):
    asset = float(trust["asset_value"])
    g = float(trust["expected_growth_rate"])
    term = min(int(trust["crat_term_years"]), int(policies["max_crat_term_years"]))
    remainder = flat_annuity_remainder(asset, g, term, float(trust["crat_payout_rate"]))
    return {
        "term_years": term,
        "projected_charitable_remainder": round(remainder, 2),
        "estimated_income_tax_deduction": round(remainder * policies["charitable_deduction_rate"], 2),
        "family_transfer_fit": "LOW",
    }


if __name__ == "__main__":
    # Self-test: reproduce the five training gold answers to the cent.
    pol = api("/api/policies/tax")
    rmd = api("/api/rmd-factors")

    def src(cid): return api(f"/api/source-documents?client_id={cid}")
    def acct(cid): return api(f"/api/retirement-accounts?client_id={cid}")[0]
    def life(cid): return api(f"/api/life-insurance?client_id={cid}")[0]
    def tc(cid): return api(f"/api/trust-candidates?client_id={cid}")[0]

    r1 = roth_conversion_rmd(signed_profile(src("CLT-1001")), acct("CLT-1001"), pol, rmd, 2046)
    assert r1["annual_conversion_amount"] == 209600.0
    assert r1["baseline_rmd_tax_through_horizon"] == 1097182.33
    assert r1["projected_roth_balance_horizon"] == 4594320.16

    r5 = roth_conversion_rmd(signed_profile(src("CLT-1005")), acct("CLT-1005"), pol, rmd, 2042)
    assert r5["rmd_tax_savings_through_horizon"] == 112697.88

    i2 = ilit_plan(signed_profile(src("CLT-1002")), life("CLT-1002"), pol, 2026)
    assert i2["annual_exclusion_capacity"] == 80000.0
    assert i2["withdrawal_window_end"] == "2026-04-16"
    assert i2["earliest_premium_payment_date"] == "2026-04-17"

    g3 = grat(tc("CLT-1003"), pol["estate_tax_rate"])
    c3 = crat(tc("CLT-1003"), pol)
    assert g3["projected_remainder_to_heirs"] == 10154624.61
    assert c3["estimated_income_tax_deduction"] == 9970680.0

    g4 = grat(tc("CLT-1004"), pol["estate_tax_rate"])
    assert g4["estimated_estate_tax_reduction"] == 5346980.42

    print("OK: all five training gold figures reproduced to the cent.")
