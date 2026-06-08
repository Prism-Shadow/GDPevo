from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path


SOURCE_PRIORITY = {
    "STALE_MARKETING_INTAKE": 0,
    "CRM_NOTE": 1,
    "CUSTODIAN_EXPORT": 2,
    "ATTORNEY_MEMO": 3,
    "SIGNED_PROFILE": 4,
}


def money(value):
    return round(float(value) + 1e-9, 2)


def parse_date(value):
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def load_data(data_dir):
    data_dir = Path(data_dir)
    out = {}
    for name in [
        "clients",
        "source_documents",
        "retirement_accounts",
        "life_insurance",
        "trust_candidates",
        "tax_policy",
        "rmd_factors",
    ]:
        with (data_dir / f"{name}.json").open("r", encoding="utf-8") as f:
            out[name] = json.load(f)
    return out


def get_client(data, client_id):
    return next(c for c in data["clients"] if c["client_id"] == client_id)


def client_documents(data, client_id):
    return [d for d in data["source_documents"] if d["client_id"] == client_id]


def retirement_account(data, client_id):
    matches = [a for a in data["retirement_accounts"] if a["client_id"] == client_id]
    return matches[0] if matches else None


def life_policy(data, client_id):
    matches = [p for p in data["life_insurance"] if p["client_id"] == client_id]
    return matches[0] if matches else None


def trust_candidate(data, client_id):
    matches = [t for t in data["trust_candidates"] if t["client_id"] == client_id]
    return matches[0] if matches else None


def effective_facts(data, client_id):
    facts = dict(get_client(data, client_id))
    docs = sorted(
        client_documents(data, client_id),
        key=lambda d: (SOURCE_PRIORITY.get(d["source_type"], -1), d["effective_date"], d["document_id"]),
    )
    controlling = {}
    for doc in docs:
        for key, value in doc.get("facts", {}).items():
            facts[key] = value
            controlling[key] = doc["source_type"]
    facts["_controlling_sources"] = controlling
    return facts


def estate_exemption(policy, year, marital_status):
    base = policy["estate_tax_exemption"].get(str(year), policy["estate_tax_exemption"]["2026"])
    multiplier = 2 if marital_status == "married" else 1
    return float(base) * multiplier


def estate_context(data, client_id):
    facts = effective_facts(data, client_id)
    policy = data["tax_policy"]
    exemption = estate_exemption(policy, facts["planning_year"], facts["marital_status"])
    taxable_estate = max(0.0, float(facts["estate_value"]) - exemption)
    estate_tax = taxable_estate * float(policy["estate_tax_rate"])
    liquid_assets = float(facts.get("liquid_assets", 0))
    return {
        "planning_year": facts["planning_year"],
        "exemption_used": money(exemption),
        "taxable_estate": money(taxable_estate),
        "estate_tax_exposure": money(estate_tax),
        "liquid_assets_available": money(liquid_assets),
        "liquidity_gap_before_planning": money(max(0.0, estate_tax - liquid_assets)),
    }


def simulate_roth(data, client_id, horizon_year):
    facts = effective_facts(data, client_id)
    acct = retirement_account(data, client_id)
    policy = data["tax_policy"]
    factors = {int(k): float(v) for k, v in data["rmd_factors"].items()}

    year0 = int(facts["planning_year"])
    age0 = int(facts["age"])
    tax_rate = float(facts["marginal_tax_rate"])
    bracket_top = float(policy["conversion_bracket_targets"][facts["filing_status"]])
    bracket_room = max(0.0, bracket_top - float(facts["annual_non_ira_income"]))
    conversion_years = int(acct["recommended_conversion_years"])
    balance0 = float(acct["traditional_balance"])
    annual_conversion = min(bracket_room, balance0 / conversion_years)
    annual_conversion = money(annual_conversion)

    ret = float(acct["expected_return"])
    rmd_start_age = int(acct["rmd_start_age"])

    baseline = balance0
    conv_trad = balance0
    conv_roth = float(acct.get("roth_balance", 0))
    baseline_rmd_tax = 0.0
    conversion_rmd_tax = 0.0
    conversion_tax = 0.0
    total_converted = 0.0
    positive_years = 0
    first_rmd_year = None

    for year in range(year0, int(horizon_year) + 1):
        age = age0 + (year - year0)
        if age >= rmd_start_age and first_rmd_year is None:
            first_rmd_year = year

        if age >= rmd_start_age:
            factor = factors.get(age, factors[max(factors)])
            rmd = baseline / factor
            baseline_rmd_tax += rmd * tax_rate
            baseline = (baseline - rmd) * (1 + ret)
        else:
            baseline = baseline * (1 + ret)

        conversion = 0.0
        if year < year0 + conversion_years and conv_trad > 0:
            conversion = min(annual_conversion, conv_trad)
            total_converted += conversion
            conversion_tax += conversion * tax_rate
            positive_years += 1 if conversion > 0 else 0
            conv_trad -= conversion
            conv_roth += conversion

        if age >= rmd_start_age and conv_trad > 0:
            factor = factors.get(age, factors[max(factors)])
            rmd = conv_trad / factor
            conversion_rmd_tax += rmd * tax_rate
            conv_trad = (conv_trad - rmd) * (1 + ret)
        else:
            conv_trad = conv_trad * (1 + ret)
        conv_roth = conv_roth * (1 + ret)

    return {
        "client_id": client_id,
        "analysis_type": "roth_conversion_rmd",
        "recommendation": {
            "primary_action": "STAGED_ROTH_CONVERSION",
            "suitability": "SUITABLE" if annual_conversion > 0 else "DEFER",
            "risk_flag": "TAX_BRACKET_MANAGEMENT",
        },
        "conversion_plan": {
            "first_conversion_year": year0,
            "conversion_years": conversion_years,
            "conversion_years_positive": positive_years,
            "annual_conversion_amount": money(annual_conversion),
            "total_converted": money(total_converted),
            "total_conversion_tax": money(conversion_tax),
        },
        "rmd_projection": {
            "horizon_year": int(horizon_year),
            "first_rmd_year": first_rmd_year,
            "baseline_rmd_tax_through_horizon": money(baseline_rmd_tax),
            "conversion_rmd_tax_through_horizon": money(conversion_rmd_tax),
            "rmd_tax_savings_through_horizon": money(baseline_rmd_tax - conversion_rmd_tax),
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": money(conv_roth),
            "projected_traditional_balance_horizon": money(conv_trad),
            "heir_tax_profile": "MIXED_TAXABLE_AND_TAX_FREE" if conv_trad > 1 else "MOSTLY_TAX_FREE",
        },
        "source_resolution": {
            "controlling_profile_source": facts["_controlling_sources"].get("annual_non_ira_income", "SIGNED_PROFILE"),
            "controlling_account_source": "CUSTODIAN_EXPORT",
        },
    }


def ilit_plan(data, client_id):
    facts = effective_facts(data, client_id)
    policy = data["tax_policy"]
    life = life_policy(data, client_id)
    year = int(facts["planning_year"])
    exclusion = float(policy["annual_gift_exclusion"][str(year)])
    beneficiaries = int(facts["beneficiary_count"])
    capacity = exclusion * beneficiaries
    premium = float(life["annual_premium"])
    gap = max(0.0, premium - capacity)

    contribution_date = parse_date(life["planned_contribution_date"])
    notice_due = contribution_date + timedelta(days=7)
    withdrawal_end = notice_due + timedelta(days=30)
    earliest_payment = withdrawal_end + timedelta(days=1)

    lookback = bool(life["is_existing_policy_transfer"])
    if lookback and gap > 0:
        risk = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
        action = "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION"
    elif lookback:
        risk = "THREE_YEAR_LOOKBACK"
        action = "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK"
    elif gap > 0:
        risk = "EXCLUSION_SHORTFALL"
        action = "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL"
    else:
        risk = "LOW_IF_FORMALITIES_MET"
        action = "FUND_WITH_CRUMMEY_NOTICES"

    return {
        "client_id": client_id,
        "analysis_type": "ilit_crummey_implementation",
        "recommendation": {
            "primary_action": action,
            "suitability": "SUITABLE_WITH_ADMINISTRATION",
            "risk_flag": risk,
        },
        "gift_plan": {
            "planning_year": year,
            "annual_exclusion_per_beneficiary": money(exclusion),
            "beneficiary_count": beneficiaries,
            "annual_exclusion_capacity": money(capacity),
            "annual_premium": money(premium),
            "premium_gap": money(gap),
        },
        "administration": {
            "notices_required": beneficiaries,
            "contribution_date": contribution_date.isoformat(),
            "notice_due_date": notice_due.isoformat(),
            "withdrawal_window_end": withdrawal_end.isoformat(),
            "earliest_premium_payment_date": earliest_payment.isoformat(),
            "dedicated_bank_account_required": True,
        },
        "estate_result": {
            "death_benefit": money(float(life["death_benefit"])),
            "estate_inclusion_risk": risk,
            "projected_outside_estate_if_implemented": money(float(life["death_benefit"]) if not lookback else 0.0),
            "tax_liquidity_support": money(float(life["death_benefit"]) * float(policy["estate_tax_rate"])),
        },
        "source_resolution": {
            "controlling_beneficiary_source": facts["_controlling_sources"].get("beneficiary_count", "SIGNED_PROFILE"),
            "controlling_policy_source": "ATTORNEY_MEMO" if lookback else "SIGNED_PROFILE",
        },
    }


def trust_comparison(data, client_id):
    facts = effective_facts(data, client_id)
    policy = data["tax_policy"]
    trust = trust_candidate(data, client_id)
    estate = estate_context(data, client_id)
    asset = float(trust["asset_value"])
    growth = float(trust["expected_growth_rate"])
    grat_term = int(trust["grat_term_years"])
    annuity_rate = float(trust["grat_annuity_rate"])
    grat_projected = asset * ((1 + growth) ** grat_term)
    grat_annuity_back = asset * annuity_rate * grat_term
    grat_remainder = max(0.0, grat_projected - grat_annuity_back)
    grat_tax_reduction = grat_remainder * float(policy["estate_tax_rate"])

    crat_term = min(int(trust["crat_term_years"]), int(policy["max_crat_term_years"]))
    crat_projected = asset * ((1 + growth) ** crat_term)
    crat_payouts = asset * float(trust["crat_payout_rate"]) * crat_term
    crat_remainder = max(0.0, crat_projected - crat_payouts)
    deduction = crat_remainder * float(policy["charitable_deduction_rate"])

    if facts["philanthropic_intent"] == "high" and facts["family_transfer_priority"] != "high":
        preferred = "CRAT"
        code = "PHILANTHROPIC_PRIORITY"
        alternate_role = "SECONDARY_FAMILY_TRANSFER_TOOL"
    else:
        preferred = "GRAT"
        code = "CHILDREN_TRANSFER_PRIORITY"
        alternate_role = "SECONDARY_CHARITABLE_TOOL"

    return {
        "client_id": client_id,
        "analysis_type": "trust_comparison",
        "recommendation": {
            "preferred_strategy": preferred,
            "rationale_code": code,
            "alternate_role": alternate_role,
        },
        "estate_context": estate,
        "grat": {
            "term_years": grat_term,
            "projected_remainder_to_heirs": money(grat_remainder),
            "estimated_estate_tax_reduction": money(grat_tax_reduction),
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
        },
        "crat": {
            "term_years": crat_term,
            "projected_charitable_remainder": money(crat_remainder),
            "estimated_income_tax_deduction": money(deduction),
            "family_transfer_fit": "LOW" if preferred == "GRAT" else "MODERATE",
        },
        "source_resolution": {
            "controlling_goal_source": facts["_controlling_sources"].get("philanthropic_intent", "SIGNED_PROFILE"),
            "controlling_asset_source": "ATTORNEY_MEMO",
        },
    }


def integrated_plan(data, client_id):
    estate = estate_context(data, client_id)
    ilit = ilit_plan(data, client_id)
    trust = trust_comparison(data, client_id)
    facts = effective_facts(data, client_id)
    if (
        ilit["recommendation"]["risk_flag"] == "LOW_IF_FORMALITIES_MET"
        and trust["recommendation"]["preferred_strategy"] == "GRAT"
    ):
        primary = "COMBINE_ILIT_AND_GRAT"
        sequencing = "ILIT_FIRST_THEN_GRAT"
    elif trust["recommendation"]["preferred_strategy"] == "CRAT":
        primary = "CRAT_WITH_LIQUIDITY_REVIEW"
        sequencing = "TRUST_DECISION_FIRST"
    else:
        primary = "ILIT_WITH_EXEMPTION_REVIEW"
        sequencing = "ILIT_FIRST_THEN_ATTORNEY_REVIEW"
    action_set = ["ATTORNEY_DRAFT_REVIEW", "ILIT_CRUMMEY_NOTICE_CYCLE"]
    if trust["recommendation"]["preferred_strategy"] == "GRAT":
        action_set.append("GRAT_FOR_APPRECIATING_SHARES")
    else:
        action_set.append("CRAT_FOR_CHARITABLE_REMAINDER")
    if ilit["gift_plan"]["premium_gap"] > 0:
        action_set.append("LIFETIME_EXEMPTION_ALLOCATION")
    return {
        "client_id": client_id,
        "analysis_type": "estate_liquidity_action_plan",
        "recommendation": {
            "primary_action": primary,
            "sequencing": sequencing,
            "risk_flag": ilit["recommendation"]["risk_flag"],
        },
        "estate_context": estate,
        "ilit": {
            "annual_exclusion_capacity": ilit["gift_plan"]["annual_exclusion_capacity"],
            "premium_gap": ilit["gift_plan"]["premium_gap"],
            "estate_inclusion_risk": ilit["estate_result"]["estate_inclusion_risk"],
            "projected_outside_estate_if_implemented": ilit["estate_result"][
                "projected_outside_estate_if_implemented"
            ],
        },
        "trust_transfer": {
            "preferred_strategy": trust["recommendation"]["preferred_strategy"],
            "projected_remainder_to_heirs": trust["grat"]["projected_remainder_to_heirs"],
            "estimated_estate_tax_reduction": trust["grat"]["estimated_estate_tax_reduction"],
            "projected_charitable_remainder": trust["crat"]["projected_charitable_remainder"],
        },
        "action_set": sorted(action_set),
        "source_resolution": {
            "controlling_goal_source": facts["_controlling_sources"].get("family_transfer_priority", "SIGNED_PROFILE"),
            "controlling_policy_source": ilit["source_resolution"]["controlling_policy_source"],
        },
    }
