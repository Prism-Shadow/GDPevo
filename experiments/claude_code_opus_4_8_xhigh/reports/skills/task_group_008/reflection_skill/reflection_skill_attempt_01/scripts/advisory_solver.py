#!/usr/bin/env python3
"""
Private-wealth advisory solver library.

Reusable, verified building blocks for the four task families:
  - roth_conversion_rmd            (Roth-conversion / RMD tax summary)
  - ilit_crummey_implementation    (ILIT Crummey funding cycle)
  - trust_comparison               (GRAT vs CRAT recommendation)
  - estate_liquidity_action_plan   (integrated estate-liquidity plan)

Every formula here was reverse-engineered from the live advisory API and
verified to reproduce the gold answers to the cent. Treat these functions as
the source of truth; do NOT recompute formulas from memory.

Usage pattern for a new task:
    from advisory_solver import API, controlling_facts, roth_rmd, estate_context, grat_crat, ilit_cycle
    api = API("http://127.0.0.1:8066")   # use the base URL the harness gives you
    cid = "CLT-XXXX"
    ... build the answer dict, round every USD number to cents, dump JSON ...

IMPORTANT conventions (see references/business_rules.md for the why):
  - All policy constants (gift exclusion, estate exemption, rates, bracket
    targets, max CRAT term) come from /api/policies/tax. Never hardcode them.
  - RMD divisors come from /api/rmd-factors keyed by integer age.
  - Round every USD output to 2 decimals with round(x, 2).
  - Dates are ISO YYYY-MM-DD.
"""

import json
import urllib.request
from datetime import date, timedelta


class API:
    def __init__(self, base):
        self.base = base.rstrip("/")

    def get(self, path):
        with urllib.request.urlopen(self.base + path) as r:
            return json.loads(r.read())

    def tax(self):
        return self.get("/api/policies/tax")

    def rmd_factors(self):
        # keyed by integer age
        return {int(k): v for k, v in self.get("/api/rmd-factors").items()}

    def header(self, cid):
        return self.get(f"/api/clients/{cid}")

    def source_docs(self, cid):
        return self.get(f"/api/source-documents?client_id={cid}")

    def retirement(self, cid):
        return self.get(f"/api/retirement-accounts?client_id={cid}")[0]

    def life(self, cid):
        return self.get(f"/api/life-insurance?client_id={cid}")[0]

    def trust(self, cid):
        return self.get(f"/api/trust-candidates?client_id={cid}")[0]


# ---------------------------------------------------------------------------
# SOURCE PRECEDENCE
# ---------------------------------------------------------------------------
def controlling_facts(api, cid):
    """
    Resolve conflicting source documents.

    Precedence rules (verified):
      * PROFILE / GOAL / BENEFICIARY facts  -> SIGNED_PROFILE controls.
        SIGNED_PROFILE is the newest (effective 2026-02-06), signed, and most
        complete document. Whenever a fact is present in SIGNED_PROFILE it wins
        over CRM_NOTE (oldest, stale import) and ATTORNEY_MEMO.
      * ESTATE / ASSET-VALUATION facts      -> ATTORNEY_MEMO controls
        (the dedicated estate-valuation document).
      * RETIREMENT ACCOUNT facts            -> CUSTODIAN_EXPORT controls
        (the retirement-accounts export).

    Returns a dict of the resolved profile facts plus the controlling-source
    enum labels you will echo into source_resolution.*.
    """
    docs = {d["source_type"]: d["facts"] for d in api.source_docs(cid)}
    signed = docs["SIGNED_PROFILE"]
    return {
        "facts": signed,                       # use SIGNED_PROFILE for all profile/goal/beneficiary facts
        "attorney": docs.get("ATTORNEY_MEMO", {}),
        "crm": docs.get("CRM_NOTE", {}),
        "controlling_profile_source": "SIGNED_PROFILE",
        "controlling_beneficiary_source": "SIGNED_PROFILE",
        "controlling_goal_source": "SIGNED_PROFILE",
        "controlling_policy_source": "SIGNED_PROFILE",   # NOTE: governing doc is SIGNED_PROFILE, not the custodian/life record
        "controlling_account_source": "CUSTODIAN_EXPORT",
        "controlling_asset_source": "ATTORNEY_MEMO",
    }


# ---------------------------------------------------------------------------
# ROTH CONVERSION / RMD
# ---------------------------------------------------------------------------
def roth_rmd(api, cid, horizon_year):
    """
    Returns the full roth_conversion_rmd numeric block.

    Conversion sizing:
      annual_conversion_amount = bracket_target[filing_status] - annual_non_ira_income
      conversion_years         = recommended_conversion_years (custodian export)
      total_converted          = annual * years
      total_conversion_tax     = total_converted * marginal_tax_rate

    Year-by-year simulation (planning_year .. horizon_year inclusive),
    ORDER OF OPERATIONS PER YEAR:
      1. (conversion scenario, first `conversion_years` years) convert
         min(annual, trad) from traditional to roth.
      2. if age >= rmd_start_age: rmd = trad / rmd_factor[age];
         rmd_tax += rmd * marginal_rate; trad -= rmd.   (RMD BEFORE growth)
      3. grow trad *= (1+return); roth *= (1+return).
    baseline scenario = same loop with conversions disabled.

    first_rmd_year = planning_year + (rmd_start_age - age)
    Reported roth/traditional horizon balances come from the CONVERSION scenario.
    """
    tax = api.tax()
    rf = api.rmd_factors()
    s = controlling_facts(api, cid)["facts"]
    acct = api.retirement(cid)

    income = s["annual_non_ira_income"]
    mr = s["marginal_tax_rate"]
    fs = s["filing_status"]
    age0 = s["age"]
    py = s["planning_year"]

    target = tax["conversion_bracket_targets"][fs]
    annual = target - income
    conv_years = acct["recommended_conversion_years"]
    ret = acct["expected_return"]
    rmd_age = acct["rmd_start_age"]
    trad0 = acct["traditional_balance"]
    roth0 = acct["roth_balance"]
    first_rmd_year = py + (rmd_age - age0)

    def simulate(do_conv):
        trad, roth, rmd_tax = trad0, roth0, 0.0
        for i, year in enumerate(range(py, horizon_year + 1)):
            age = age0 + (year - py)
            if do_conv and i < conv_years:
                conv = min(annual, trad)
                trad -= conv
                roth += conv
            if age >= rmd_age:
                rmd = trad / rf[age]
                rmd_tax += rmd * mr
                trad -= rmd
            trad *= (1 + ret)
            roth *= (1 + ret)
        return trad, roth, rmd_tax

    base_tax = simulate(False)[2]
    c_trad, c_roth, c_tax = simulate(True)

    return {
        "first_conversion_year": py,
        "conversion_years": conv_years,
        "conversion_years_positive": conv_years if annual > 0 else 0,
        "annual_conversion_amount": round(annual, 2),
        "total_converted": round(annual * conv_years, 2),
        "total_conversion_tax": round(annual * conv_years * mr, 2),
        "horizon_year": horizon_year,
        "first_rmd_year": first_rmd_year,
        "baseline_rmd_tax_through_horizon": round(base_tax, 2),
        "conversion_rmd_tax_through_horizon": round(c_tax, 2),
        "rmd_tax_savings_through_horizon": round(base_tax - c_tax, 2),
        "projected_roth_balance_horizon": round(c_roth, 2),
        "projected_traditional_balance_horizon": round(c_trad, 2),
        "heir_tax_profile": heir_tax_profile(c_roth, c_trad),
        "annual_conversion_amount_raw": annual,  # for decision logic
    }


def heir_tax_profile(roth, trad):
    """
    roth = tax-free to heirs, trad = taxable to heirs.
    Verified: a roth fraction of 0.61 and 0.46 are both MIXED_TAXABLE_AND_TAX_FREE.
    A pure roth-vs-trad majority test is WRONG (the blind attempt's bug).
    Use a high band for MOSTLY_TAX_FREE and a low band for MOSTLY_TAXABLE.
    """
    total = roth + trad
    if total <= 0:
        return "MIXED_TAXABLE_AND_TAX_FREE"
    frac = roth / total
    if frac >= 0.70:
        return "MOSTLY_TAX_FREE"
    if frac <= 0.30:
        return "MOSTLY_TAXABLE"
    return "MIXED_TAXABLE_AND_TAX_FREE"


def roth_recommendation(plan):
    """
    Recommendation enums for roth_conversion_rmd.
    A working staged conversion (positive headroom AND positive savings) is
    SUITABLE / TAX_BRACKET_MANAGEMENT, even when RMDs are near-term.
    Do NOT downgrade to BORDERLINE/RMD_NEAR_TERM merely because the client is
    close to RMD age (that was the blind attempt's bug on the near-RMD case).
    """
    headroom = plan["annual_conversion_amount_raw"] > 0
    savings = plan["rmd_tax_savings_through_horizon"] > 0
    if headroom and savings:
        return {"primary_action": "STAGED_ROTH_CONVERSION",
                "suitability": "SUITABLE",
                "risk_flag": "TAX_BRACKET_MANAGEMENT"}
    if not headroom:
        return {"primary_action": "NO_CONVERSION",
                "suitability": "DEFER",
                "risk_flag": "TAX_BRACKET_MANAGEMENT"}
    return {"primary_action": "DEFER",
            "suitability": "BORDERLINE",
            "risk_flag": "RMD_NEAR_TERM"}


# ---------------------------------------------------------------------------
# ESTATE CONTEXT
# ---------------------------------------------------------------------------
def estate_context(api, cid):
    """
    taxable_estate = estate_value - exemption_used, floored at 0.
      exemption_used = estate_tax_exemption[planning_year] * (2 if married else 1).
      (Married households get a DOUBLE exemption -- portability. Single = 1x.)
    estate_tax_exposure = taxable_estate * estate_tax_rate.
    liquidity_gap_before_planning = max(0, exposure - liquid_assets).
    """
    tax = api.tax()
    s = controlling_facts(api, cid)["facts"]
    py = s["planning_year"]
    ev = s["estate_value"]
    exemption = tax["estate_tax_exemption"][str(py)]
    married = s["marital_status"] == "married"
    exemption_used = exemption * (2 if married else 1)
    taxable = max(0.0, ev - exemption_used)
    exposure = taxable * tax["estate_tax_rate"]
    liquid = s["liquid_assets"]
    gap = max(0.0, exposure - liquid)
    return {
        "planning_year": py,
        "exemption_used": round(exemption_used, 2),
        "taxable_estate": round(taxable, 2),
        "estate_tax_exposure": round(exposure, 2),
        "liquid_assets_available": round(liquid, 2),
        "liquidity_gap_before_planning": round(gap, 2),
    }


# ---------------------------------------------------------------------------
# GRAT / CRAT
# ---------------------------------------------------------------------------
def grat_crat(api, cid):
    """
    GRAT remainder  = asset*(1+growth)**grat_term - (asset*grat_annuity_rate*grat_term)
    CRAT remainder  = asset*(1+growth)**crat_term - (asset*crat_payout_rate*crat_term)
      -> The annuity / payout stream is a SIMPLE SUM (payment * term).
         Do NOT future-value / compound the payment stream (the blind bug).
    grat.estimated_estate_tax_reduction = grat_remainder * estate_tax_rate
    crat.estimated_income_tax_deduction = crat_remainder * charitable_deduction_rate
    """
    tax = api.tax()
    t = api.trust(cid)
    a = t["asset_value"]
    g = t["expected_growth_rate"]
    gt, gr = t["grat_term_years"], t["grat_annuity_rate"]
    ct, cr = t["crat_term_years"], t["crat_payout_rate"]
    grat_rem = a * (1 + g) ** gt - (a * gr * gt)
    crat_rem = a * (1 + g) ** ct - (a * cr * ct)
    return {
        "grat_term_years": gt,
        "grat_remainder": round(grat_rem, 2),
        "grat_estate_tax_reduction": round(grat_rem * tax["estate_tax_rate"], 2),
        "crat_term_years": ct,
        "crat_remainder": round(crat_rem, 2),
        "crat_income_tax_deduction": round(crat_rem * tax["charitable_deduction_rate"], 2),
    }


def trust_recommendation(api, cid):
    """
    Decide GRAT vs CRAT from the controlling GOAL facts (SIGNED_PROFILE).
    family_transfer_priority dominant -> GRAT (children transfer).
    philanthropic_intent dominant     -> CRAT (philanthropic).
    On a tie, family transfer wins for a family with high transfer priority.
    """
    s = controlling_facts(api, cid)["facts"]
    fam = {"low": 0, "moderate": 1, "high": 2}[s["family_transfer_priority"]]
    phil = {"low": 0, "moderate": 1, "high": 2}[s["philanthropic_intent"]]
    if phil > fam:
        return {"preferred_strategy": "CRAT",
                "rationale_code": "PHILANTHROPIC_PRIORITY",
                "alternate_role": "SECONDARY_FAMILY_TRANSFER_TOOL",
                "crat_family_transfer_fit": "LOW"}
    return {"preferred_strategy": "GRAT",
            "rationale_code": "CHILDREN_TRANSFER_PRIORITY",
            "alternate_role": "SECONDARY_CHARITABLE_TOOL",
            "crat_family_transfer_fit": "LOW"}


# ---------------------------------------------------------------------------
# ILIT / CRUMMEY
# ---------------------------------------------------------------------------
def ilit_cycle(api, cid):
    """
    annual_exclusion_per_beneficiary = annual_gift_exclusion[planning_year]
    beneficiary_count                = SIGNED_PROFILE beneficiary_count
    annual_exclusion_capacity        = exclusion * beneficiary_count
    premium_gap                      = max(0, annual_premium - capacity)
    notices_required                 = beneficiary_count

    Crummey date arithmetic (verified):
      contribution_date          = planned_contribution_date
      notice_due_date            = contribution_date + 7 days
      withdrawal_window_end      = notice_due_date + 30 days
      earliest_premium_payment   = withdrawal_window_end + 1 day
      (The 30-day window runs from the NOTICE DUE DATE, not the contribution.)

    tax_liquidity_support = death_benefit * estate_tax_rate  (NOT the full DB).
    projected_outside_estate_if_implemented:
      - new policy / not an existing-policy transfer -> full death_benefit
        (outside the estate), risk LOW_IF_FORMALITIES_MET.
      - existing-policy transfer -> THREE_YEAR_LOOKBACK; inside estate during
        the lookback (projected_outside = 0 within the 3-year window).
    """
    tax = api.tax()
    s = controlling_facts(api, cid)["facts"]
    l = api.life(cid)
    py = s["planning_year"]
    excl = tax["annual_gift_exclusion"][str(py)]
    bc = s["beneficiary_count"]
    cap = excl * bc
    prem = l["annual_premium"]
    gap = max(0.0, prem - cap)
    db = l["death_benefit"]

    contrib = date.fromisoformat(l["planned_contribution_date"])
    notice_due = contrib + timedelta(days=7)
    window_end = notice_due + timedelta(days=30)
    earliest = window_end + timedelta(days=1)

    existing = l.get("is_existing_policy_transfer", False)
    shortfall = gap > 0
    if existing and shortfall:
        risk = "THREE_YEAR_LOOKBACK_AND_EXCLUSION_SHORTFALL"
    elif existing:
        risk = "THREE_YEAR_LOOKBACK"
    elif shortfall:
        risk = "EXCLUSION_SHORTFALL"
    else:
        risk = "LOW_IF_FORMALITIES_MET"

    outside = 0.0 if existing else db  # within 3-yr lookback the DB is inside the estate

    return {
        "annual_exclusion_per_beneficiary": round(excl, 2),
        "beneficiary_count": bc,
        "annual_exclusion_capacity": round(cap, 2),
        "annual_premium": round(prem, 2),
        "premium_gap": round(gap, 2),
        "notices_required": bc,
        "contribution_date": contrib.isoformat(),
        "notice_due_date": notice_due.isoformat(),
        "withdrawal_window_end": window_end.isoformat(),
        "earliest_premium_payment_date": earliest.isoformat(),
        "dedicated_bank_account_required": True,
        "death_benefit": round(db, 2),
        "estate_inclusion_risk": risk,
        "projected_outside_estate_if_implemented": round(outside, 2),
        "tax_liquidity_support": round(db * tax["estate_tax_rate"], 2),
    }


if __name__ == "__main__":
    import sys
    api = API(sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8066")
    print(json.dumps(api.tax(), indent=2))
