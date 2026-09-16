import json, math
from datetime import date, timedelta

# =============================================================================
# Source resolution helpers
# =============================================================================

SOURCE_PRIORITY_PROFILE = ["SIGNED_PROFILE", "ATTORNEY_MEMO", "CUSTODIAN_EXPORT", "CRM_NOTE", "STALE_MARKETING_INTAKE"]
SOURCE_PRIORITY_ACCOUNT = ["CUSTODIAN_EXPORT", "SIGNED_PROFILE", "CRM_NOTE"]
SOURCE_PRIORITY_POLICY  = ["SIGNED_PROFILE", "ATTORNEY_MEMO", "CUSTODIAN_EXPORT", "CRM_NOTE"]
SOURCE_PRIORITY_TRUST   = ["ATTORNEY_MEMO", "SIGNED_PROFILE", "CRM_NOTE"]
SOURCE_PRIORITY_BENEF   = ["SIGNED_PROFILE", "ATTORNEY_MEMO", "CUSTODIAN_EXPORT", "CRM_NOTE", "STALE_MARKETING_INTAKE"]
SOURCE_PRIORITY_GOAL    = ["SIGNED_PROFILE", "ATTORNEY_MEMO", "CUSTODIAN_EXPORT", "CRM_NOTE", "STALE_MARKETING_INTAKE"]

def best_source(docs, client_id, priority_list):
    """Return the best doc for a client by source priority, picking latest per tier."""
    client_docs = [d for d in docs if d.get("client_id") == client_id and d.get("source_type") in priority_list]
    for src in priority_list:
        matches = [d for d in client_docs if d["source_type"] == src]
        if matches:
            return max(matches, key=lambda d: d.get("effective_date", ""))
    return None

def resolve_profile(docs, client_id):
    """Resolve profile facts. Returns (facts_dict, controlling_source)."""
    doc = best_source(docs, client_id, SOURCE_PRIORITY_PROFILE)
    if doc is None:
        return {}, "SIGNED_PROFILE"
    return doc.get("facts", {}), doc["source_type"]

def resolve_account(accounts, client_id):
    """Resolve account. Returns (acct_dict, controlling_source)."""
    for acct in accounts:
        if acct["client_id"] == client_id:
            return acct, "CUSTODIAN_EXPORT"
    return None, None

def resolve_policy(policies, client_id):
    """Resolve life insurance policy. Returns (pol_dict, controlling_source)."""
    for pol in policies:
        if pol["client_id"] == client_id:
            return pol, "SIGNED_PROFILE"
    return None, None

def resolve_trust(trusts, client_id):
    """Resolve trust candidate. Returns (trust_dict, controlling_source)."""
    for t in trusts:
        if t["client_id"] == client_id:
            return t, "ATTORNEY_MEMO"
    return None, None

def resolve_client(clients, client_id):
    """Find client record. Returns client_dict or None."""
    for c in clients:
        if c["client_id"] == client_id:
            return c
    return None

def resolve_beneficiary_source(docs, client_id):
    doc = best_source(docs, client_id, SOURCE_PRIORITY_BENEF)
    return doc["source_type"] if doc else "SIGNED_PROFILE"

def resolve_policy_source_from_docs(docs, client_id):
    doc = best_source(docs, client_id, SOURCE_PRIORITY_POLICY)
    return doc["source_type"] if doc else "SIGNED_PROFILE"

def resolve_goal_source(docs, client_id):
    doc = best_source(docs, client_id, SOURCE_PRIORITY_GOAL)
    return doc["source_type"] if doc else "SIGNED_PROFILE"

def resolve_asset_source(docs, client_id):
    doc = best_source(docs, client_id, SOURCE_PRIORITY_TRUST)
    return doc["source_type"] if doc else "ATTORNEY_MEMO"

# =============================================================================
# Roth conversion / RMD analysis
# =============================================================================

def compute_roth_conversion_rmd(params):
    income = params["income"]
    bracket_target = params["bracket_target"]
    marginal_rate = params["marginal_rate"]
    trad = params["trad_balance"]
    roth = params["roth_balance"]
    r = params["expected_return"]
    conv_years = params["conversion_years"]
    rmd_start = params["rmd_start_age"]
    planning_yr = params["planning_year"]
    horizon = params["horizon_year"]
    rmd_factors = params["rmd_factors"]
    age_now = params["age"]
    liquid_assets = params.get("liquid_assets", float("inf"))

    annual_conv = round(max(0.0, bracket_target - income), 2)
    total_conv = round(annual_conv * conv_years, 2)
    total_conv_tax = round(total_conv * marginal_rate, 2)
    first_rmd_year = planning_yr + (rmd_start - age_now)

    # Baseline scenario
    bal = float(trad)
    baseline_tax = 0.0
    for yr in range(planning_yr, horizon + 1):
        age = age_now + (yr - planning_yr)
        if age >= rmd_start:
            rmd = bal / rmd_factors[age]
            baseline_tax += rmd * marginal_rate
            bal -= rmd
        bal *= (1 + r)

    # Conversion scenario
    trad2 = float(trad)
    roth2 = float(roth)
    last_conv = planning_yr + conv_years - 1
    conv_rmd_tax = 0.0
    for yr in range(planning_yr, horizon + 1):
        age = age_now + (yr - planning_yr)
        if yr <= last_conv:
            trad2 -= annual_conv
            roth2 += annual_conv
        if age >= rmd_start:
            rmd = trad2 / rmd_factors[age]
            conv_rmd_tax += rmd * marginal_rate
            trad2 -= rmd
        trad2 *= (1 + r)
        roth2 *= (1 + r)

    savings = round(baseline_tax - conv_rmd_tax, 2)
    baseline_tax = round(baseline_tax, 2)
    conv_rmd_tax = round(conv_rmd_tax, 2)
    roth_horizon = round(roth2, 2)
    trad_horizon = round(trad2, 2)

    # Heir tax profile
    if roth_horizon > 3.0 * trad_horizon:
        heir = "MOSTLY_TAX_FREE"
    elif trad_horizon > 3.0 * roth_horizon:
        heir = "MOSTLY_TAXABLE"
    else:
        heir = "MIXED_TAXABLE_AND_TAX_FREE"

    # Recommendation
    yrs_to_rmd = rmd_start - age_now
    if savings > 0 and annual_conv > 0:
        action = "STAGED_ROTH_CONVERSION"
        suit = "SUITABLE"
    elif annual_conv > 0:
        action = "DEFER"
        suit = "BORDERLINE"
    else:
        action = "NO_CONVERSION"
        suit = "DEFER"

    # Risk flag
    if total_conv_tax > liquid_assets:
        risk = "LIQUIDITY_CONSTRAINT"
    elif yrs_to_rmd <= 2:
        risk = "RMD_NEAR_TERM"
    else:
        risk = "TAX_BRACKET_MANAGEMENT"

    return {
        "conversion_plan": {
            "first_conversion_year": planning_yr,
            "conversion_years": conv_years,
            "conversion_years_positive": conv_years,
            "annual_conversion_amount": annual_conv,
            "total_converted": total_conv,
            "total_conversion_tax": total_conv_tax,
        },
        "rmd_projection": {
            "horizon_year": horizon,
            "first_rmd_year": first_rmd_year,
            "baseline_rmd_tax_through_horizon": baseline_tax,
            "conversion_rmd_tax_through_horizon": conv_rmd_tax,
            "rmd_tax_savings_through_horizon": savings,
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": roth_horizon,
            "projected_traditional_balance_horizon": trad_horizon,
            "heir_tax_profile": heir,
        },
        "recommendation": {
            "primary_action": action,
            "suitability": suit,
            "risk_flag": risk,
        }
    }

# =============================================================================
# ILIT Crummey implementation
# =============================================================================

def compute_ilit_crummey(params):
    excl_per_ben = params["annual_exclusion_per_beneficiary"]
    ben_count = params["beneficiary_count"]
    annual_prem = params["annual_premium"]
    death_ben = params["death_benefit"]
    contrib_date_str = params["planned_contribution_date"]
    is_transfer = params["is_existing_policy_transfer"]
    planning_yr = params["planning_year"]

    capacity = round(excl_per_ben * ben_count, 2)
    gap = round(max(0.0, annual_prem - capacity), 2)

    contrib = date.fromisoformat(contrib_date_str)
    notice_due = contrib + timedelta(days=7)
    withdrawal_end = notice_due + timedelta(days=30)
    earliest_prem = withdrawal_end + timedelta(days=1)

    if is_transfer and gap > 0:
        risk = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
        outside = 0.0
    elif is_transfer:
        risk = "THREE_YEAR_LOOKBACK"
        outside = round(death_ben, 2)
    elif gap > 0:
        risk = "EXCLUSION_SHORTFALL"
        outside = 0.0
    else:
        risk = "LOW_IF_FORMALITIES_MET"
        outside = round(death_ben, 2)

    tax_liq = round(death_ben * 0.4, 2)

    if not is_transfer and gap == 0:
        action = "FUND_WITH_CRUMMEY_NOTICES"
        suit = "SUITABLE_WITH_ADMINISTRATION"
    elif not is_transfer and gap > 0:
        action = "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL"
        suit = "BORDERLINE"
    elif is_transfer and gap == 0:
        action = "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK"
        suit = "SUITABLE_WITH_ADMINISTRATION"
    else:
        action = "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION"
        suit = "NOT_SUITABLE"

    return {
        "gift_plan": {
            "planning_year": planning_yr,
            "annual_exclusion_per_beneficiary": round(float(excl_per_ben), 2),
            "beneficiary_count": ben_count,
            "annual_exclusion_capacity": capacity,
            "annual_premium": round(float(annual_prem), 2),
            "premium_gap": gap,
        },
        "administration": {
            "notices_required": ben_count,
            "contribution_date": contrib_date_str,
            "notice_due_date": notice_due.isoformat(),
            "withdrawal_window_end": withdrawal_end.isoformat(),
            "earliest_premium_payment_date": earliest_prem.isoformat(),
            "dedicated_bank_account_required": gap == 0,
        },
        "estate_result": {
            "death_benefit": round(float(death_ben), 2),
            "estate_inclusion_risk": risk,
            "projected_outside_estate_if_implemented": outside,
            "tax_liquidity_support": tax_liq,
        },
        "recommendation": {
            "primary_action": action,
            "suitability": suit,
            "risk_flag": risk,
        }
    }

# =============================================================================
# Trust comparison (GRAT vs CRAT)
# =============================================================================

def compute_trust_comparison(params):
    A = params["asset_value"]
    g = params["expected_growth_rate"]
    grat_term = params["grat_term_years"]
    grat_ann = params["grat_annuity_rate"]
    crat_term = params["crat_term_years"]
    crat_payout = params["crat_payout_rate"]
    estate_rate = params["estate_tax_rate"]
    char_rate = params["charitable_deduction_rate"]
    estate_val = params["estate_value"]
    exemption = params["estate_tax_exemption"]
    liquid = params["liquid_assets"]
    phil = params["philanthropic_intent"]
    fam = params["family_transfer_priority"]
    planning_yr = params["planning_year"]

   grat_remainder = round(A * (1 + g) ** grat_term - A * grat_ann * grat_term, 2)
   grat_estate_reduction = round(grat_remainder * estate_rate, 2)

   crat_remainder = round(A * (1 + g) ** crat_term - A * crat_payout * crat_term, 2)
   crat_income_deduction = round(crat_remainder * char_rate, 2)

    # MFJ gets 2x exemption; SINGLE/HOH get 1x
    filing = params.get("filing_status", "SINGLE")
    exemption_total = exemption * 2 if filing == "MFJ" else exemption
    taxable_estate = round(estate_val - exemption_total, 2)
    estate_tax_exposure = round(taxable_estate * estate_rate, 2)
    liquidity_gap = round(max(0.0, estate_tax_exposure - liquid), 2)

    if fam == "high" and phil in ("low", "moderate"):
        preferred = "GRAT"
        rationale = "CHILDREN_TRANSFER_PRIORITY"
        alternate = "SECONDARY_CHARITABLE_TOOL"
    else:
        preferred = "CRAT"
        rationale = "PHILANTHROPIC_PRIORITY"
        alternate = "SECONDARY_FAMILY_TRANSFER_TOOL"

    return {
        "estate_context": {
            "planning_year": planning_yr,
            "exemption_used": exemption,
            "taxable_estate": taxable_estate,
            "estate_tax_exposure": estate_tax_exposure,
            "liquid_assets_available": round(float(liquid), 2),
            "liquidity_gap_before_planning": liquidity_gap,
        },
        "grat": {
            "term_years": grat_term,
            "projected_remainder_to_heirs": grat_remainder,
            "estimated_estate_tax_reduction": grat_estate_reduction,
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
        },
        "crat": {
            "term_years": crat_term,
            "projected_charitable_remainder": crat_remainder,
            "estimated_income_tax_deduction": crat_income_deduction,
            "family_transfer_fit": "LOW",
        },
        "recommendation": {
            "preferred_strategy": preferred,
            "rationale_code": rationale,
            "alternate_role": alternate,
        }
    }

# =============================================================================
# Estate liquidity action plan
# =============================================================================

def compute_estate_liquidity(params):
    ilit = compute_ilit_crummey({
        "annual_exclusion_per_beneficiary": params["annual_exclusion_per_beneficiary"],
        "beneficiary_count": params["beneficiary_count"],
        "annual_premium": params["annual_premium"],
        "death_benefit": params["death_benefit"],
        "planned_contribution_date": params["planned_contribution_date"],
        "is_existing_policy_transfer": params["is_existing_policy_transfer"],
        "planning_year": params["planning_year"],
    })

    trust = compute_trust_comparison({
        "asset_value": params["asset_value"],
        "expected_growth_rate": params["expected_growth_rate"],
        "grat_term_years": params["grat_term_years"],
        "grat_annuity_rate": params["grat_annuity_rate"],
        "crat_term_years": params["crat_term_years"],
        "crat_payout_rate": params["crat_payout_rate"],
        "estate_tax_rate": params["estate_tax_rate"],
        "charitable_deduction_rate": params["charitable_deduction_rate"],
        "estate_value": params["estate_value"],
        "estate_tax_exemption": params["estate_tax_exemption"],
        "liquid_assets": params["liquid_assets"],
        "philanthropic_intent": params["philanthropic_intent"],
        "family_transfer_priority": params["family_transfer_priority"],
        "planning_year": params["planning_year"],
    })

    estate_val = params["estate_value"]
    exemption = params["estate_tax_exemption"]
    liquid = params["liquid_assets"]
    taxable_estate = round(estate_val - exemption, 2)
    estate_tax_exposure = round(taxable_estate * 0.4, 2)
    liquidity_gap = round(max(0.0, estate_tax_exposure - liquid), 2)

    actions = ["ATTORNEY_DRAFT_REVIEW"]
    if params["philanthropic_intent"] == "high":
        actions.append("CRAT_FOR_CHARITABLE_REMAINDER")
    if params["family_transfer_priority"] == "high" and trust["grat"]["projected_remainder_to_heirs"] > 0:
        actions.append("GRAT_FOR_APPRECIATING_SHARES")
    if ilit["gift_plan"]["premium_gap"] == 0:
        actions.append("ILIT_CRUMMEY_NOTICE_CYCLE")
    if liquidity_gap > 0:
        actions.append("LIFETIME_EXEMPTION_ALLOCATION")
    actions.sort()

    ilit_feasible = ilit["gift_plan"]["premium_gap"] == 0
    grat_feasible = trust["grat"]["projected_remainder_to_heirs"] > 0
    is_transfer = params.get("is_existing_policy_transfer", False)

    if ilit_feasible and grat_feasible and params["family_transfer_priority"] == "high":
        primary = "COMBINE_ILIT_AND_GRAT"
        seq = "ILIT_FIRST_THEN_ATTORNEY_REVIEW" if is_transfer else "ILIT_FIRST_THEN_GRAT"
    elif params["philanthropic_intent"] == "high":
        primary = "CRAT_WITH_LIQUIDITY_REVIEW"
        seq = "TRUST_DECISION_FIRST"
    else:
        primary = "ILIT_WITH_EXEMPTION_REVIEW"
        seq = "ILIT_FIRST_THEN_ATTORNEY_REVIEW" if is_transfer else "ILIT_FIRST_THEN_GRAT"

    return {
        "estate_context": {
            "planning_year": params["planning_year"],
            "exemption_used": exemption,
            "taxable_estate": taxable_estate,
            "estate_tax_exposure": estate_tax_exposure,
            "liquid_assets_available": round(float(liquid), 2),
            "liquidity_gap_before_planning": liquidity_gap,
        },
        "ilit": {
            "annual_exclusion_capacity": ilit["gift_plan"]["annual_exclusion_capacity"],
            "premium_gap": ilit["gift_plan"]["premium_gap"],
            "estate_inclusion_risk": ilit["estate_result"]["estate_inclusion_risk"],
            "projected_outside_estate_if_implemented": ilit["estate_result"]["projected_outside_estate_if_implemented"],
        },
        "trust_transfer": {
            "preferred_strategy": trust["recommendation"]["preferred_strategy"],
            "projected_remainder_to_heirs": trust["grat"]["projected_remainder_to_heirs"],
            "estimated_estate_tax_reduction": trust["grat"]["estimated_estate_tax_reduction"],
            "projected_charitable_remainder": trust["crat"]["projected_charitable_remainder"],
        },
        "action_set": actions,
        "recommendation": {
            "primary_action": primary,
            "sequencing": seq,
            "risk_flag": ilit["estate_result"]["estate_inclusion_risk"],
        }
    }
