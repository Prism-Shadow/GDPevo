#!/usr/bin/env python3
"""Reference implementation of the core advisory computations.

Use this module from a solver script as a verifiable source of truth for
RMD projections, GRAT/CRAT remainders, ILIT dates, and estate context.
Always pull input values from the live API; do not hard-code them here.
"""

from datetime import date, timedelta
from typing import Optional


def rmd_simulation(
    *,
    traditional_balance: float,
    roth_balance: float,
    expected_return: float,
    marginal_tax_rate: float,
    rmd_factors: dict[int, float],
    rmd_start_age: int,
    client_age: int,
    planning_year: int,
    horizon_year: int,
    annual_conversion_amount: float = 0.0,
    conversion_start_year: int | None = None,
    conversion_years: int = 0,
) -> dict:
    """Run a year-by-year RMD simulation, optionally with Roth conversions.

    Returns a dict with keys:
      - rmd_tax_total: total RMD tax over the projection
      - final_traditional_balance
      - final_roth_balance
    """
    conv_start = conversion_start_year or planning_year
    conv_end = conv_start + conversion_years

    trad = traditional_balance
    roth = roth_balance
    tax_total = 0.0

    for year in range(planning_year, horizon_year + 1):
        age = client_age + (year - planning_year)

        if conv_start <= year < conv_end:
            amt = min(annual_conversion_amount, trad)
            trad -= amt
            roth += amt

        if age >= rmd_start_age:
            divisor = rmd_factors[age]
            rmd = trad / divisor
            trad -= rmd
            tax_total += rmd * marginal_tax_rate

        trad *= (1 + expected_return)
        roth *= (1 + expected_return)

    return {
        "rmd_tax_total": round(tax_total, 2),
        "final_traditional_balance": round(max(trad, 0), 2),
        "final_roth_balance": round(roth, 2),
    }


def grat_remainder(
    asset_value: float,
    expected_growth_rate: float,
    term_years: int,
    annuity_rate: float,
) -> float:
    """Compute GRAT projected remainder to heirs."""
    annuity = asset_value * annuity_rate
    fv = asset_value * (1 + expected_growth_rate) ** term_years
    return round(fv - (term_years * annuity), 2)


def crat_charitable_remainder(
    asset_value: float,
    expected_growth_rate: float,
    term_years: int,
    payout_rate: float,
) -> float:
    """Compute CRAT projected charitable remainder."""
    annuity = asset_value * payout_rate
    fv = asset_value * (1 + expected_growth_rate) ** term_years
    return round(fv - (term_years * annuity), 2)


def ilit_dates(contribution_date_str: str) -> dict:
    """Compute ILIT Crummey notice timeline from the planned contribution date."""
    contrib = date.fromisoformat(contribution_date_str)
    notice = contrib + timedelta(days=7)
    withdrawal_end = notice + timedelta(days=30)
    earliest_premium = withdrawal_end + timedelta(days=1)
    return {
        "contribution_date": contrib.isoformat(),
        "notice_due_date": notice.isoformat(),
        "withdrawal_window_end": withdrawal_end.isoformat(),
        "earliest_premium_payment_date": earliest_premium.isoformat(),
    }


def estate_context(
    estate_value: float,
    exemption_used: float,
    estate_tax_rate: float,
    liquid_assets: float,
) -> dict:
    """Compute taxable estate, exposure, and liquidity gap."""
    taxable = estate_value - exemption_used
    exposure = round(taxable * estate_tax_rate, 2)
    gap = round(max(0.0, exposure - liquid_assets), 2)
    return {
        "taxable_estate": taxable,
        "estate_tax_exposure": exposure,
        "liquidity_gap_before_planning": gap,
    }


def annual_conversion_amount(
    bracket_target: float,
    annual_non_ira_income: float,
) -> float:
    """Derive the annual Roth conversion amount from bracket headroom."""
    return round(max(0.0, bracket_target - annual_non_ira_income), 2)


def ilit_risk(
    is_existing_policy_transfer: bool,
    premium_gap: float,
) -> str:
    """Determine ILIT estate inclusion risk."""
    if not is_existing_policy_transfer:
        if premium_gap == 0:
            return "LOW_IF_FORMALITIES_MET"
        return "EXCLUSION_SHORTFALL"
    else:
        if premium_gap == 0:
            return "THREE_YEAR_LOOKBACK"
        return "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
