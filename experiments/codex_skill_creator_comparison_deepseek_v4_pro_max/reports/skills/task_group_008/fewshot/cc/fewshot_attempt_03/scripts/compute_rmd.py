#!/usr/bin/env python3
"""
Deterministic RMD projection engine for private wealth advisory.

Computes baseline and conversion RMD tax projections plus legacy balances
given resolved client facts. Run as a standalone validation script or import
its functions.

Usage:
    python compute_rmd.py --input <facts.json> --output <result.json>

The input JSON must supply all resolved facts. See the --help output for
the full schema.
"""

import argparse
import json
import sys
from typing import Any


def compute_roth_conversion(facts: dict[str, Any]) -> dict[str, Any]:
    """
    Compute the full roth_conversion_rmd output block from resolved facts.

    Required facts keys:
        client_id, planning_year, age, filing_status,
        annual_non_ira_income, marginal_tax_rate,
        traditional_balance, roth_balance, expected_return,
        rmd_start_age, recommended_conversion_years,
        conversion_bracket_target, rmd_factors (dict age->factor),
        horizon_year, liquid_assets,
        controlling_profile_source, controlling_account_source,
        task_id
    """
    planning_year = facts["planning_year"]
    age = facts["age"]
    income = facts["annual_non_ira_income"]
    marginal = facts["marginal_tax_rate"]
    bracket = facts["conversion_bracket_target"]
    trad = facts["traditional_balance"]
    roth = facts["roth_balance"]
    rate = facts["expected_return"]
    rmd_start = facts["rmd_start_age"]
    conv_years = facts["recommended_conversion_years"]
    rmd_factors = facts["rmd_factors"]
    horizon = facts["horizon_year"]
    liquid = facts.get("liquid_assets", 0)

    annual_conv = round(bracket - income, 2)
    total_conv = round(annual_conv * conv_years, 2)
    conv_tax = round(total_conv * marginal, 2)

    first_rmd = planning_year + (rmd_start - age)

    # --- Baseline RMD ---
    bal = trad
    for y in range(planning_year, first_rmd):
        bal *= (1 + rate)
    base_tax = 0.0
    for y in range(first_rmd, horizon + 1):
        a = age + (y - planning_year)
        factor = rmd_factors.get(str(a))
        if factor is None:
            continue
        rmd = bal / factor
        base_tax += rmd * marginal
        bal = (bal - rmd) * (1 + rate)

    # --- Conversion RMD (with overlap handling) ---
    bal_c = trad
    conv_rmd_tax = 0.0
    for y in range(planning_year, horizon + 1):
        is_conv_year = y < planning_year + conv_years
        is_rmd_year = y >= first_rmd

        if is_conv_year:
            bal_c -= annual_conv

        if is_rmd_year:
            a = age + (y - planning_year)
            factor = rmd_factors.get(str(a))
            if factor is not None:
                rmd = bal_c / factor
                conv_rmd_tax += rmd * marginal
                bal_c -= rmd

        bal_c *= (1 + rate)

    savings = round(base_tax - conv_rmd_tax, 2)
    base_tax = round(base_tax, 2)
    conv_rmd_tax = round(conv_rmd_tax, 2)

    # --- Legacy ---
    roth_h = roth
    for y in range(planning_year, planning_year + conv_years):
        roth_h = (roth_h + annual_conv) * (1 + rate)
    for y in range(planning_year + conv_years, horizon + 1):
        roth_h *= (1 + rate)
    roth_h = round(roth_h, 2)

    trad_h = round(bal_c, 2)

    if roth_h > 3 * trad_h:
        heir = "MOSTLY_TAX_FREE"
    elif trad_h > 3 * roth_h:
        heir = "MOSTLY_TAXABLE"
    else:
        heir = "MIXED_TAXABLE_AND_TAX_FREE"

    # --- Enums ---
    if conv_years < 1 or annual_conv <= 0:
        primary = "NO_CONVERSION"
    elif first_rmd <= planning_year + 2 and savings < 1000:
        primary = "DEFER"
    else:
        primary = "STAGED_ROTH_CONVERSION"

    if primary == "STAGED_ROTH_CONVERSION":
        suit = "SUITABLE"
    elif primary == "DEFER":
        suit = "DEFER"
    else:
        suit = "DEFER"

    if primary == "STAGED_ROTH_CONVERSION":
        if liquid < 2 * conv_tax:
            risk = "LIQUIDITY_CONSTRAINT"
        elif first_rmd <= planning_year + 2:
            risk = "RMD_NEAR_TERM"
        else:
            risk = "TAX_BRACKET_MANAGEMENT"
    elif primary == "DEFER":
        risk = "RMD_NEAR_TERM"
    else:
        risk = "TAX_BRACKET_MANAGEMENT"

    return {
        "task_id": facts["task_id"],
        "client_id": facts["client_id"],
        "analysis_type": "roth_conversion_rmd",
        "recommendation": {
            "primary_action": primary,
            "suitability": suit,
            "risk_flag": risk,
        },
        "conversion_plan": {
            "first_conversion_year": planning_year,
            "conversion_years": conv_years,
            "conversion_years_positive": conv_years,
            "annual_conversion_amount": annual_conv,
            "total_converted": total_conv,
            "total_conversion_tax": conv_tax,
        },
        "rmd_projection": {
            "horizon_year": horizon,
            "first_rmd_year": first_rmd,
            "baseline_rmd_tax_through_horizon": base_tax,
            "conversion_rmd_tax_through_horizon": conv_rmd_tax,
            "rmd_tax_savings_through_horizon": savings,
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": roth_h,
            "projected_traditional_balance_horizon": trad_h,
            "heir_tax_profile": heir,
        },
        "source_resolution": {
            "controlling_profile_source": facts["controlling_profile_source"],
            "controlling_account_source": facts["controlling_account_source"],
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="RMD projection engine")
    parser.add_argument("--input", required=True, help="JSON facts file")
    parser.add_argument("--output", required=True, help="Output JSON file")
    args = parser.parse_args()

    with open(args.input) as f:
        facts = json.load(f)
    result = compute_roth_conversion(facts)
    with open(args.output, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
