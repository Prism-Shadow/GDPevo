"""
advisory_lib.py — reusable helpers for the Private Wealth Advisory benchmark.

All client data, tax-policy constants, and RMD factors come from the read-only
advisory API (NOT from model memory). Pass the base URL in (default below) or
set the API_BASE environment variable; the harness usually exposes it that way.

These functions reproduce the exact gold conventions reverse-engineered from the
worked train examples. See SKILL.md for the narrative explanation of every rule.

Usage (interactive):
    import advisory_lib as A
    A.fetch.cache_clear()                       # if you change BASE at runtime
    print(A.solve_roth("CLT-1001", horizon_year=2046))
    print(A.solve_ilit("CLT-1002"))
    print(A.solve_trust("CLT-1003"))
    print(A.solve_estate_plan("CLT-1004"))
"""
import json
import os
import urllib.request
from datetime import date, timedelta
from functools import lru_cache

BASE = os.environ.get("API_BASE", "http://127.0.0.1:8066").rstrip("/")

# ----- source-of-truth precedence per fact domain (see SKILL.md "Source resolution") -----
PROFILE_ORDER = ["SIGNED_PROFILE", "ATTORNEY_MEMO", "CRM_NOTE"]      # profile / goal / beneficiary
ASSET_ORDER   = ["ATTORNEY_MEMO", "SIGNED_PROFILE", "CRM_NOTE"]      # estate/asset valuation for trusts


@lru_cache(maxsize=None)
def fetch(path):
    with urllib.request.urlopen(BASE + path) as r:
        return json.load(r)


def round2(x):
    # USD to cents; +1e-9 nudge avoids 0.005 banker's-rounding surprises
    return round(float(x) + 1e-9, 2)


def tax_policy():
    return fetch("/api/policies/tax")


def rmd_factors():
    return {int(k): v for k, v in fetch("/api/rmd-factors").items()}


def client_header(cid):
    return fetch(f"/api/clients/{cid}")


def docs_map(cid):
    """source_type -> facts dict (one doc per source_type in this dataset)."""
    out = {}
    for d in fetch(f"/api/source-documents?client_id={cid}"):
        out[d["source_type"]] = d["facts"]
    return out


def pick(dm, key, order):
    """Return the value of `key` from the first source in `order` that has it."""
    for s in order:
        if s in dm and key in dm[s] and dm[s][key] is not None:
            return dm[s][key]
    return None


def first_or_none(items):
    return items[0] if items else None


# ---------------------------------------------------------------------------
# Estate-tax context (shared by trust + estate-liquidity families)
# ---------------------------------------------------------------------------
def estate_context(cid, asset_order=ASSET_ORDER):
    hdr = client_header(cid)
    dm = docs_map(cid)
    pol = tax_policy()
    planning_year = pick(dm, "planning_year", PROFILE_ORDER) or hdr["planning_year"]
    marital = pick(dm, "marital_status", PROFILE_ORDER) or hdr["marital_status"]
    # estate/asset valuation uses the asset source of truth (attorney memo for trusts)
    estate_value = pick(dm, "estate_value", asset_order) or hdr["estate_value"]
    liquid = pick(dm, "liquid_assets", PROFILE_ORDER) or hdr["liquid_assets"]
    exemption_unit = pol["estate_tax_exemption"][str(planning_year)]
    married = str(marital).lower() == "married"
    exemption_used = exemption_unit * (2 if married else 1)
    taxable_estate = max(0.0, estate_value - exemption_used)
    exposure = taxable_estate * pol["estate_tax_rate"]
    liquidity_gap = max(0.0, exposure - liquid)
    return dict(
        planning_year=planning_year,
        married=married,
        estate_value=estate_value,
        exemption_used=round2(exemption_used),
        taxable_estate=round2(taxable_estate),
        estate_tax_exposure=round2(exposure),
        liquid_assets_available=round2(liquid),
        liquidity_gap_before_planning=round2(liquidity_gap),
    )


# ---------------------------------------------------------------------------
# 1) Roth conversion + RMD
# ---------------------------------------------------------------------------
def solve_roth(cid, horizon_year):
    hdr = client_header(cid)
    dm = docs_map(cid)
    pol = tax_policy()
    rmd = rmd_factors()
    acct = first_or_none(fetch(f"/api/retirement-accounts?client_id={cid}"))

    age = pick(dm, "age", PROFILE_ORDER) or hdr["age"]
    planning_year = pick(dm, "planning_year", PROFILE_ORDER) or hdr["planning_year"]
    filing = pick(dm, "filing_status", PROFILE_ORDER) or hdr["filing_status"]
    income = pick(dm, "annual_non_ira_income", PROFILE_ORDER)
    marg = pick(dm, "marginal_tax_rate", PROFILE_ORDER)

    trad0 = acct["traditional_balance"]
    roth0 = acct["roth_balance"]
    ret = acct["expected_return"]
    rmd_age = acct["rmd_start_age"]
    conv_years = acct["recommended_conversion_years"]

    target = pol["conversion_bracket_targets"][filing]
    annual_conv = target - income
    first_conv_year = planning_year
    total_converted = annual_conv * conv_years
    total_conv_tax = total_converted * marg
    first_rmd_year = (planning_year - age) + rmd_age

    def simulate(do_conversion):
        trad, roth_bal, rmd_tax = trad0, roth0, 0.0
        for year in range(planning_year, horizon_year + 1):
            a = age + (year - planning_year)
            # 1. conversion (first conv_years years), capped at remaining traditional
            if do_conversion and first_conv_year <= year < first_conv_year + conv_years:
                c = min(annual_conv, trad)
                trad -= c
                roth_bal += c
            # 2. RMD once the owner reaches rmd_start_age
            if a >= rmd_age and a in rmd:
                r = trad / rmd[a]
                trad -= r
                rmd_tax += r * marg
            # 3. growth applied at end of year to both buckets
            trad *= (1 + ret)
            roth_bal *= (1 + ret)
        return rmd_tax, trad, roth_bal

    base_tax, _, _ = simulate(False)
    conv_tax, conv_trad, conv_roth = simulate(True)
    savings = base_tax - conv_tax

    # ---- enum logic ----
    if annual_conv <= 0:
        primary, suit = "NO_CONVERSION", "DEFER"
    elif savings > 0:
        primary, suit = "STAGED_ROTH_CONVERSION", "SUITABLE"
    else:
        primary, suit = "DEFER", "BORDERLINE"
    # near-term RMD risk if owner already at/over RMD age this planning year
    risk = "RMD_NEAR_TERM" if age >= rmd_age else "TAX_BRACKET_MANAGEMENT"
    # heir profile from relative size of tax-free vs taxable buckets at horizon
    if conv_roth >= 2 * conv_trad:
        heir = "MOSTLY_TAX_FREE"
    elif conv_trad >= 2 * conv_roth:
        heir = "MOSTLY_TAXABLE"
    else:
        heir = "MIXED_TAXABLE_AND_TAX_FREE"

    return {
        "client_id": cid,
        "analysis_type": "roth_conversion_rmd",
        "recommendation": {"primary_action": primary, "suitability": suit, "risk_flag": risk},
        "conversion_plan": {
            "first_conversion_year": first_conv_year,
            "conversion_years": conv_years,
            "conversion_years_positive": conv_years if annual_conv > 0 else 0,
            "annual_conversion_amount": round2(annual_conv),
            "total_converted": round2(total_converted),
            "total_conversion_tax": round2(total_conv_tax),
        },
        "rmd_projection": {
            "horizon_year": horizon_year,
            "first_rmd_year": first_rmd_year,
            "baseline_rmd_tax_through_horizon": round2(base_tax),
            "conversion_rmd_tax_through_horizon": round2(conv_tax),
            "rmd_tax_savings_through_horizon": round2(savings),
        },
        "legacy_projection": {
            "projected_roth_balance_horizon": round2(conv_roth),
            "projected_traditional_balance_horizon": round2(conv_trad),
            "heir_tax_profile": heir,
        },
        "source_resolution": {
            "controlling_profile_source": "SIGNED_PROFILE",
            "controlling_account_source": "CUSTODIAN_EXPORT",
        },
    }


# ---------------------------------------------------------------------------
# 2) ILIT / Crummey
# ---------------------------------------------------------------------------
def ilit_core(cid):
    """Shared ILIT figures used by both the ILIT family and the estate-plan family."""
    dm = docs_map(cid)
    pol = tax_policy()
    ec = estate_context(cid)
    policy = first_or_none(fetch(f"/api/life-insurance?client_id={cid}"))
    planning_year = ec["planning_year"]
    beneficiary_count = pick(dm, "beneficiary_count", PROFILE_ORDER)
    excl = pol["annual_gift_exclusion"][str(planning_year)]
    capacity = excl * beneficiary_count
    premium = policy["annual_premium"]
    premium_gap = max(0.0, premium - capacity)
    existing = bool(policy["is_existing_policy_transfer"])
    short = premium_gap > 0
    if existing and short:
        risk = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
    elif existing:
        risk = "THREE_YEAR_LOOKBACK"
    elif short:
        risk = "EXCLUSION_SHORTFALL"
    else:
        risk = "LOW_IF_FORMALITIES_MET"
    death_benefit = policy["death_benefit"]
    # During the 3-year lookback an existing-policy transfer is pulled back into the
    # estate, so nothing is reliably outside the estate in the first cycle.
    outside = 0.0 if existing else death_benefit
    return dict(
        planning_year=planning_year,
        beneficiary_count=beneficiary_count,
        annual_exclusion_per_beneficiary=excl,
        annual_exclusion_capacity=capacity,
        annual_premium=premium,
        premium_gap=premium_gap,
        existing=existing,
        risk=risk,
        death_benefit=death_benefit,
        outside_estate=outside,
        policy=policy,
        estate_tax_rate=pol["estate_tax_rate"],
    )


def solve_ilit(cid):
    c = ilit_core(cid)
    contribution = date.fromisoformat(c["policy"]["planned_contribution_date"])
    notice_due = contribution + timedelta(days=7)
    withdrawal_end = notice_due + timedelta(days=30)
    earliest_premium = withdrawal_end + timedelta(days=1)

    if c["risk"] == "LOW_IF_FORMALITIES_MET":
        primary, suit = "FUND_WITH_CRUMMEY_NOTICES", "SUITABLE_WITH_ADMINISTRATION"
    elif c["risk"] == "EXCLUSION_SHORTFALL":
        primary, suit = "USE_LIFETIME_EXEMPTION_FOR_SHORTFALL", "BORDERLINE"
    elif c["risk"] == "THREE_YEAR_LOOKBACK":
        primary, suit = "USE_NEW_POLICY_OR_ACCEPT_LOOKBACK", "BORDERLINE"
    else:  # both problems
        primary, suit = "DISCLOSE_LOOKBACK_AND_USE_EXEMPTION", "NOT_SUITABLE"

    return {
        "client_id": cid,
        "analysis_type": "ilit_crummey_implementation",
        "recommendation": {"primary_action": primary, "suitability": suit, "risk_flag": c["risk"]},
        "gift_plan": {
            "planning_year": c["planning_year"],
            "annual_exclusion_per_beneficiary": round2(c["annual_exclusion_per_beneficiary"]),
            "beneficiary_count": c["beneficiary_count"],
            "annual_exclusion_capacity": round2(c["annual_exclusion_capacity"]),
            "annual_premium": round2(c["annual_premium"]),
            "premium_gap": round2(c["premium_gap"]),
        },
        "administration": {
            "notices_required": c["beneficiary_count"],
            "contribution_date": contribution.isoformat(),
            "notice_due_date": notice_due.isoformat(),
            "withdrawal_window_end": withdrawal_end.isoformat(),
            "earliest_premium_payment_date": earliest_premium.isoformat(),
            "dedicated_bank_account_required": True,
        },
        "estate_result": {
            "death_benefit": round2(c["death_benefit"]),
            "estate_inclusion_risk": c["risk"],
            "projected_outside_estate_if_implemented": round2(c["outside_estate"]),
            "tax_liquidity_support": round2(c["death_benefit"] * c["estate_tax_rate"]),
        },
        "source_resolution": {
            "controlling_beneficiary_source": "SIGNED_PROFILE",
            "controlling_policy_source": "SIGNED_PROFILE",
        },
    }


# ---------------------------------------------------------------------------
# 3) GRAT vs CRAT
# ---------------------------------------------------------------------------
def grat_remainder(asset, growth, term, annuity_rate):
    # FV of asset, minus the simple (un-reinvested) sum of fixed annual annuities
    return asset * (1 + growth) ** term - asset * annuity_rate * term


def crat_remainder(asset, growth, term, payout_rate):
    return asset * (1 + growth) ** term - asset * payout_rate * term


def trust_numbers(cid):
    tc = first_or_none(fetch(f"/api/trust-candidates?client_id={cid}"))
    pol = tax_policy()
    asset = tc["asset_value"]
    growth = tc["expected_growth_rate"]
    gterm = tc["grat_term_years"]
    cterm = min(tc["crat_term_years"], pol["max_crat_term_years"])
    g_rem = grat_remainder(asset, growth, gterm, tc["grat_annuity_rate"])
    c_rem = crat_remainder(asset, growth, cterm, tc["crat_payout_rate"])
    return dict(
        asset=asset, gterm=gterm, cterm=cterm,
        grat_remainder=g_rem,
        grat_tax_reduction=g_rem * pol["estate_tax_rate"],
        crat_remainder=c_rem,
        crat_deduction=c_rem * pol["charitable_deduction_rate"],
    )


def goal_priority(cid):
    """Return (family_transfer_priority, philanthropic_intent) from SIGNED-first goals."""
    dm = docs_map(cid)
    return (
        pick(dm, "family_transfer_priority", PROFILE_ORDER),
        pick(dm, "philanthropic_intent", PROFILE_ORDER),
    )


_RANK = {"low": 0, "moderate": 1, "high": 2}


def prefers_grat(cid):
    ftp, phil = goal_priority(cid)
    return _RANK.get(ftp, 0) >= _RANK.get(phil, 0)


def solve_trust(cid):
    ec = estate_context(cid)
    t = trust_numbers(cid)
    grat_pref = prefers_grat(cid)
    if grat_pref:
        preferred = "GRAT"
        rationale = "CHILDREN_TRANSFER_PRIORITY"
        alternate = "SECONDARY_CHARITABLE_TOOL"
        fit = "LOW"
    else:
        preferred = "CRAT"
        rationale = "PHILANTHROPIC_PRIORITY"
        alternate = "SECONDARY_FAMILY_TRANSFER_TOOL"
        fit = "MODERATE"
    return {
        "client_id": cid,
        "analysis_type": "trust_comparison",
        "recommendation": {
            "preferred_strategy": preferred,
            "rationale_code": rationale,
            "alternate_role": alternate,
        },
        "estate_context": {
            "planning_year": ec["planning_year"],
            "exemption_used": ec["exemption_used"],
            "taxable_estate": ec["taxable_estate"],
            "estate_tax_exposure": ec["estate_tax_exposure"],
            "liquid_assets_available": ec["liquid_assets_available"],
            "liquidity_gap_before_planning": ec["liquidity_gap_before_planning"],
        },
        "grat": {
            "term_years": t["gterm"],
            "projected_remainder_to_heirs": round2(t["grat_remainder"]),
            "estimated_estate_tax_reduction": round2(t["grat_tax_reduction"]),
            "mortality_inclusion_risk": "TERM_SURVIVAL_REQUIRED",
        },
        "crat": {
            "term_years": t["cterm"],
            "projected_charitable_remainder": round2(t["crat_remainder"]),
            "estimated_income_tax_deduction": round2(t["crat_deduction"]),
            "family_transfer_fit": fit,
        },
        "source_resolution": {
            "controlling_goal_source": "SIGNED_PROFILE",
            "controlling_asset_source": "ATTORNEY_MEMO",
        },
    }


# ---------------------------------------------------------------------------
# 4) Integrated estate-liquidity action plan
# ---------------------------------------------------------------------------
def solve_estate_plan(cid):
    ec = estate_context(cid)
    ilit = ilit_core(cid)
    t = trust_numbers(cid)
    grat_pref = prefers_grat(cid)
    preferred = "GRAT" if grat_pref else "CRAT"

    if grat_pref:
        primary = "COMBINE_ILIT_AND_GRAT"
        sequencing = "ILIT_FIRST_THEN_GRAT"
    else:
        primary = "CRAT_WITH_LIQUIDITY_REVIEW"
        sequencing = "TRUST_DECISION_FIRST"

    action_set = ["ATTORNEY_DRAFT_REVIEW", "ILIT_CRUMMEY_NOTICE_CYCLE"]
    if grat_pref:
        action_set.append("GRAT_FOR_APPRECIATING_SHARES")
    else:
        action_set.append("CRAT_FOR_CHARITABLE_REMAINDER")
    if ilit["premium_gap"] > 0:
        action_set.append("LIFETIME_EXEMPTION_ALLOCATION")
    action_set = sorted(action_set)

    return {
        "client_id": cid,
        "analysis_type": "estate_liquidity_action_plan",
        "recommendation": {
            "primary_action": primary,
            "sequencing": sequencing,
            "risk_flag": ilit["risk"],
        },
        "estate_context": {
            "planning_year": ec["planning_year"],
            "exemption_used": ec["exemption_used"],
            "taxable_estate": ec["taxable_estate"],
            "estate_tax_exposure": ec["estate_tax_exposure"],
            "liquid_assets_available": ec["liquid_assets_available"],
            "liquidity_gap_before_planning": ec["liquidity_gap_before_planning"],
        },
        "ilit": {
            "annual_exclusion_capacity": round2(ilit["annual_exclusion_capacity"]),
            "premium_gap": round2(ilit["premium_gap"]),
            "estate_inclusion_risk": ilit["risk"],
            "projected_outside_estate_if_implemented": round2(ilit["outside_estate"]),
        },
        "trust_transfer": {
            "preferred_strategy": preferred,
            "projected_remainder_to_heirs": round2(t["grat_remainder"]),
            "estimated_estate_tax_reduction": round2(t["grat_tax_reduction"]),
            "projected_charitable_remainder": round2(t["crat_remainder"]),
        },
        "action_set": action_set,
        "source_resolution": {
            "controlling_goal_source": "SIGNED_PROFILE",
            "controlling_policy_source": "SIGNED_PROFILE",
        },
    }
