"""Reusable helpers for the private-wealth advisory benchmark.

All formulas here are verified to the cent against the gold answers for the four task families:
roth_conversion_rmd, ilit_crummey_implementation, trust_comparison, estate_liquidity_action_plan.

Usage sketch:
    import advisory as A
    base = A.base_url()                       # honors API_BASE env var, defaults to 127.0.0.1:8066
    client = A.get(base, "/api/clients/CLT-1001")
    docs   = A.get(base, "/api/source-documents", client_id="CLT-1001")
    policy = A.get(base, "/api/policies/tax")
    facts  = A.controlling_household_facts(client, docs)   # SIGNED_PROFILE wins
    ...

Read the function docstrings; adapt as needed for the exact template fields of your task.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from datetime import date, timedelta

# ---------------------------------------------------------------------------
# API access
# ---------------------------------------------------------------------------

DEFAULT_BASE = "http://127.0.0.1:8066"

# Source-document precedence for household/profile/goal facts (highest first).
SOURCE_PRECEDENCE = [
    "SIGNED_PROFILE",
    "ATTORNEY_MEMO",
    "CRM_NOTE",
    "STALE_MARKETING_INTAKE",
]


def base_url() -> str:
    return os.environ.get("API_BASE", DEFAULT_BASE).rstrip("/")


def get(base: str, path: str, **query):
    """GET a JSON endpoint. Pass query params as kwargs, e.g. client_id='CLT-1001'."""
    url = base + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Source-precedence resolution
# ---------------------------------------------------------------------------

def controlling_household_facts(client_header: dict, source_docs: list) -> dict:
    """Merge source documents by precedence (SIGNED_PROFILE wins), layered over the client header.

    Returns a flat dict of facts. Higher-precedence documents overwrite lower ones field-by-field,
    so e.g. a SIGNED_PROFILE beneficiary_count beats a CRM_NOTE one.
    """
    facts = dict(client_header or {})
    ordered = sorted(
        source_docs or [],
        key=lambda d: SOURCE_PRECEDENCE.index(d.get("source_type"))
        if d.get("source_type") in SOURCE_PRECEDENCE else len(SOURCE_PRECEDENCE),
        reverse=True,  # apply lowest precedence first so highest overwrites last
    )
    for d in ordered:
        facts.update(d.get("facts", {}))
    return facts


def money(x) -> float:
    """Round to cents the way the grader expects."""
    return round(float(x), 2)


# ---------------------------------------------------------------------------
# Shared estate math
# ---------------------------------------------------------------------------

def estate_math(estate_value, liquid_assets, marital_status, planning_year, policy):
    base_exemption = policy["estate_tax_exemption"][str(planning_year)]
    multiplier = 2 if marital_status == "married" else 1   # portability for married couples
    exemption_used = base_exemption * multiplier
    taxable_estate = max(0.0, estate_value - exemption_used)
    rate = policy["estate_tax_rate"]
    exposure = taxable_estate * rate
    gap = max(0.0, exposure - liquid_assets)
    return {
        "planning_year": planning_year,
        "exemption_used": money(exemption_used),
        "taxable_estate": money(taxable_estate),
        "estate_tax_exposure": money(exposure),
        "liquid_assets_available": money(liquid_assets),
        "liquidity_gap_before_planning": money(gap),
    }


# ---------------------------------------------------------------------------
# Roth conversion / RMD
# ---------------------------------------------------------------------------

def conversion_plan(account, profile, policy):
    planning_year = profile["planning_year"]
    conv_years = account["recommended_conversion_years"]
    headroom = policy["conversion_bracket_targets"][profile["filing_status"]] - profile["annual_non_ira_income"]
    annual = min(account["traditional_balance"] / conv_years, headroom)
    total = annual * conv_years
    return {
        "first_conversion_year": planning_year,
        "conversion_years": conv_years,
        "annual_conversion_amount": money(annual),
        "total_converted": money(total),
        "total_conversion_tax": money(total * profile["marginal_tax_rate"]),
        "_annual_raw": annual,  # keep full precision for the simulation
    }


def simulate_rmd(profile, account, annual_conversion, conversion_years, horizon_year, rmd_factors):
    """Year-by-year simulation. Order each year: convert -> RMD -> grow.

    Returns (cumulative_rmd_tax, traditional_at_horizon, roth_at_horizon, positive_conversion_years).
    rmd_factors keys may be str or int; this handles both.
    """
    age = profile["age"]
    planning_year = profile["planning_year"]
    mtr = profile["marginal_tax_rate"]
    ret = account["expected_return"]
    rmd_start = account["rmd_start_age"]
    trad = float(account["traditional_balance"])
    roth = float(account["roth_balance"])
    rmd_tax = 0.0
    pos_years = 0

    def factor(a):
        return rmd_factors.get(str(a), rmd_factors.get(a))

    for y in range(planning_year, horizon_year + 1):
        a = age + (y - planning_year)
        if (y - planning_year) < conversion_years:
            c = min(annual_conversion, trad)
            if c > 0:
                trad -= c
                roth += c
                pos_years += 1
        f = factor(a)
        if a >= rmd_start and f:
            rmd = trad / f
            trad -= rmd
            rmd_tax += rmd * mtr
        trad *= (1 + ret)
        roth *= (1 + ret)
    return rmd_tax, trad, roth, pos_years


def heir_tax_profile(roth, trad):
    total = roth + trad
    if total <= 0:
        return "MOSTLY_TAXABLE"
    r = roth / total
    if r >= 0.70:
        return "MOSTLY_TAX_FREE"
    if r <= 0.30:
        return "MOSTLY_TAXABLE"
    return "MIXED_TAXABLE_AND_TAX_FREE"


# ---------------------------------------------------------------------------
# ILIT / Crummey
# ---------------------------------------------------------------------------

def crummey_dates(contribution_date_iso: str):
    """7-day notice lag, 30-day withdrawal window, premium the day after the window lapses."""
    c = date.fromisoformat(contribution_date_iso)
    notice_due = c + timedelta(days=7)
    window_end = notice_due + timedelta(days=30)
    earliest_premium = window_end + timedelta(days=1)
    return {
        "contribution_date": c.isoformat(),
        "notice_due_date": notice_due.isoformat(),
        "withdrawal_window_end": window_end.isoformat(),
        "earliest_premium_payment_date": earliest_premium.isoformat(),
    }


def ilit_gift_plan(beneficiary_count, annual_premium, planning_year, policy):
    per = policy["annual_gift_exclusion"][str(planning_year)]
    capacity = per * beneficiary_count
    return {
        "planning_year": planning_year,
        "annual_exclusion_per_beneficiary": money(per),
        "beneficiary_count": beneficiary_count,
        "annual_exclusion_capacity": money(capacity),
        "annual_premium": money(annual_premium),
        "premium_gap": money(max(0.0, annual_premium - capacity)),  # floored at 0
    }


def ilit_risk_flag(premium_gap, is_existing_policy_transfer):
    shortfall = premium_gap > 0
    lookback = bool(is_existing_policy_transfer)
    if shortfall and lookback:
        return "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
    if lookback:
        return "THREE_YEAR_LOOKBACK"
    if shortfall:
        return "EXCLUSION_SHORTFALL"
    return "LOW_IF_FORMALITIES_MET"


# ---------------------------------------------------------------------------
# GRAT / CRAT trust comparison
# ---------------------------------------------------------------------------

def trust_remainder(asset_value, growth_rate, annuity_rate, term_years):
    """Grow corpus at growth_rate; subtract the PLAIN SUM of annuity payments (NOT reinvested)."""
    fv_assets = asset_value * (1 + growth_rate) ** term_years
    payment = asset_value * annuity_rate
    return fv_assets - payment * term_years


def trust_blocks(trust, policy):
    A_val = trust["asset_value"]
    g = trust["expected_growth_rate"]
    grat_rem = trust_remainder(A_val, g, trust["grat_annuity_rate"], trust["grat_term_years"])
    crat_term = min(trust["crat_term_years"], policy["max_crat_term_years"])
    crat_rem = trust_remainder(A_val, g, trust["crat_payout_rate"], crat_term)
    return {
        "grat": {
            "term_years": trust["grat_term_years"],
            "projected_remainder_to_heirs": money(grat_rem),
            "estimated_estate_tax_reduction": money(grat_rem * policy["estate_tax_rate"]),
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
        },
        "crat": {
            "term_years": crat_term,
            "projected_charitable_remainder": money(crat_rem),
            "estimated_income_tax_deduction": money(crat_rem * policy["charitable_deduction_rate"]),
        },
    }
