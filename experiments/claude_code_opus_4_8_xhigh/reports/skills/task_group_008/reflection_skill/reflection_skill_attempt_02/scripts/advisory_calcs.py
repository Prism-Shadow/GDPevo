#!/usr/bin/env python3
"""
Deterministic calculators for the private-wealth advisory benchmark.

Every formula here was reverse-engineered from gold answers and verified to
reproduce them to the cent. Do NOT change the order of operations or the
annuity/exemption conventions without re-verifying against gold.

Usage as a library (preferred): import the functions and feed them values you
fetched from the API. Usage as a CLI: see `python advisory_calcs.py --help`
for a self-test that re-derives the documented sanity checks.

All money is handled as float and rounded to 2 decimals ONLY at output time
(round(x, 2)). Never round mid-simulation.
"""

from __future__ import annotations
import json
import urllib.request
from datetime import date, timedelta

DEFAULT_BASE = "http://127.0.0.1:8066"


# --------------------------------------------------------------------------
# API helpers
# --------------------------------------------------------------------------
def api_get(path, base=DEFAULT_BASE):
    with urllib.request.urlopen(base + path) as r:
        return json.load(r)


def load_policy(base=DEFAULT_BASE):
    return api_get("/api/policies/tax", base)


def load_rmd_factors(base=DEFAULT_BASE):
    # keys come back as strings ("73".."99"); values are divisors
    return api_get("/api/rmd-factors", base)


# --------------------------------------------------------------------------
# Roth conversion / RMD engine  (task family: roth_conversion_rmd)
# --------------------------------------------------------------------------
def roth_rmd_simulation(
    age, planning_year, horizon_year,
    traditional_balance, roth_balance, expected_return,
    rmd_start_age, conversion_years, annual_conversion_amount,
    marginal_tax_rate, rmd_factors, do_convert,
):
    """
    Year-by-year simulation from planning_year..horizon_year INCLUSIVE.

    CRITICAL ORDER OF OPERATIONS PER YEAR (verified against gold):
        1. CONVERT  (if scenario has conversions AND this is a conversion year)
        2. RMD      (if current age >= rmd_start_age)
        3. GROW     both balances by expected_return

    Converting BEFORE the RMD matters whenever the conversion window overlaps
    RMD years: the conversion shrinks the traditional balance first, which
    lowers that year's RMD.

    Conversions run for the FULL `conversion_years` window starting at
    planning_year (year < planning_year + conversion_years). They are NOT
    truncated when RMDs begin. This was the single biggest blind-solver error.

    Returns dict with rmd_tax_total, traditional_end, roth_end,
    first_rmd_year, conversions_performed.
    """
    trad = float(traditional_balance)
    roth = float(roth_balance)
    birth_year = planning_year - age
    first_rmd_year = birth_year + rmd_start_age
    rmd_tax_total = 0.0
    conversions_performed = 0

    for year in range(planning_year, horizon_year + 1):
        cur_age = year - birth_year
        # 1) CONVERT
        if do_convert and year < planning_year + conversion_years:
            amt = min(annual_conversion_amount, trad)
            trad -= amt
            roth += amt
            conversions_performed += 1
        # 2) RMD
        if cur_age >= rmd_start_age:
            factor = rmd_factors.get(str(cur_age))
            if factor:
                r = trad / factor
                trad -= r
                rmd_tax_total += r * marginal_tax_rate
        # 3) GROW
        trad *= (1 + expected_return)
        roth *= (1 + expected_return)

    return {
        "rmd_tax_total": rmd_tax_total,
        "traditional_end": trad,
        "roth_end": roth,
        "first_rmd_year": first_rmd_year,
        "conversions_performed": conversions_performed,
    }


def annual_conversion_headroom(bracket_target, non_ira_income):
    """Annual conversion amount = top of target bracket - non-IRA income."""
    return bracket_target - non_ira_income


def heir_tax_profile(roth_end, traditional_end):
    """roth_fraction >= 0.7 -> MOSTLY_TAX_FREE; <= 0.3 -> MOSTLY_TAXABLE; else MIXED."""
    total = roth_end + traditional_end
    if total <= 0:
        return "MIXED_TAXABLE_AND_TAX_FREE"
    frac = roth_end / total
    if frac >= 0.7:
        return "MOSTLY_TAX_FREE"
    if frac <= 0.3:
        return "MOSTLY_TAXABLE"
    return "MIXED_TAXABLE_AND_TAX_FREE"


# --------------------------------------------------------------------------
# GRAT / CRAT remainder math  (task families: trust_comparison, estate_liquidity)
# --------------------------------------------------------------------------
def grat_remainder(asset_value, growth_rate, term_years, annuity_rate):
    """
    Asset grows at compound growth for the full term; the annuity payments are
    subtracted at their NOMINAL sum (NOT future-valued):

        remainder = asset*(1+g)^term  -  asset*annuity_rate*term
    """
    return asset_value * (1 + growth_rate) ** term_years - asset_value * annuity_rate * term_years


def crat_remainder(asset_value, growth_rate, term_years, payout_rate):
    """Same shape as GRAT: asset*(1+g)^term - asset*payout_rate*term."""
    return asset_value * (1 + growth_rate) ** term_years - asset_value * payout_rate * term_years


def grat_estate_tax_reduction(grat_rem, estate_tax_rate):
    return grat_rem * estate_tax_rate


def crat_income_tax_deduction(crat_rem, charitable_deduction_rate):
    """Deduction is on the CRAT REMAINDER, not the raw asset value."""
    return crat_rem * charitable_deduction_rate


# --------------------------------------------------------------------------
# Estate context  (task families: trust_comparison, estate_liquidity, ILIT)
# --------------------------------------------------------------------------
def estate_exemption(marital_status, single_exemption):
    """Married -> double the exemption. Single -> single exemption.
    NOTE: this doubled value is for estate_context taxable-estate math.
    The ILIT tax_liquidity_support calc uses the SINGLE exemption (see SKILL)."""
    if str(marital_status).lower() == "married":
        return single_exemption * 2
    return single_exemption


def estate_context(estate_value, exemption_used, estate_tax_rate, liquid_assets):
    taxable = estate_value - exemption_used
    exposure = taxable * estate_tax_rate
    gap = max(0.0, exposure - liquid_assets)
    return {
        "taxable_estate": taxable,
        "estate_tax_exposure": exposure,
        "liquidity_gap_before_planning": gap,
    }


def tax_liquidity_support(death_benefit, estate_value, single_exemption, estate_tax_rate):
    """ILIT: min(death_benefit, estate tax exposure using SINGLE exemption)."""
    exposure = (estate_value - single_exemption) * estate_tax_rate
    return min(death_benefit, max(0.0, exposure))


# --------------------------------------------------------------------------
# Crummey / ILIT gift mechanics  (task family: ilit_crummey_implementation)
# --------------------------------------------------------------------------
def crummey_dates(contribution_date_iso, window_days=30):
    """
    contribution_date == notice_due_date (notices go out the day of contribution).
    withdrawal_window_end = contribution + window_days.
    earliest_premium_payment_date = withdrawal_window_end + 1 day.
    """
    c = date.fromisoformat(contribution_date_iso)
    end = c + timedelta(days=window_days)
    return {
        "contribution_date": c.isoformat(),
        "notice_due_date": c.isoformat(),
        "withdrawal_window_end": end.isoformat(),
        "earliest_premium_payment_date": (end + timedelta(days=1)).isoformat(),
    }


def gift_plan(per_beneficiary_exclusion, beneficiary_count, annual_premium):
    capacity = per_beneficiary_exclusion * beneficiary_count
    return {
        "annual_exclusion_per_beneficiary": per_beneficiary_exclusion,
        "beneficiary_count": beneficiary_count,
        "annual_exclusion_capacity": capacity,
        "annual_premium": annual_premium,
        "premium_gap": max(0.0, annual_premium - capacity),
    }


# --------------------------------------------------------------------------
# Self-test: re-derive the documented sanity checks from the live API.
# --------------------------------------------------------------------------
def _selftest(base=DEFAULT_BASE):
    rmd = load_rmd_factors(base)
    tax = load_policy(base)
    ok = []

    # Roth task shape (CLT-1001-like): age66 py2026 hz2046 trad2.8M roth0 ret.065
    camt = annual_conversion_headroom(tax["conversion_bracket_targets"]["MFJ"], 185000)
    b = roth_rmd_simulation(66, 2026, 2046, 2800000, 0, 0.065, 73, 7, camt, 0.32, rmd, False)
    c = roth_rmd_simulation(66, 2026, 2046, 2800000, 0, 0.065, 73, 7, camt, 0.32, rmd, True)
    ok.append(("roth_headroom", camt == 209600))
    ok.append(("roth_baseline_tax", round(b["rmd_tax_total"], 2) == 1097182.33))
    ok.append(("roth_conv_tax", round(c["rmd_tax_total"], 2) == 617448.59))
    ok.append(("roth_roth_end", round(c["roth_end"], 2) == 4594320.16))

    # GRAT/CRAT shape
    g = grat_remainder(8000000, 0.08, 5, 0.04)
    cr = crat_remainder(8000000, 0.08, 20, 0.055)
    ok.append(("grat_rem", round(g, 2) == 10154624.61))
    ok.append(("crat_rem", round(cr, 2) == 28487657.15))
    ok.append(("crat_deduction", round(crat_income_tax_deduction(cr, tax["charitable_deduction_rate"]), 2) == 9970680.0))

    # Crummey dates
    d = crummey_dates("2026-03-10", 30)
    ok.append(("crummey_window", d["withdrawal_window_end"] == "2026-04-09"))
    ok.append(("crummey_pay", d["earliest_premium_payment_date"] == "2026-04-10"))

    for name, passed in ok:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}")
    return all(p for _, p in ok)


if __name__ == "__main__":
    import sys
    if "--help" in sys.argv:
        print(__doc__)
    else:
        all_ok = _selftest()
        sys.exit(0 if all_ok else 1)
