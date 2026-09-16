#!/usr/bin/env python3
"""Deterministic wealth advisory computations from API data.

Usage:
  python3 compute.py roth <params.json>
  python3 compute.py ilit <params.json>
  python3 compute.py trust <params.json>
  python3 compute.py estate <params.json>

Each subcommand reads a JSON object from stdin (or a file path argument)
with the relevant API-derived parameters and prints the computed fields as JSON.

The computation formulas follow the reference at references/formulas.md.
"""

import json
import sys
from datetime import date, timedelta


def compute_roth(params):
    """Roth conversion and RMD projection."""
    traditional_balance = params["traditional_balance"]
    roth_balance = params["roth_balance"]
    expected_return = params["expected_return"]
    marginal_tax_rate = params["marginal_tax_rate"]
    bracket_target = params["bracket_target"]
    annual_non_ira_income = params["annual_non_ira_income"]
    conversion_years = params["conversion_years"]
    rmd_start_age = params["rmd_start_age"]
    age = params["age"]
    planning_year = params["planning_year"]
    horizon_year = params["horizon_year"]
    rmd_factors = params["rmd_factors"]  # dict string_key -> float

    # Conversion plan
    annual_conversion_amount = bracket_target - annual_non_ira_income
    max_annual = traditional_balance / conversion_years
    if annual_conversion_amount > max_annual:
        annual_conversion_amount = max_annual
    if annual_conversion_amount < 0:
        annual_conversion_amount = 0

    total_converted = annual_conversion_amount * conversion_years
    total_conversion_tax = total_converted * marginal_tax_rate

    # First RMD year
    first_rmd_year = planning_year + (rmd_start_age - age)

    # Baseline projection (no conversions)
    bal_baseline = traditional_balance
    baseline_tax_sum = 0.0
    for yr in range(planning_year, horizon_year + 1):
        yr_age = age + (yr - planning_year)
        if yr >= first_rmd_year:
            div = rmd_factors.get(str(yr_age), 999)
            rmd = bal_baseline / div
            tax = rmd * marginal_tax_rate
            baseline_tax_sum += tax
            bal_baseline -= rmd
        bal_baseline *= (1 + expected_return)

    # Conversion scenario
    bal_trad = traditional_balance
    bal_roth = roth_balance
    conversion_tax_sum = 0.0
    conv_years_count = 0
    for yr in range(planning_year, horizon_year + 1):
        yr_age = age + (yr - planning_year)
        # Apply conversion if in conversion window
        if conv_years_count < conversion_years:
            bal_trad -= annual_conversion_amount
            bal_roth += annual_conversion_amount
            conv_years_count += 1
        # Apply RMD if applicable
        if yr >= first_rmd_year:
            div = rmd_factors.get(str(yr_age), 999)
            rmd = bal_trad / div
            tax = rmd * marginal_tax_rate
            conversion_tax_sum += tax
            bal_trad -= rmd
        # Grow balances
        bal_trad *= (1 + expected_return)
        bal_roth *= (1 + expected_return)

    rmd_tax_savings = baseline_tax_sum - conversion_tax_sum

    return {
        "conversion_plan": {
            "first_conversion_year": planning_year,
            "conversion_years": conversion_years,
            "conversion_years_positive": conversion_years,
            "annual_conversion_amount": round(annual_conversion_amount, 2),
            "total_converted": round(total_converted, 2),
            "total_conversion_tax": round(total_conversion_tax, 2)
        },
        "rmd_projection": {
            "horizon_year": horizon_year,
            "first_rmd_year": first_rmd_year,
            "baseline_rmd_tax_through_horizon": round(baseline_tax_sum, 2),
            "conversion_rmd_tax_through_horizon": round(conversion_tax_sum, 2),
            "rmd_tax_savings_through_horizon": round(rmd_tax_savings, 2)
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": round(bal_roth, 2),
            "projected_traditional_balance_horizon": round(bal_trad, 2),
            "heir_tax_profile": (
                "MOSTLY_TAX_FREE" if bal_roth > 2 * bal_trad
                else "MOSTLY_TAXABLE" if bal_trad > 2 * bal_roth
                else "MIXED_TAXABLE_AND_TAX_FREE"
            )
        }
    }


def compute_ilit(params):
    """ILIT Crummey funding computations."""
    annual_exclusion_per_beneficiary = params["annual_exclusion_per_beneficiary"]
    beneficiary_count = params["beneficiary_count"]
    annual_premium = params["annual_premium"]
    death_benefit = params["death_benefit"]
    contribution_date_str = params["contribution_date"]
    estate_tax_rate = params["estate_tax_rate"]
    planning_year = params["planning_year"]
    is_existing_policy_transfer = params.get("is_existing_policy_transfer", False)

    annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count
    premium_gap = max(0.0, annual_premium - annual_exclusion_capacity)

    contribution_date = date.fromisoformat(contribution_date_str)
    notice_due = contribution_date + timedelta(days=7)
    withdrawal_end = notice_due + timedelta(days=30)
    earliest_payment = withdrawal_end + timedelta(days=1)

    tax_liquidity_support = death_benefit * estate_tax_rate
    projected_outside = death_benefit

    # Risk determination
    if is_existing_policy_transfer and premium_gap > 0:
        risk_flag = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
        primary_action = "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION"
    elif is_existing_policy_transfer:
        risk_flag = "THREE_YEAR_LOOKBACK"
        primary_action = "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK"
    elif premium_gap > 0:
        risk_flag = "EXCLUSION_SHORTFALL"
        primary_action = "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL"
    else:
        risk_flag = "LOW_IF_FORMALITIES_MET"
        primary_action = "FUND_WITH_CRUMMEY_NOTICES"

    return {
        "gift_plan": {
            "planning_year": planning_year,
            "annual_exclusion_per_beneficiary": annual_exclusion_per_beneficiary,
            "beneficiary_count": beneficiary_count,
            "annual_exclusion_capacity": round(annual_exclusion_capacity, 2),
            "annual_premium": round(annual_premium, 2),
            "premium_gap": round(premium_gap, 2)
        },
        "administration": {
            "notices_required": beneficiary_count,
            "contribution_date": contribution_date_str,
            "notice_due_date": notice_due.isoformat(),
            "withdrawal_window_end": withdrawal_end.isoformat(),
            "earliest_premium_payment_date": earliest_payment.isoformat(),
            "dedicated_bank_account_required": True
        },
        "estate_result": {
            "death_benefit": round(death_benefit, 2),
            "estate_inclusion_risk": risk_flag,
            "projected_outside_estate_if_implemented": round(projected_outside, 2),
            "tax_liquidity_support": round(tax_liquidity_support, 2)
        },
        "recommendation": {
            "primary_action": primary_action,
            "suitability": "SUITABLE_WITH_ADMINISTRATION",
            "risk_flag": risk_flag
        }
    }


def compute_trust(params):
    """Trust comparison (GRAT vs CRAT) computations."""
    estate_value = params["estate_value"]
    estate_tax_exemption = params["estate_tax_exemption"]
    estate_tax_rate = params["estate_tax_rate"]
    liquid_assets = params["liquid_assets"]
    planning_year = params["planning_year"]
    asset_value = params["asset_value"]
    expected_growth_rate = params["expected_growth_rate"]
    grat_term_years = params["grat_term_years"]
    grat_annuity_rate = params["grat_annuity_rate"]
    crat_term_years = params["crat_term_years"]
    crat_payout_rate = params["crat_payout_rate"]
    charitable_deduction_rate = params["charitable_deduction_rate"]
    family_transfer_priority = params["family_transfer_priority"]
    philanthropic_intent = params["philanthropic_intent"]

    # Double exemption for MFJ (married filing jointly)
    filing_status = params.get("filing_status", "SINGLE")
    if filing_status == "MFJ":
        estate_tax_exemption = estate_tax_exemption * 2
    
    taxable_estate = max(0.0, estate_value - estate_tax_exemption)
    estate_tax_exposure = taxable_estate * estate_tax_rate
    liquidity_gap = max(0.0, estate_tax_exposure - liquid_assets)

    # GRAT
    grat_growth = asset_value * ((1 + expected_growth_rate) ** grat_term_years)
    grat_annuity = asset_value * grat_annuity_rate * grat_term_years
    grat_remainder = grat_growth - grat_annuity
    grat_tax_reduction = grat_remainder * estate_tax_rate

    # CRAT
    crat_growth = asset_value * ((1 + expected_growth_rate) ** crat_term_years)
    crat_payout = asset_value * crat_payout_rate * crat_term_years
    crat_remainder = crat_growth - crat_payout
    crat_income_deduction = crat_remainder * charitable_deduction_rate

    # Strategy selection
    if family_transfer_priority == "high":
        preferred = "GRAT"
        rationale = "CHILDREN_TRANSFER_PRIORITY"
        alt = "SECONDARY_CHARITABLE_TOOL"
    elif philanthropic_intent == "high":
        preferred = "CRAT"
        rationale = "PHILANTHROPIC_PRIORITY"
        alt = "SECONDARY_FAMILY_TRANSFER_TOOL"
    else:
        preferred = "GRAT"
        rationale = "CHILDREN_TRANSFER_PRIORITY"
        alt = "SECONDARY_CHARITABLE_TOOL"

    ftf = "LOW"  # CRAT family transfer fit when family priority is high

    return {
        "estate_context": {
            "planning_year": planning_year,
            "exemption_used": round(float(estate_tax_exemption), 2),
            "taxable_estate": round(taxable_estate, 2),
            "estate_tax_exposure": round(estate_tax_exposure, 2),
            "liquid_assets_available": round(liquid_assets, 2),
            "liquidity_gap_before_planning": round(liquidity_gap, 2)
        },
        "grat": {
            "term_years": grat_term_years,
            "projected_remainder_to_heirs": round(grat_remainder, 2),
            "estimated_estate_tax_reduction": round(grat_tax_reduction, 2),
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED"
        },
        "crat": {
            "term_years": crat_term_years,
            "projected_charitable_remainder": round(crat_remainder, 2),
            "estimated_income_tax_deduction": round(crat_income_deduction, 2),
            "family_transfer_fit": ftf
        },
        "recommendation": {
            "preferred_strategy": preferred,
            "rationale_code": rationale,
            "alternate_role": alt
        }
    }


def compute_estate(params):
    """Estate liquidity action plan computations."""
    # Estate context (same as trust)
    estate_value = params["estate_value"]
    estate_tax_exemption = params["estate_tax_exemption"]
    estate_tax_rate = params["estate_tax_rate"]
    liquid_assets = params["liquid_assets"]
    planning_year = params["planning_year"]

    # Double exemption for MFJ (married filing jointly)
    filing_status = params.get("filing_status", "SINGLE")
    if filing_status == "MFJ":
        estate_tax_exemption = estate_tax_exemption * 2
    
    taxable_estate = max(0.0, estate_value - estate_tax_exemption)
    estate_tax_exposure = taxable_estate * estate_tax_rate
    liquidity_gap = max(0.0, estate_tax_exposure - liquid_assets)

    # ILIT
    annual_exclusion_per_beneficiary = params["annual_exclusion_per_beneficiary"]
    beneficiary_count = params["beneficiary_count"]
    annual_premium = params["annual_premium"]
    death_benefit = params["death_benefit"]
    is_existing_policy_transfer = params.get("is_existing_policy_transfer", False)

    annual_exclusion_capacity = annual_exclusion_per_beneficiary * beneficiary_count
    premium_gap = max(0.0, annual_premium - annual_exclusion_capacity)
    projected_outside = death_benefit

    if is_existing_policy_transfer and premium_gap > 0:
        risk_flag = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
    elif is_existing_policy_transfer:
        risk_flag = "THREE_YEAR_LOOKBACK"
    elif premium_gap > 0:
        risk_flag = "EXCLUSION_SHORTFALL"
    else:
        risk_flag = "LOW_IF_FORMALITIES_MET"

    # Trust transfer (same computations as trust comparison)
    asset_value = params["asset_value"]
    expected_growth_rate = params["expected_growth_rate"]
    grat_term_years = params["grat_term_years"]
    grat_annuity_rate = params["grat_annuity_rate"]
    crat_term_years = params["crat_term_years"]
    crat_payout_rate = params["crat_payout_rate"]
    charitable_deduction_rate = params["charitable_deduction_rate"]
    family_transfer_priority = params["family_transfer_priority"]
    philanthropic_intent = params["philanthropic_intent"]

    if family_transfer_priority == "high":
        preferred = "GRAT"
    elif philanthropic_intent == "high":
        preferred = "CRAT"
    else:
        preferred = "GRAT"

    grat_growth = asset_value * ((1 + expected_growth_rate) ** grat_term_years)
    grat_annuity = asset_value * grat_annuity_rate * grat_term_years
    grat_remainder = grat_growth - grat_annuity
    grat_tax_reduction = grat_remainder * estate_tax_rate

    crat_growth = asset_value * ((1 + expected_growth_rate) ** crat_term_years)
    crat_payout = asset_value * crat_payout_rate * crat_term_years
    crat_remainder = crat_growth - crat_payout

    # Primary action
    if preferred == "GRAT":
        primary_action = "COMBINE_ILIT_AND_GRAT"
        sequencing = "ILIT_FIRST_THEN_GRAT"
    else:
        primary_action = "CRAT_WITH_LIQUIDITY_REVIEW"
        sequencing = "TRUST_DECISION_FIRST"

    # Action set (alphabetically sorted)
    if preferred == "GRAT":
        action_set = sorted(["ATTORNEY_DRAFT_REVIEW", "GRAT_FOR_APPRECIATING_SHARES", "ILIT_CRUMMEY_NOTICE_CYCLE"])
    else:
        action_set = sorted(["ATTORNEY_DRAFT_REVIEW", "CRAT_FOR_CHARITABLE_REMAINDER", "ILIT_CRUMMEY_NOTICE_CYCLE"])

    return {
        "estate_context": {
            "planning_year": planning_year,
            "exemption_used": round(float(estate_tax_exemption), 2),
            "taxable_estate": round(taxable_estate, 2),
            "estate_tax_exposure": round(estate_tax_exposure, 2),
            "liquid_assets_available": round(liquid_assets, 2),
            "liquidity_gap_before_planning": round(liquidity_gap, 2)
        },
        "ilit": {
            "annual_exclusion_capacity": round(annual_exclusion_capacity, 2),
            "premium_gap": round(premium_gap, 2),
            "estate_inclusion_risk": risk_flag,
            "projected_outside_estate_if_implemented": round(projected_outside, 2)
        },
        "trust_transfer": {
            "preferred_strategy": preferred,
            "projected_remainder_to_heirs": round(grat_remainder, 2),
            "estimated_estate_tax_reduction": round(grat_tax_reduction, 2),
            "projected_charitable_remainder": round(crat_remainder, 2)
        },
        "recommendation": {
            "primary_action": primary_action,
            "sequencing": sequencing,
            "risk_flag": risk_flag
        },
        "action_set": action_set
    }


COMMANDS = {
    "roth": compute_roth,
    "ilit": compute_ilit,
    "trust": compute_trust,
    "estate": compute_estate
}


def main():
    if len(sys.argv) < 2:
        print("Usage: compute.py <command> [params.json]", file=sys.stderr)
        sys.exit(1)

    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"Unknown command: {cmd}. Use: roth, ilit, trust, estate", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) >= 3:
        with open(sys.argv[2]) as f:
            params = json.load(f)
    else:
        params = json.load(sys.stdin)

    result = COMMANDS[cmd](params)
    json.dump(result, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()
